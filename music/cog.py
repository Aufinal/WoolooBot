import asyncio
import time
from typing import Optional

import discord
from discord.ext import commands
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


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queue = GuildVar(TrackQueue)
        self.bound_channel: GuildVar[Optional[discord.TextChannel]] = GuildVar(
            lambda: None
        )
        self.paused_at: GuildVar[Optional[float]] = GuildVar(lambda: None)

    async def cog_command_error(
        self, ctx: commands.Context, error: commands.CommandError
    ):
        if isinstance(error, MessageableException):
            await ctx.send(error.message)

        return await super().cog_command_error(ctx, error)

    @commands.command()
    @check_channel
    @check_voice
    async def play(self, ctx: commands.Context, *, query: str):
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
            return

        if not track.processed:
            await self.bot.loop.run_in_executor(None, track.update_info)

        embed = track.as_embed()
        embed.add_field(name="Up next", value=next_track, inline=False)

        assert self.bound_channel[ctx] is not None
        await self.bound_channel[ctx].send(embed=embed)  # type: ignore

        if not ctx.voice_client.is_playing():

            def after(error):
                if error:
                    print(f"Playback error: {error.message}")
                    return

                future = asyncio.run_coroutine_threadsafe(
                    self.next_track(ctx), self.bot.loop
                )
                return future.result()

            ctx.voice_client.play(track.as_audio(), after=after)

        else:
            ctx.voice_client.source = track.as_audio()

        self.queue[ctx].playing = track
        self.queue[ctx].playing_since = time.time()

    @commands.command()
    @check_channel
    @check_voice
    @check_bot_voice
    async def skip(self, ctx: commands.Context):
        await ctx.send("**Skipping current track.**")
        return await self.next_track(ctx)

    @commands.command()
    @check_channel
    @check_voice
    @check_bot_voice
    async def pause(self, ctx: commands.Context):
        assert ctx.voice_client is not None

        ctx.voice_client.pause()
        self.paused_at[ctx] = time.time()
        return await ctx.send("**Playback paused.**")

    @commands.command()
    @check_channel
    @check_voice
    @check_bot_connected
    async def resume(self, ctx: commands.Context):
        assert ctx.voice_client is not None

        if not ctx.voice_client.is_paused():
            return await ctx.send("**I am not paused.**")
        ctx.voice_client.resume()

        if (
            self.queue[ctx].playing_since is not None
            and self.paused_at[ctx] is not None
        ):
            self.queue[ctx].playing_since += time.time() - self.paused_at[ctx]

        return await ctx.send("**Playback resumed.**")

    @commands.command()
    @check_channel
    @check_voice
    @check_bot_connected
    async def disconnect(self, ctx: commands.Context):
        assert ctx.voice_client is not None

        self.bound_channel[ctx] = None
        self.queue[ctx].clear()
        await ctx.voice_client.disconnect()
        return await ctx.send("**Successfully disconnected.**")

    @commands.command(name="queue")
    @check_channel
    @check_voice
    @check_bot_connected
    async def view_queue(self, ctx: commands.Context):
        await ctx.send(embed=self.queue[ctx].as_embed())

    @commands.command()
    @check_channel
    @check_voice
    @check_bot_connected
    async def remove(self, ctx: commands.Context, *args: int):
        try:
            removed_entries = self.queue[ctx].remove(list(args))

            if len(removed_entries) == 1:
                track = removed_entries[0]
                await ctx.send(f"**Successfully removed `{track.title}`.**")
            else:
                await ctx.send(
                    f"**Successfully removed `{len(removed_entries)}` tracks.**"
                )
        except QueueError as e:
            await ctx.send(
                "**Invalid indices given for command `remove` : {}**".format(
                    ", ".join(map(str, e.args))
                )
            )
