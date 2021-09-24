from typing import Dict, Optional, Union

import youtube_dl
from discord import Member, Embed
from .player import FFmpegTmpFileAudio

# Suppress noise about console usage from errors
youtube_dl.utils.bug_reports_message = lambda: ""

ytdl_format_options = {
    "format": "bestaudio[ext=webm]/bestaudio",  # we want the best audio
    "nocheckcertificate": True,  # just in case
    "ignoreerrors": False,  # same
    "quiet": True,  # no clutter
    "no_warnings": True,  # same
    "skip_download": True,  # duh...
    "extract_flat": "in_playlist",  # don't process whole playlists
    "default_search": "ytsearch",  # default search for non-link stuff
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


class YoutubeTrack:
    def __init__(self, ytdl_info: Dict[str, str], processed: bool = True) -> None:
        self.from_ytdl(ytdl_info)
        self.processed = processed
        self.requested_by: Optional[Member] = None

    def from_ytdl(self, ytdl_info: Dict[str, str]) -> None:
        for attr in (
            "title",
            "url",
            "duration",
            "thumbnail",
            "channel",
            "id",
            "acodec",
        ):
            setattr(self, attr, ytdl_info.get(attr, ""))

    def update_info(self):
        new_info = ytdl.extract_info(self.url, ie_key="Youtube")
        self.from_ytdl(new_info)
        self.processed = True

    def as_audio(self):
        return FFmpegTmpFileAudio(self.url, codec=self.acodec)

    def as_embed(self):
        embed = Embed(
            description=f"[{self.title}]({self.url})",
        )
        embed.set_thumbnail(url=self.thumbnail)
        embed.add_field(
            name="Requested by", value=f"`{self.requested_by.display_name}`"
        )
        embed.add_field(name="Duration", value=self.pretty_duration)

        return embed

    @property
    def pretty_duration(self):
        return "{:02d}:{:02d}".format(*divmod(int(self.duration), 60))

    @property
    def markdown_link(self):
        link = f"https://www.youtube.com/watch?v={self.id}"
        return f"[{self.title}]({link})"


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
        # We process the first entry, for thumbnail purposes
        playlist.entries[0].update_info()
        return playlist

    else:
        return YoutubeTrack(data)
