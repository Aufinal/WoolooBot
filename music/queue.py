from time import strftime, gmtime, time
from typing import List, Optional, Tuple, Union

import discord

from .youtube import YoutubePlaylist, YoutubeTrack


class TrackQueue:
    def __init__(self):
        self.entries: List[YoutubeTrack] = []
        self.playing: Optional[YoutubeTrack] = None
        self.playing_since: Optional[float] = None

    def queue_time(self):
        if self.playing is not None and self.playing_since is not None:
            track_remaining = int(self.playing_since + self.playing.duration - time())
        else:
            track_remaining = 0
        return track_remaining + sum(entry.duration for entry in self.entries)

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
            value="{:02d}:{:02d}".format(*divmod(time_until, 60))
            if time_until
            else "Now",
        )
        embed.add_field(
            name="Position in queue",
            value="Now" if tracks_until == 0 else tracks_until,
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
            value="{:02d}:{:02d}".format(*divmod(time_until, 60))
            if time_until
            else "Now",
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

    def next_song(self) -> Tuple[Optional[YoutubeTrack], Optional[discord.Embed]]:
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
        tot_duration = int(sum(entry.duration for entry in self.entries))
        strformat = "%M:%S" if tot_duration < 3600 else "%H:%M:%S"
        tot_duration = strftime(strformat, gmtime(tot_duration))

        embed.description = f"""
        **Now playing:**
        {now_playing}

        **Up next:**
        {up_next}
        **{num_tracks} tracks in queue - {tot_duration} total length**"""

        return embed
