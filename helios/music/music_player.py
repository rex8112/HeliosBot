#  MIT License
#
#  Copyright (c) 2023 Riley Winkler
#
#  Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to deal
#  in the Software without restriction, including without limitation the rights
#  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#  copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included in all
#  copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
#  SOFTWARE.
import asyncio
import logging
import math
import re
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Optional, Self

import discord
from discord import Interaction, ui
from discord.utils import format_dt

from .playlist import Playlist, YoutubePlaylist
from .song import Song
from ..colour import Colour
from ..views.generic_views import YesNoView

if TYPE_CHECKING:
    from ..helios_voice_controller import HeliosVoiceController
    from ..voice_scheduler import Schedule, TimeSlot
    from ..server import Server
    from ..member import HeliosMember


logger = logging.getLogger('HeliosLogger.Music')


class MusicPlayer:
    def __init__(self, vc: 'HeliosVoiceController', schedule: 'Schedule', time_slot: 'TimeSlot'):
        """A class to manage music in a server."""
        self.vc = vc
        self.server: 'Server' = vc.server
        self.schedule = schedule
        self.time_slot = time_slot

        self.currently_playing: Optional['Song'] = None
        self.background_playlist: Playlist = Playlist()
        self._playlist: Playlist = Playlist()
        self._vc: Optional[discord.VoiceClient] = self.server.guild.voice_client
        self._started: Optional[datetime] = None
        self._ended: Optional[datetime] = None
        self._control_message: Optional[discord.Message] = None
        self._control_view: Optional['MusicPlayerView'] = None
        self._leaving = False
        self._stopping = False
        self._skipping = False
        self.loop_running = False
        self._task = None

    @property
    def playlist(self) -> Playlist:
        return self._playlist

    @property
    def channel(self):
        return self._vc.channel if self._vc else None

    @staticmethod
    def verify_url(url: str) -> bool:
        regex = r'https:\/\/(?:www\.)?|(?:music\.)?youtu(?:be\.com|\.be)\/(?:playlist\?list=([^"&?\/\s]+)|(?:watch\?v=)?([^"&?\/\s]{3,11}))'
        matches = re.match(regex, url, re.RegexFlag.I)
        return matches is not None

    @staticmethod
    def is_playlist(url: str) -> bool:
        return 'playlist' in url

    @staticmethod
    async def fetch_song(url: str, requester: 'HeliosMember') -> Optional['Song']:
        return await Song.from_url(url, requester=requester)

    @staticmethod
    async def fetch_playlist(url: str, requester: 'HeliosMember') -> Optional['YoutubePlaylist']:
        return await YoutubePlaylist.from_url(url, requester=requester)

    async def member_play(self, interaction: discord.Interaction, *args):
        server = self.server
        member = server.members.get(interaction.user.id)
        if interaction.user.voice is None:
            await interaction.response.send_message(content='Must be in a VC', ephemeral=True)
            return
        if self.channel and interaction.user.voice.channel != self.channel:
            await interaction.response.send_message(content=f'I am currently busy, sorry.')
            return

        if len(args) > 0:
            url = args[0]
        else:
            url = None
        if not url:
            modal = NewSongModal()
            await interaction.response.send_modal(modal)
            await modal.wait()
            url = modal.url.value
            interaction = modal.interaction
        else:
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=True)

        assert interaction

        matches = self.verify_url(url)
        is_playlist = self.is_playlist(url)
        if matches:
            if is_playlist:
                playlist = await self.fetch_playlist(url, requester=member)
                if playlist is None:
                    await interaction.followup.send('Sorry, I could not get that, is it private or typed wrong?')
                    return
                cost = playlist.total_cost
                if member.points < cost:
                    await interaction.followup.send(content=f'Not enough {server.points_name.capitalize()} to play this'
                                                            f' playlist. Cost: {cost} '
                                                            f'{server.points_name.capitalize()}')
                    return
                view = YesNoView(interaction.user)
                message = await interaction.followup.send(content=f'Would you like to shuffle this playlist?', view=view)
                await view.wait()
                shuffle = view.value if view.value is not None else False
                if shuffle:
                    playlist.shuffle()
                if await self.add_playlist(playlist):
                    await message.edit(content=f'Added {len(playlist)} songs to the queue', view=None)
                else:
                    await message.edit(content='Failed to add playlist to queue, not enough available time', view=None)
            else:
                song = await self.fetch_song(url, requester=member)
                if song is None:
                    await interaction.followup.send('Sorry, I could not get that, is it private or typed wrong?')
                    return
                if await self.add_song(song):
                    await interaction.followup.send(content=f'Added {song.title} to the queue')
                else:
                    await interaction.followup.send(content='Failed to add song to queue, not enough available time')
        else:
            await interaction.followup.send(content='Invalid URL Given')

    def start(self):
        if not self.loop_running:
            self._task = asyncio.create_task(self.main_loop())

    def stop(self):
        self._stopping = True
        if self._control_message is not None:
            self._control_view.stop()

    async def main_loop(self):
        self.loop_running = True
        try:
            while not self._stopping:
                try:
                    if self._control_message is None:
                        await self.refresh_message()
                    if not self.is_connected() or not await self.play_music():
                        await asyncio.sleep(1)
                except Exception as e:
                    logger.error(f'{self.server.name}: Music Player: Main Loop Error: <{type(e).__name__}> {e}')
                    await asyncio.sleep(1)
            await self._control_message.delete()
        finally:
            self.loop_running = False

    async def play_music(self):
        if self.playlist.get_current_song() is None:
            return False
        if self.currently_playing is not None:
            logger.critical(f'{self.server.name}: Music Player: Two loops running at once')
            return False
        song = self.playlist.next()
        if song is None:
            return False
        self._skipping = False
        self.currently_playing = song
        await self.update_message()

        duration = song.duration
        start = 0
        finished = False
        while not finished:
            try:
                await self.vc.play(await song.audio_source(start=start))
            except Exception as e:
                logger.error(f'{self.server.name}: Music Player: Failed to play song: {e}')
                pass
            # If song ended early, try to continue unless it was skipped.
            if self._skipping:
                break
            now = datetime.now().astimezone()
            played_for = (now - self.vc.last_start).total_seconds()
            time_left = duration - (played_for + start)

            if time_left / duration > 0.1 and not self._stopping:
                start += played_for
                await asyncio.sleep(1)
            else:
                finished = True

        if song.playlist:
            song.playlist.next()
        self.currently_playing = None
        await self.update_message()
        return True

    def is_connected(self) -> bool:
        return bool(self.vc.voice_client and self.vc.voice_client.is_connected())

    def skip_song(self):
        self._skipping = True
        self.vc.voice_client.stop()

    def skip_playlist(self):
        if self.currently_playing and self.currently_playing.playlist:
            songs = self.currently_playing.playlist.songs
            for song in songs:
                try:
                    self.playlist.songs.remove(song)
                except ValueError:
                    ...
        self.skip_song()

    def playlist_time_left(self) -> int:
        if self.currently_playing and self.currently_playing.playlist:
            songs = self.currently_playing.playlist.unplayed
            delta = sum([x.duration if x.duration else 0 for x in songs])
            if self.currently_playing:
                delta += self.time_left()
            return delta
        return 0

    def check_schedule(self, duration: int):
        now = datetime.now().astimezone()
        song_end = now + timedelta(seconds=duration)
        if song_end > self.time_slot.end - timedelta(seconds=5*60):
            res = self.schedule.set_end_time(self.time_slot, song_end + timedelta(seconds=5*60))
            return res
        return True

    async def add_song(self, song: 'Song'):
        """Add a song to the queue."""
        if not self.check_schedule(song.duration):
            return False
        self.playlist.add_song(song)
        if self.loop_running:
            await self.update_message()
        return True

    async def add_playlist(self, playlist: 'YoutubePlaylist'):
        """Add a playlist to the queue."""
        if not self.check_schedule(playlist.total_duration):
            return False
        [self.playlist.add_song(x) for x in playlist.unplayed]
        if self.loop_running:
            await self.update_message()
        return True

    async def update_message(self):
        if self._control_message is None:
            return
        await self._control_view.setup()
        try:
            await self._control_message.edit(view=self._control_view)
        except discord.NotFound:
            self._control_message = None
            await self.refresh_message()

    async def refresh_message(self):
        if self._control_message:
            await self._control_message.delete()
        if self._control_view is None or self._control_view.is_finished():
            self._control_view = await MusicPlayerView(self).setup()
        else:
            await self._control_view.setup()
        # noinspection bad-argument-type
        self._control_message = await self.channel.send(view=self._control_view)

    def seconds_running(self) -> int:
        if self.currently_playing is None:
            return 0
        return int((datetime.now().astimezone() - self._started).total_seconds()) if self._started else 0

    def time_left(self) -> int:
        if self.currently_playing is None:
            return 0
        duration = self.currently_playing.duration
        seconds_running = self.seconds_running()
        return duration - seconds_running

    def members_in_channel(self) -> int:
        if self.is_connected():
            return len(self._vc.channel.members) - 1
        return 0


