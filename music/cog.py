import asyncio
import logging
import os
import time
from typing import Optional, cast

import discord
from discord.ext import commands, tasks
from youtube_dl.utils import YoutubeDLError

from .guildstate import GuildVar
from .queue import QueueError, TrackQueue
from .utils import (
    MessageableException,
    check_bot_connected,
    check_bot_voice,
    check_channel,
    check_voice,
)
from .youtube import yt_search

# Maximum idle time before the bot disconnects from channel
MAX_IDLE_TIME = 120.0

# Maximum waiting time for YT video processing
MAX_YT_WAIT_TIME = 5

log = logging.getLogger(__name__)


def is_idle(client: discord.VoiceClient):
    is_alone = len(cast(discord.VoiceChannel, client.channel).members) == 1
    is_silent = not client.is_playing()

    return is_alone or is_silent


class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.queue = GuildVar(TrackQueue)
        self.bound_channel: GuildVar[Optional[discord.TextChannel]] = GuildVar(
            lambda: None
        )
        self.paused_at: GuildVar[Optional[float]] = GuildVar(lambda: None)
        self.idle_since: GuildVar[Optional[float]] = GuildVar(lambda: None)

        self.check_idle.start()

    async def cog_command_error(
        self, ctx: commands.Context, error: commands.CommandError
    ):
        if isinstance(error, MessageableException):
            await ctx.send(error.message)

        return await super().cog_command_error(ctx, error)

    @commands.command(aliases=["p"])
    @check_channel
    @check_voice
    async def play(self, ctx: commands.Context, *, query: str):
        """Plays from either a Youtube URL or Youtube search."""
        if ctx.voice_client is None:
            # First use: we join the channel of the command's author and bind
            voice_channel = ctx.author.voice.channel
            text_channel = ctx.channel

            self.bound_channel[ctx] = text_channel
            await voice_channel.connect()
            await ctx.send(
                f"Joined {voice_channel.mention} and bound to {text_channel.mention}."
            )

        assert ctx.voice_client is not None

        try:
            search_result = await self.bot.loop.run_in_executor(
                None, yt_search, query, ctx.author
            )
        except YoutubeDLError as e:
            return await ctx.send(f"Youtube-dl error : {e}")

        if search_result is None:
            return await ctx.send("No results found !")

        else:
            embed = self.queue[ctx].enqueue(search_result)
            await ctx.send(embed=embed)

        if not ctx.voice_client.is_playing():
            return await self.next_track(ctx)

    async def next_track(self, ctx: commands.Context):
        if ctx.voice_client is None:
            return

        (track, next_track) = self.queue[ctx].next_song()

        if track is None:
            ctx.voice_client.stop()
            self.queue[ctx].playing = None
            return

        await self.bot.loop.run_in_executor(None, track.update_info)

        embed = track.as_embed()
        embed.title = "Now playing"
        embed.add_field(name="Up next", value=next_track, inline=False)

        assert self.bound_channel[ctx] is not None
        await self.bound_channel[ctx].send(embed=embed)  # type: ignore

        player = track.as_audio()
        log.info(f"Playing {track.url}")

        # Wait for file to be nonempty to stream (avoids premature stopping)
        # Loses up to 1s on very slow connections...
        t = time.time()
        while not os.stat(player._tempfile.name).st_size:
            time.sleep(0.01)
            if time.time() - t > MAX_YT_WAIT_TIME:
                await self.bound_channel[ctx].send(  # type:ignore
                    "**Can't play the requested youtube video: link timed out**"
                )
                return await self.next_track(ctx)

        time.sleep(0.1)

        if not ctx.voice_client.is_playing():

            def after(error):
                if error:
                    print(f"Playback error: {error.message}")
                    return

                future = asyncio.run_coroutine_threadsafe(
                    self.next_track(ctx), self.bot.loop
                )
                return future.result()

            ctx.voice_client.play(player, after=after)

        else:
            ctx.voice_client.source = player

        self.queue[ctx].playing = track
        self.queue[ctx].playing_since = time.time()

    @commands.command(aliases=["s"])
    @check_channel
    @check_voice
    @check_bot_voice
    async def skip(self, ctx: commands.Context, *, idx: int = 1):
        """Skips the currently playing track.

        If a parameter is specified, skips to the specified track in the queue instead.
        """
        success_message = (
            "**Skipping current track.**"
            if idx == 1
            else f"**Skipping to track** `{idx}`."
        )

        try:
            self.queue[ctx].remove(list(range(1, idx)))
            await ctx.send(success_message)
            return await self.next_track(ctx)
        except QueueError:
            return await ctx.send(f"**Index** `{idx}` **is not a valid song !**")

    @commands.command()
    @check_channel
    @check_voice
    @check_bot_voice
    async def pause(self, ctx: commands.Context):
        """Pauses the current playback."""
        assert ctx.voice_client is not None

        ctx.voice_client.pause()
        self.paused_at[ctx] = time.time()
        return await ctx.send("**Playback paused.**")

    @commands.command()
    @check_channel
    @check_voice
    @check_bot_connected
    async def resume(self, ctx: commands.Context):
        """Resumes a paused playback."""
        assert ctx.voice_client is not None

        if not ctx.voice_client.is_paused():
            return await ctx.send("**I am not paused.**")
        ctx.voice_client.resume()

        if (
            self.queue[ctx].playing_since is not None
            and self.paused_at[ctx] is not None
        ):
            self.queue[ctx].playing_since += (
                time.time() - self.paused_at[ctx]  # type:ignore
            )

        return await ctx.send("**Playback resumed.**")

    async def cleanup(self, client: discord.VoiceClient):
        if client.guild is not None:
            self.bound_channel[client.guild] = None
            self.queue[client.guild].clear()

        return await client.disconnect()

    @commands.command()
    @check_channel
    @check_voice
    @check_bot_connected
    async def disconnect(self, ctx: commands.Context):
        """Disconnects from current voice channel.

        Also unbounds the bot from any text channels and clears the queue."""
        assert ctx.voice_client is not None
        await self.cleanup(ctx.voice_client)
        return await ctx.send("**Successfully disconnected.**")

    @commands.command(name="queue")
    @check_channel
    @check_voice
    @check_bot_connected
    async def view_queue(self, ctx: commands.Context, *, start: int = 1):
        """Displays the current queue.

        If an argument is given, displays the songs after the specified track.
        """
        try:
            await ctx.send(embed=self.queue[ctx].as_embed(start=start - 1))
        except QueueError:
            await ctx.send(
                f"**Error : start index** `{start}`"
                "** is greater than the queue length !**"
            )

    @commands.command()
    @check_channel
    @check_voice
    @check_bot_connected
    async def remove(self, ctx: commands.Context, *args: int):
        """Removes one or several entries from the queue."""
        try:
            removed_entries = self.queue[ctx].remove(list(args))

            if len(removed_entries) == 1:
                track = removed_entries[0]
                await ctx.send(f"**Successfully removed** `{track.title}`.")
            else:
                await ctx.send(
                    f"**Successfully removed** `{len(removed_entries)}` **tracks.**"
                )
        except QueueError as e:
            await ctx.send(
                "**Invalid indices given for command `remove` : **`{}`".format(
                    ", ".join(map(str, e.args[0]))
                )
            )

    @commands.command()
    @check_channel
    @check_voice
    @check_bot_connected
    async def clear(self, ctx: commands.Context):
        """Clears the track queue."""
        self.queue[ctx].clear()
        await ctx.send("**Queue cleared.**")

    @commands.command()
    @check_channel
    @check_voice
    @check_bot_connected
    async def shuffle(self, ctx: commands.Context):
        """Shuffles the track queue."""
        self.queue[ctx].shuffle()
        await ctx.send("**Successfully shuffled the track queue.**")

    @tasks.loop(seconds=5.0)
    async def check_idle(self):
        bot = self.bot
        for client in bot.voice_clients:

            if is_idle(client):
                if self.idle_since[client.guild] is None:
                    self.idle_since[client.guild] = time.time()

                elif (
                    cast(float, self.idle_since[client.guild]) + MAX_IDLE_TIME
                    < time.time()
                ):
                    log.info(
                        f"Disconnecting due to inactivity in guild {client.guild.name}"
                    )
                    await self.cleanup(client)
                    self.idle_since[client.guild] = None

            else:
                self.idle_since[client.guild] = None
