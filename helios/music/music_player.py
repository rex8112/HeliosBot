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
import math
import re
import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Optional

import discord
from discord import Interaction
from discord.ext import tasks
from discord.utils import format_dt

from .playlist import Playlist, YoutubePlaylist
from .song import Song
from ..colour import Colour
from ..exceptions import ConnectError
from ..views.generic_views import YesNoView

if TYPE_CHECKING:
    from ..server import Server
    from ..member import HeliosMember


logger = logging.getLogger('HeliosLogger.Music')


class MusicPlayer:
    def __init__(self, server: 'Server'):
        """A class to manage music in a server."""
        self.server = server
        self.currently_playing: Optional['Song'] = None
        self.playlists: dict[discord.VoiceChannel, Playlist] = {}
        self._vc: Optional[discord.VoiceClient] = None
        self._started: Optional[datetime] = None
        self._ended: Optional[datetime] = None
        self._control_message: Optional[discord.Message] = None
        self._control_view: Optional['MusicPlayerView'] = None
        self._leaving = False
        self._stopping = False

        self.on_voice_state_update = self.server.bot.event(self.on_voice_state_update)

    @property
    def playlist(self) -> Playlist:
        if self.is_connected():
            playlist = self.playlists.get(self._vc.channel)
            if playlist is None:
                self.playlists[self._vc.channel] = playlist = Playlist()
            return playlist
        else:
            return Playlist()

    @property
    def channel(self):
        return self._vc.channel if self._vc else None

    @staticmethod
    def verify_url(url: str) -> bool:
        regex = r'https:\/\/(?:www\.)?youtu(?:be\.com|\.be)\/(?:playlist\?list=([^"&?\/\s]+)|(?:watch\?v=)?([^"&?\/\s]{3,11}))'
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
        if server.music_player.channel and interaction.user.voice.channel != server.music_player.channel:
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
            await interaction.response.defer(ephemeral=True)

        if not server.music_player.is_connected():
            await server.music_player.join_channel(interaction.user.voice.channel)

        matches = server.music_player.verify_url(url)
        is_playlist = server.music_player.is_playlist(url)
        if matches:
            if is_playlist:
                playlist = await server.music_player.fetch_playlist(url, requester=member)
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
                await server.music_player.add_playlist(playlist)
                await message.edit(content=f'Added {len(playlist)} songs to the queue', view=None)
            else:
                song = await server.music_player.fetch_song(url, requester=member)
                if song is None:
                    await interaction.followup.send('Sorry, I could not get that, is it private or typed wrong?')
                    return
                await server.music_player.add_song(song)
                await interaction.followup.send(content=f'Added {song.title} to the queue')
        else:
            await interaction.followup.send(content='Invalid URL Given')

    async def join_channel(self, channel: discord.VoiceChannel):
        if self.is_connected():
            if self._vc.channel == channel:
                return
            if self._control_message:
                try:
                    await self._control_message.delete()
                except (discord.Forbidden, discord.NotFound):
                    ...
                self._control_message = None
                self._control_view = None
            await self._vc.move_to(channel)
        else:
            logger.debug(f'{self.server.name}: Music Player: Joining {channel.name}')
            tries = 0
            while not self.is_connected() and tries < 3:
                try:
                    self._vc = await channel.connect(self_deaf=True)
                except (asyncio.TimeoutError, discord.HTTPException) as e:
                    logger.error(f'{self.server.name}: Music Player: Failed to join {channel.name}: {e}')
                    await asyncio.sleep(1)
                tries += 1

            if not self.is_connected():
                raise ConnectError(f'Failed to join {channel.name}')
            logger.debug(f'{self.server.name}: Music Player: Joined {channel.name}')
        self._leaving = False
        self._control_view = MusicPlayerView(self)
        self._control_view.update_buttons()
        self._control_message = await self._vc.channel.send(embeds=self.get_embeds(), view=self._control_view)
        self.check_vc.start()

    async def leave_channel(self):
        self._leaving = True
        self.currently_playing = None
        self.playlists.clear()
        if self._vc is not None:
            self._vc.stop()
            await self._vc.disconnect()
        self._vc = None

        try:
            await self._control_message.delete()
        except (discord.Forbidden, discord.NotFound, AttributeError) as e:
            logger.warning(f'{self.server.name}: Music Player: Failed to delete control message: {e}')

        if self._control_message is not None:
            self._control_view.stop()
        self._control_message = None
        self._control_view = None
        self._leaving = False
        self._ended = None
        self.check_vc.stop()

    def is_connected(self) -> bool:
        return self._vc and self._vc.is_connected()

    async def song_finished(self, exception: Optional[Exception]) -> None:
        if self._stopping:
            return
        if exception:
            logger.error(f'{self.server.name}: Music Player: Exception in song_finished: {exception}')
        duration_played = self.seconds_running()
        cost_per_minute = self.server.settings.music_points_per_minute.value
        cost = int((duration_played * cost_per_minute) / 60)
        try:
            await self.currently_playing.requester.add_points(-cost, 'Helios', f'Music Charged for {cost/cost_per_minute}'
                                                                               f' minutes')
            if self.currently_playing.tips > 0:
                embed = discord.Embed(
                    title=f'Tipped for {self.currently_playing.title}',
                    colour=Colour.success(),
                    description=f'You have been tipped **{self.currently_playing.tips}** times.'
                )
                await self.currently_playing.requester.member.send(embed=embed)
        except (discord.Forbidden, discord.HTTPException, AttributeError):
            ...

        self.stop_song()

        if self._leaving:
            return
        if exception or not self.is_connected():
            return
        await self.play_next()

    async def play_next(self):
        if not self.is_connected():
            return False
        cont = False
        next_song = None

        while cont is False:
            next_song = self.playlist.next()
            if next_song and next_song.playlist:
                next_song.playlist.next()

            if next_song and next_song.requester.member in self.channel.members:
                if next_song.requester.points > int((next_song.duration * 2) / 60):
                    cont = True
            if len(self.playlist) == 0 and next_song is None:
                cont = True

        if next_song is None:
            await self.update_message()
            return
        await self.play_song(next_song)

    async def play_song(self, song: 'Song') -> bool:
        if not self.is_connected():
            return False

        self._stopping = False
        self.currently_playing = song
        self._started = datetime.now().astimezone()
        self._ended = None
        loop = asyncio.get_event_loop()
        audio_source = await song.audio_source()
        await asyncio.sleep(0.5)
        if audio_source is None:
            return await self.play_next()
        self._vc.play(audio_source, after=lambda x: loop.create_task(self.song_finished(x)), bitrate=64)
        await self.update_message()
        return True

    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if member != member.guild.me:
            return
        if before.channel and after.channel is None and self._leaving is False:
            self.stop_song()
            await self.leave_channel()

    def stop_song(self) -> bool:
        self._stopping = True
        self.currently_playing = None
        self._started = None
        self._ended = datetime.now().astimezone()
        if not self.is_connected():
            return False
        self._vc.stop()
        return True

    def skip_song(self):
        self._vc.stop()

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

    async def add_song(self, song: 'Song'):
        """Add a song to the queue."""
        self.playlist.add_song(song)
        if self.currently_playing is None:
            await self.play_song(self.playlist.next())
        else:
            await self.update_message()

    async def add_playlist(self, playlist: 'YoutubePlaylist'):
        """Add a playlist to the queue."""
        [self.playlist.add_song(x) for x in playlist.unplayed]
        if self.currently_playing is None:
            await self.play_song(self.playlist.next())
        else:
            await self.update_message()

    async def update_message(self):
        if self._control_message is None:
            return
        self._control_view.update_buttons()
        await self._control_message.edit(embeds=self.get_embeds(), view=self._control_view)

    async def refresh_message(self):
        await self._control_message.delete()
        self._control_message = await self.channel.send(embeds=self.get_embeds(), view=self._control_view)

    @tasks.loop(seconds=10)
    async def check_vc(self):
        if not self.is_connected():
            return

        ago = datetime.now().astimezone() - timedelta(minutes=5)
        if self._ended and self._ended <= ago:
            await self.leave_channel()
        elif self.members_in_channel() == 0:
            await self.leave_channel()

    @check_vc.before_loop
    async def before_check_vc(self):
        await self.server.bot.wait_until_ready()

    def seconds_running(self) -> int:
        if self.currently_playing is None:
            return 0
        return int((datetime.now().astimezone() - self._started).total_seconds())

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

    def get_embeds(self) -> list[discord.Embed]:
        embeds = []
        np_string = 'Nothing Currently Playing'
        if self.currently_playing:
            ends = datetime.now().astimezone() + timedelta(seconds=self.currently_playing.duration)
            np_string = f'[{self.currently_playing.title}]({self.currently_playing.url})\nBy {self.currently_playing.author}\nEnds in: {format_dt(ends, "R")}'
        embed = discord.Embed(
            title='Now Playing',
            colour=Colour.music(),
            description=np_string
        )
        if self.currently_playing:
            embed.set_thumbnail(url=self.currently_playing.thumbnail)
            requester = self.currently_playing.requester
            embed.set_author(name=requester.member.display_name, icon_url=requester.member.display_avatar.url)

        nxt_string = 'Nothing'
        try:
            next_song = self.playlist.songs[0]
            nxt_string = f'[{next_song.title}]({next_song.url})\nBy {next_song.author}'
        except IndexError:
            ...
        embed.add_field(name='Next Up', value=nxt_string)
        embed.add_field(name='Songs in Queue', value=f'{len(self.playlist.songs)}')
        embeds.append(embed)

        if self.currently_playing and self.currently_playing.playlist:
            playlist = self.currently_playing.playlist
            delta = timedelta(seconds=self.playlist_time_left())
            end_time = datetime.now().astimezone() + delta
            playlist_embed = discord.Embed(
                title='Playlist',
                colour=Colour.playlist(),
                description=f'[{self.currently_playing.playlist.title}]({self.currently_playing.playlist.url})\n'
                            f'{len(playlist.played)+1}/'
                            f'{len(self.currently_playing.playlist)}\n\nEnds {format_dt(end_time, "R")}'
            )
            playlist_embed.set_thumbnail(url=self.currently_playing.playlist.thumbnail)
            embeds.insert(0, playlist_embed)
        return embeds