class SkipPlaylistButton(ui.Button['MusicPlayerView']):
    def __init__(self, mp: 'MusicPlayer', votes: int, needed: int) -> None:
        super().__init__(style=discord.ButtonStyle.red)
        self.mp = mp
        disable = mp.currently_playing is None
        self.label = f'Skip Playlist ({votes}/{needed})'
        self.disabled = disable or votes >= needed or mp.currently_playing.playlist is None

    async def callback(self, interaction: discord.Interaction):
        assert isinstance(self.view, MusicPlayerView)
        update = False

        if interaction.user not in self.view.voted_to_skip_playlist:
            self.view.voted_to_skip_playlist.add(interaction.user)
            update = True
            await interaction.response.send_message(content='Voted to skip!', ephemeral=True)
        else:
            await interaction.response.send_message(content='Already voted!', ephemeral=True)

        if len(self.view.voted_to_skip_playlist) >= math.ceil(self.mp.members_in_channel() / 2):
            await self.view.setup()
            self.mp.skip_playlist()
            update = True

        if update:
            message = interaction.message
            if message is None:
                return
            await self.view.setup()
            await message.edit(view=self.view)


class MusicPlayerActionRow(ui.ActionRow['MusicPlayerView']):
    def __init__(self, mp: 'MusicPlayer', skips: int):
        super().__init__()
        self.mp = mp

        mems = self.mp.members_in_channel()
        self.skip.label = f'Skip ({skips}/{math.ceil(mems/2)})'
        disable = self.mp.currently_playing is None
        self.tip_button.label = f'Tip 10 {self.mp.server.points_name.capitalize()}'
        self.tip_button.disabled = disable
        self.skip.disabled = disable or skips >= math.ceil(mems / 2)
        self.show_queue.disabled = len(self.mp.playlist.songs) == 0
        self.play.label = 'Enqueue' if self.mp.currently_playing else 'Play'

    @ui.button(label='Play', style=discord.ButtonStyle.green)
    async def play(self: Self, interaction: discord.Interaction, _: discord.ui.Button):
        await self.mp.member_play(interaction)

    @ui.button(label='Skip', style=discord.ButtonStyle.red, disabled=True)
    async def skip(self: Self, interaction: discord.Interaction, _: discord.ui.Button):
        update = False
        if interaction.user not in self.view.voted_to_skip:
            self.view.voted_to_skip.add(interaction.user)
            update = True
            await interaction.response.send_message(content='Voted to skip!', ephemeral=True)
        else:
            await interaction.response.send_message(content='Already voted!', ephemeral=True)

        if len(self.view.voted_to_skip) >= math.ceil(self.mp.members_in_channel() / 2):
            await self.view.setup()
            self.mp.skip_song()
            update = True

        if update:
            message = interaction.message
            if message is None:
                return
            await self.view.setup()
            await message.edit(view=self.view)

    @ui.button(label='Show Queue')
    async def show_queue(self: Self, interaction: discord.Interaction, _: discord.ui.Button):
        view = self.mp.playlist.get_paginator_view()
        await interaction.response.send_message(embeds=view.get_embeds(view.get_paged_values()), view=view,
                                                ephemeral=True)

    @ui.button(label='Tip', style=discord.ButtonStyle.green, row=1, disabled=True)
    async def tip_button(self: Self, interaction: discord.Interaction, _: discord.ui.Button):
        if self.mp.currently_playing is None:
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        member = self.mp.server.members.get(interaction.user.id)
        requester = self.mp.currently_playing.requester
        if member == requester:
            await interaction.followup.send(content='You can\'t tip yourself.')
            return
        if member.points >= 10:
            self.mp.currently_playing.tips += 1
            await member.transfer_points(requester, 10, 'Music Tip')
            await interaction.followup.send(content=f'Successfully tipped {requester.member.display_name} **10** '
                                                    f'{self.mp.server.points_name.capitalize()}')
        else:
            await interaction.followup.send(content=f'Not enough {self.mp.server.points_name.capitalize()}')

    @ui.button(label='Refresh', row=1)
    async def refresh_message(self: Self, interaction: discord.Interaction, _):
        await interaction.response.defer()
        await self.mp.refresh_message()


