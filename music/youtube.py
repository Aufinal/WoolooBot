from typing import Dict, Union

import youtube_dl
from discord.player import FFmpegPCMAudio

# Suppress noise about console usage from errors
youtube_dl.utils.bug_reports_message = lambda: ""

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

ffmpeg_options = [
    "-vn",  # discard video
    "-multiple_requests 1",  # uhhh
    "-reconnect 1",  # reconnect on failure...
    "-reconnect_streamed 1",  # ... even if streaming...
    "-reconnect_delay_max 5",  # ... fail after 5s of failed attempts
    "-fflags +discardcorrupt",  # don't crash on corrupt frames
    "-bufsize 960k",  # small buffer (music is 192kbps)
]


class YoutubeTrack:
    def __init__(self, ytdl_info: Dict[str, str], processed: bool = True) -> None:
        self.from_ytdl(ytdl_info)
        self.processed = processed

    def from_ytdl(self, ytdl_info: Dict[str, str]) -> None:
        for attr in ("title", "url", "duration", "thumbnail", "channel"):
            setattr(self, attr, ytdl_info.get(attr, ""))

    def update_info(self):
        new_info = ytdl.extract_info(self.url, ie_key="Youtube")
        self.from_ytdl(new_info)
        self.processed = True

    @property
    def pretty_duration(self):
        return "{:02d}:{:02d}".format(*divmod(self.duration, 60))

    def as_audio(self) -> FFmpegPCMAudio:
        return FFmpegPCMAudio(self.url, options=" ".join(ffmpeg_options))


class YoutubePlaylist:
    def __init__(self, ytdl_info: Dict[str, str]) -> None:
        self.title = ytdl_info["title"]
        self.entries = [
            YoutubeTrack(info, processed=False) for info in ytdl_info["entries"]
        ]


def yt_search(query: str) -> Union[None, YoutubeTrack, YoutubePlaylist]:
    data = ytdl.extract_info(query)

    if data["extractor"] == "youtube:search":
        # Search results: we only take the first one if it exists
        results = data.get("entries", [])
        if len(results):
            track = YoutubeTrack(results[0])
            track.update_info()
            return track
        else:
            return None

    elif data.get("_type") == "playlist":
        playlist = YoutubePlaylist(data)
        # We only process the first entry, for thumbnail purposes
        playlist.entries[0].update_info()
        return playlist

    else:
        return YoutubeTrack(data)
