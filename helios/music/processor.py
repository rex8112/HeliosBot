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
import functools
import yt_dlp

import discord

ytdlopts = {
    'format': 'bestaudio/best',
    'outtmpl': 'downloads/%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'audioformat': 'mp3',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
    'force-ipv4': True,
    'preferredcodec': 'mp3',
    'cachedir': False
}

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn -sn -dn -ignore_unknown'
}

ytdl = yt_dlp.YoutubeDL(ytdlopts)


def extract_info_wrapper(*args, **kwargs):
    data = ytdl.extract_info(*args, **kwargs)
    return data


async def get_info(url: str, *, process=True):
    loop = asyncio.get_event_loop()
    partial = functools.partial(extract_info_wrapper, url=url, download=False, process=process)
    data = await loop.run_in_executor(None, partial)
    if data.get('extractor') == 'youtube:tab':
        partial.keywords['url'] = data.get('url')
        data = await loop.run_in_executor(None, partial)
    return data


async def get_audio_source(url: str):
    data = await get_info(url)
    return discord.FFmpegPCMAudio(source=data['url'], **ffmpeg_options, executable='ffmpeg')
