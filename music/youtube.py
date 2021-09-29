import dataclasses
from typing import Any, Dict, List, Union

import youtube_dl
from discord import Embed, User
from youtube_dl.utils import YoutubeDLError

from .player import FFmpegTmpFileAudio
from .utils import format_time

# Suppress noise about console usage from errors
youtube_dl.utils.bug_reports_message = lambda: ""

ytdl_format_options = {
    "format": "bestaudio[ext=webm]/bestaudio/best",  # we want the best audio
    "nocheckcertificate": True,  # just in case
    "ignoreerrors": False,  # same
    "quiet": True,  # no clutter
    "no_warnings": True,  # same
    "skip_download": True,  # duh...
    "extract_flat": "in_playlist",  # don't process whole playlists
    "default_search": "ytsearch",  # default search for non-link stuff
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


ffmpeg_options = [
    "-y",  # don't prompt for user input (yes to all)
    "-vn",  # discard everything but the audio
    "-multiple_requests 1",  # not sure what this is doing
    "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",  # reconnect on failure
    "-fflags +discardcorrupt",  # don't crash on corrupt frames
]


@dataclasses.dataclass
class BaseYoutubeTrack:
    title: str
    url: str
    duration: float
    id: str
    requested_by: User
    thumbnail: str = ""
    channel: str = ""
    acodec: str = ""

    @property
    def markdown_link(self) -> str:
        link = f"https://www.youtube.com/watch?v={self.id}"
        return f"[{self.title}]({link})"


class YoutubeTrack(BaseYoutubeTrack):
    def __init__(self, *args, **kwargs):
        fields = [field.name for field in dataclasses.fields(self)]
        filtered_kwargs = {
            name: value for (name, value) in kwargs.items() if name in fields
        }

        super().__init__(*args, **filtered_kwargs)

    def update_info(self) -> None:
        new_info = ytdl.extract_info(self.id, ie_key="Youtube")
        if new_info is None:
            raise YoutubeDLError("Cannot update track information")

        self.__init__(**new_info, requested_by=self.requested_by)

    def as_audio(self) -> FFmpegTmpFileAudio:
        return FFmpegTmpFileAudio(
            self.url, codec=self.acodec, before_options=ffmpeg_options
        )

    def as_embed(self) -> Embed:
        embed = Embed(description=self.markdown_link)
        embed.set_thumbnail(url=self.thumbnail)
        embed.add_field(
            name="Requested by", value=f"`{self.requested_by.display_name}`"
        )
        embed.add_field(name="Duration", value=format_time(self.duration))

        return embed


class YoutubePlaylist:
    title: str
    entries: List[YoutubeTrack]
    requested_by: User

    def __init__(self, ytdl_info: Dict[str, Any], requested_by: User) -> None:
        self.title = ytdl_info["title"]
        entries = ytdl_info["entries"]
        self.entries = [
            YoutubeTrack(**info, requested_by=requested_by) for info in entries
        ]
        self.requested_by = requested_by


def yt_search(
    query: str, requested_by: User
) -> Union[None, YoutubeTrack, YoutubePlaylist]:
    data = ytdl.extract_info(query)

    if data is None:
        return None

    if data["extractor"] == "youtube:search":
        # Search results: we only take the first one if it exists
        results = data.get("entries", [])
        if len(results):
            track = YoutubeTrack(**results[0], requested_by=requested_by)
            track.update_info()
            return track
        else:
            return None

    elif data.get("_type") == "playlist":
        playlist = YoutubePlaylist(data, requested_by=requested_by)
        # We process the first entry, for thumbnail purposes
        playlist.entries[0].update_info()
        return playlist

    else:
        return YoutubeTrack(**data)
