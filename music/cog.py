import asyncio
from typing import List

from discord.ext import commands
from discord.ext.commands.errors import CommandError
from youtube_dl.utils import YoutubeDLError

from .utils import (
    check_channel,
    check_voice,
    check_bot_voice,
)
from .youtube import yt_search, YoutubePlaylist, YoutubeTrack


class Music(commands.Cog):
    def __init__(self, bot):
        # TODO: multiple guilds
        self.bot = bot
        self.queue: List[YoutubeTrack] = []
        self.bound_channel = None

    async def cog_command_error(self, ctx, error):
        print(error)
        if isinstance(error, commands.CheckFailure) and hasattr(error, "message"):
            await ctx.send(error.message)

        return await super().cog_command_error(ctx, error)

    async def speak(self, *args, **kwargs):
        # shortcut for sending messages to bound channel
        return await self.bound_channel.send(*args, **kwargs)

    @commands.command()
    @check_voice()
    @check_channel()
    async def play(self, ctx, *, query: str):
        if ctx.voice_client is None:
            # First use: we join the channel of the command's author and bind
            voice_channel = ctx.author.voice.channel
            text_channel = ctx.channel

            self.bound_channel = text_channel
            await voice_channel.connect()
            await self.speak(f"Joined {voice_channel} and bound to {text_channel}.")

        try:
            search_result = await self.bot.loop.run_in_executor(None, yt_search, query)
        except YoutubeDLError as e:
            return await ctx.channel.send(f"Youtube-dl error : {e}")

        if search_result is None:
            return await self.speak("No results found !")

        elif isinstance(search_result, YoutubeTrack):
            self.queue.append(search_result)
            # TODO: embed
            await self.speak(f"New song enqueued: {search_result.title}")

        elif isinstance(search_result, YoutubePlaylist):
            self.queue.extend(search_result.entries)
            # TODO: embed
            await self.speak(
                f"Playlist enqueued: {search_result.title} ({len(search_result.entries)} songs)"
            )

        else:
            raise CommandError("Search result is of unknown type")

        if not ctx.voice_client.is_playing():
            return await self.next_track(ctx)

    async def next_track(self, ctx):
        if ctx.voice_client is None:
            return

        if ctx.voice_client.is_playing():
            ctx.voice_client.stop()

        track = self.queue.pop(0)
        if not track.processed:
            await track.update_info(self.bot.loop)

        await self.speak(f"Now playing : {track.title}")

        def after(error):
            if error:
                print(f"Playback error: {error}")
                return

            future = asyncio.run_coroutine_threadsafe(
                self.next_track(ctx), self.bot.loop
            )

            try:
                future.result()
            except:
                pass

        ctx.voice_client.play(track.as_audio(), after=after)

    @commands.command()
    @check_voice()
    @check_channel()
    @check_bot_voice()
    async def skip(self, ctx):
        return await self.next_track(ctx)