class MusicPlayerView(discord.ui.View):
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

    async def interaction_check(self, interaction: discord.Interaction, /) -> bool:
        if interaction.user.voice is None or interaction.user.voice.channel != self.mp.channel:
            await interaction.response.send_message(content=f'You need to be in {self.mp.channel.mention} to use this.',
                                                    ephemeral=True)
            return False
        return True

    def update_buttons(self):
        mems = self.mp.members_in_channel()
        self.skip.label = f'Skip ({len(self.voted_to_skip)}/{math.ceil(mems/2)})'
        disable = self.mp.currently_playing is None
        self.tip_button.label = f'Tip 10 {self.mp.server.points_name.capitalize()}'
        self.tip_button.disabled = disable
        self.skip.disabled = disable or len(self.voted_to_skip) >= math.ceil(mems / 2)
        self.skip_playlist.label = f'Skip Playlist ({len(self.voted_to_skip_playlist)}/{math.ceil(mems/2)})'
        self.skip_playlist.disabled = disable or len(self.voted_to_skip_playlist) >= math.ceil(mems / 2) or self.mp.currently_playing.playlist is None
        self.show_queue.disabled = len(self.mp.playlist.songs) == 0
        self.play.label = 'Enqueue' if self.mp.currently_playing else 'Play'

    @discord.ui.button(label='Play', style=discord.ButtonStyle.green)
    async def play(self, interaction: discord.Interaction, _: discord.ui.Button):
        await self.mp.member_play(interaction)

    @discord.ui.button(label='Skip', style=discord.ButtonStyle.red, disabled=True)
    async def skip(self, interaction: discord.Interaction, _: discord.ui.Button):
        update = False
        if interaction.user not in self.voted_to_skip:
            self.voted_to_skip.add(interaction.user)
            update = True
            await interaction.response.send_message(content='Voted to skip!', ephemeral=True)
        else:
            await interaction.response.send_message(content='Already voted!', ephemeral=True)

        if len(self.voted_to_skip) >= math.ceil(self.mp.members_in_channel() / 2):
            self.update_buttons()
            self.mp.skip_song()
            update = True

        if update:
            message = interaction.message
            if message is None:
                return
            self.update_buttons()
            await message.edit(view=self)

    @discord.ui.button(label='Show Queue')
    async def show_queue(self, interaction: discord.Interaction, _: discord.ui.Button):
        view = self.mp.playlist.get_paginator_view()
        await interaction.response.send_message(embeds=view.get_embeds(view.get_paged_values()), view=view,
                                                ephemeral=True)

    @discord.ui.button(label='Tip', style=discord.ButtonStyle.green, row=1, disabled=True)
    async def tip_button(self, interaction: discord.Interaction, _: discord.ui.Button):
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

    @discord.ui.button(label='Skip Playlist', style=discord.ButtonStyle.red, row=1)
    async def skip_playlist(self, interaction: discord.Interaction, _: discord.ui.Button):
        update = False
        if interaction.user not in self.voted_to_skip_playlist:
            self.voted_to_skip_playlist.add(interaction.user)
            update = True
            await interaction.response.send_message(content='Voted to skip!', ephemeral=True)
        else:
            await interaction.response.send_message(content='Already voted!', ephemeral=True)

        if len(self.voted_to_skip_playlist) >= math.ceil(self.mp.members_in_channel() / 2):
            self.update_buttons()
            self.mp.skip_playlist()
            update = True

        if update:
            message = interaction.message
            if message is None:
                return
            self.update_buttons()
            await message.edit(view=self)

    @discord.ui.button(label='Refresh', row=1)
    async def refresh_message(self, interaction: discord.Interaction, _):
        await interaction.response.defer()
        await self.mp.refresh_message()


class NewSongModal(discord.ui.Modal):
    url = discord.ui.TextInput(label='Youtube URL')

    def __init__(self):
        super().__init__(title='Queue Song')
        self.interaction: Optional[discord.Interaction] = None

    async def on_submit(self, interaction: Interaction, /) -> None:
        self.interaction = interaction
        await interaction.response.defer(ephemeral=True, thinking=True)
        self.stop()



