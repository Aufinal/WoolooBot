import asyncio

import youtube_dl
from discord.player import FFmpegPCMAudio

from typing import Dict, Optional, Union

ytdl_format_options = {
    "format": "bestaudio/best",
    "nocheckcertificate": True,
    "ignoreerrors": False,
    "logtostderr": False,
    "quiet": True,
    "no_warnings": True,
    "skip_download": True,
    "extract_flat": "in_playlist",
    "default_search": "ytsearch",
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


class YoutubeTrack:
    def __init__(self, ytdl_info: Dict[str, str], processed: bool = True) -> None:
        self.from_ytdl(ytdl_info)
        self.processed = processed

    def from_ytdl(self, ytdl_info: Dict[str, str]) -> None:
        for attr in ("title", "url", "duration"):
            setattr(self, attr, ytdl_info[attr])

    async def update_info(self, loop: Optional[asyncio.AbstractEventLoop] = None):
        loop = loop or asyncio.get_event_loop()
        new_info = await loop.run_in_executor(
            None, lambda: ytdl.extract_info(self.url, ie_key="Youtube")
        )
        self.from_ytdl(new_info)

    def as_audio(self):
        return FFmpegPCMAudio(
            self.url,
            options=(
                "-vn -multiple_requests 1 -reconnect 1"
                " -reconnect_streamed 1 -reconnect_delay_max 5 -fflags +discardcorrupt"
            ),
        )


class YoutubePlaylist:
    def __init__(self, ytdl_info):
        self.title = ytdl_info["title"]
        self.entries = [
            YoutubeTrack(info, processed=False) for info in ytdl_info["entries"]
        ]


def yt_search(
    query: str, ie_key: Optional[str] = None
) -> Union[None, YoutubeTrack, YoutubePlaylist]:
    data = ytdl.extract_info(query, ie_key=ie_key)

    if data["extractor"] == "youtube:search":
        # Search results: we only take the first one if it exists
        results = data.get("entries", [])
        if len(results):
            track = results[0]
            return YoutubeTrack(track, processed=False)
        else:
            return None

    elif data.get("_type") == "playlist":
        # We add the whole unprocessed playlist for speed
        return YoutubePlaylist(data)

    else:
        return YoutubeTrack(data)
