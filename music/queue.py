import time
from typing import List, Optional, Tuple, Union

import discord

from .youtube import YoutubePlaylist, YoutubeTrack
from .utils import format_time


class QueueError(Exception):
    pass


class TrackQueue:
    def __init__(self):
        self.entries: List[YoutubeTrack] = []
        self.playing: Optional[YoutubeTrack] = None
        self.playing_since: Optional[float] = None

    def queue_time(self) -> int:
        if self.playing is not None and self.playing_since is not None:
            track_remaining = int(self.playing_since + self.playing.duration - time())
        else:
            track_remaining = 0

        return track_remaining + int(sum(entry.duration for entry in self.entries))

    def enqueue(self, item: Union[YoutubeTrack, YoutubePlaylist]) -> discord.Embed:
        if isinstance(item, YoutubeTrack):
            return self.enqueue_track(item)
        else:
            return self.enqueue_playlist(item)

    def enqueue_track(self, track: YoutubeTrack) -> discord.Embed:
        tracks_until = len(self.entries)
        time_until = self.queue_time()
        self.entries.append(track)

        embed = discord.Embed(
            description=track.markdown_link,
        )
        embed.set_author(
            name="Track added to queue", icon_url=track.requested_by.avatar_url
        )
        embed.set_thumbnail(url=track.thumbnail)
        embed.add_field(name="Channel", value=track.channel)
        embed.add_field(name="Duration", value=track.pretty_duration)
        embed.add_field(
            name="Time until playing",
            value=format_time(time_until) if time_until else "Now",
        )
        embed.add_field(
            name="Position in queue",
            value="Now"
            if tracks_until == 0 and self.playing is None
            else tracks_until + 1,
            inline=False,
        )

        return embed

    def enqueue_playlist(self, playlist: YoutubePlaylist) -> discord.Embed:
        time_until = self.queue_time()
        tracks_until = len(self.entries)
        for entry in playlist.entries:
            entry.requested_by = playlist.requested_by

        self.entries.extend(playlist.entries)

        embed = discord.Embed(description=playlist.title)
        embed.set_author(
            name="Playlist added to queue", icon_url=playlist.requested_by.avatar_url
        )
        embed.set_thumbnail(url=playlist.entries[0].thumbnail)
        embed.add_field(
            name="Time until playing",
            value=format_time(time_until) if time_until else "Now",
            inline=False,
        )

        embed.add_field(
            name="Position in queue",
            value="Now" if tracks_until == 0 else tracks_until,
        )
        embed.add_field(
            name="Enqueued", value="`{}` tracks".format(len(playlist.entries))
        )

        return embed

    def next_song(self) -> Tuple[Optional[YoutubeTrack], Optional[str]]:
        if self.entries:
            track = self.entries.pop(0)
            next_track = self.entries[0].title if self.entries else "Nothing"
            return (track, next_track)
        else:
            return (None, None)

    def clear(self) -> None:
        self.entries = []

    def as_embed(self) -> discord.Embed:
        embed = discord.Embed(title="Current queue")

        now_playing = "   {} | {} | Requested by {}".format(
            self.playing.markdown_link,
            self.playing.pretty_duration,
            self.playing.requested_by.name,
        )

        up_next = ""
        for (i, track) in enumerate(self.entries[:10]):
            up_next += "{}. {} | {} | Requested by {}".format(
                i + 1,
                track.markdown_link,
                track.pretty_duration,
                track.requested_by.name,
            )
            up_next += "\n\n"

        num_tracks = len(self.entries)

        embed.description = f"""
        **Now playing:**
        {now_playing}

        **Up next:**
        {up_next}
        **{num_tracks} tracks in queue - {format_time(self.queue_time)} total length**
        """

        return embed

    def remove(self, args: List[int]):
        invalid_args = [a for a in args if a > len(self.entries) or a <= 0]
        if invalid_args:
            raise QueueError(invalid_args)

        else:
            removed_entries = [e for (i, e) in enumerate(self.entries) if i + 1 in args]
            new_entries = [e for (i, e) in enumerate(self.entries) if i + 1 not in args]
            self.entries = new_entries

            return removed_entries