class MusicPlayerView(ui.LayoutView):
    container = ui.Container(accent_color=Colour.music())

    def __init__(self, mp: 'MusicPlayer'):
        super().__init__(timeout=None)
        self.mp = mp

    @property
    def song(self):
        return self.mp.currently_playing

    @property
    def playlist(self):
        return self.song.playlist if self.song else None

    @property
    def voted_to_skip(self):
        return self.song.vote_skip if self.song else set()

    @property
    def voted_to_skip_playlist(self):
        return self.playlist.vote_skip if self.playlist else set()

    async def setup(self) -> Self:
        self.container.clear_items()
        self.container.add_item(ui.TextDisplay(
            '## Music Player'
        ))

        if self.mp.currently_playing and self.mp.currently_playing.playlist:
            playlist = self.mp.currently_playing.playlist
            delta = timedelta(seconds=self.mp.playlist_time_left())
            end_time = datetime.now().astimezone() + delta
            mems = self.mp.members_in_channel()
            self.container.add_item(ui.Section(
                ui.TextDisplay[MusicPlayerView](
                    f'### Playlist\n'
                    f'[{playlist.title}]({playlist.url})\n'
                    f'{len(playlist.played)+1}/{len(playlist)}\n\n'
                    f'Ends {format_dt(end_time, "R")}'
                ),
                accessory=SkipPlaylistButton(self.mp, len(self.voted_to_skip_playlist), math.ceil(mems / 2)),
            ))
            self.container.add_item(ui.Separator())
        if self.mp.currently_playing:
            requester = self.mp.currently_playing.requester
            ends = datetime.now().astimezone() + timedelta(seconds=self.mp.currently_playing.duration)
            self.container.add_item(ui.Section(
                ui.TextDisplay(
                    '### Now Playing\n'
                    f'[{self.mp.currently_playing.title}]({self.mp.currently_playing.url})\n'
                    f'By {self.mp.currently_playing.author}\n'
                    f'Ends in: {format_dt(ends, "R")}\n'
                    f'-# Played by: {requester.member.display_name}',
                ),
                accessory=ui.Thumbnail(self.mp.currently_playing.thumbnail)
            ))
        elif self.mp.playlist.get_current_song():
            self.container.add_item(ui.TextDisplay(
                '**<LOADING NEXT SONG...>**',
            ))
        else:
            self.container.add_item(ui.TextDisplay(
                'Waiting for next song...',
            ))

        try:
            next_song = self.mp.playlist.songs[0]
            self.container.add_item(ui.Separator())
            self.container.add_item(ui.TextDisplay(
                f'### Next Up\n'
                f'[{next_song.title}]({next_song.url})\nBy {next_song.author}'
            ))
        except IndexError:
            pass

        self.container.add_item(MusicPlayerActionRow(self.mp, len(self.voted_to_skip)))

        return self

    async def interaction_check(self, interaction: discord.Interaction, /) -> bool:
        if interaction.user.voice is None or interaction.user.voice.channel != self.mp.channel:
            await interaction.response.send_message(content=f'You need to be in {self.mp.channel.mention} to use this.',
                                                    ephemeral=True)
            return False
        return True


class NewSongModal(discord.ui.Modal):
    url = discord.ui.TextInput(label='Youtube URL')

    def __init__(self):
        super().__init__(title='Queue Song')
        self.interaction: Optional[discord.Interaction] = None

    async def on_submit(self, interaction: Interaction, /) -> None:
        self.interaction = interaction
        await interaction.response.defer(ephemeral=True, thinking=True)
        self.stop()



