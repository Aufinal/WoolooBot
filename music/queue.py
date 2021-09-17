from typing import List, Optional, Tuple, Union

import discord

from .youtube import YoutubePlaylist, YoutubeTrack


class TrackQueue:
    def __init__(self):
        self.entries: List[YoutubeTrack] = []

    def enqueue(self, item: Union[YoutubeTrack, YoutubePlaylist]) -> discord.Embed:
        if isinstance(item, YoutubeTrack):
            return self.enqueue_track(item)
        else:
            return self.enqueue_playlist(item)

    def enqueue_track(self, track: YoutubeTrack) -> discord.Embed:
        # TODO: be more precise
        time_until = sum(tr.duration for tr in self.entries)
        tracks_until = len(self.entries)
        self.entries.append(track)

        embed = discord.Embed(
            description=f"[{track.title}]({track.url})",
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
        # TODO: be more precise
        time_until = sum(tr.duration for tr in self.entries)
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

    def pop(self) -> Optional[Tuple[YoutubeTrack, discord.Embed]]:

        if self.entries:
            track = self.entries.pop(0)
            next_track = self.entries[0].title if self.entries else "Nothing"
            embed = discord.Embed(
                title="Now playing",
                description=f"[{track.title}]({track.url})",
            )
            embed.set_thumbnail(url=track.thumbnail)
            embed.add_field(
                name="Requested by", value=f"`{track.requested_by.display_name}`"
            )
            embed.add_field(name="Duration", value=track.pretty_duration)
            embed.add_field(name="Up next", value=f"`{next_track}`", inline=False)
            return (track, embed)
        else:
            return (None, None)

    def reset(self):
        self.entries = []
