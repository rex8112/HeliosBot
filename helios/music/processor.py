import asyncio

import discord
import youtube_dl

ytdlopts = {
    'format': 'bestaudio/best',
    'outtmpl': 'downloads/%(extractor)s-%(id)s-%(title)s.%(ext)s',
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
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdlopts)


class YtProcessor:
    @staticmethod
    async def get_info(url: str):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: ytdl.extract_info(url=url, download=False))

    @staticmethod
    def get_audio_source_from_raw(raw_url: str):
        return discord.FFmpegPCMAudio(source=raw_url, **ffmpeg_options, executable='ffmpeg')
