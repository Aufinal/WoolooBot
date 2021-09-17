import asyncio

from discord.ext import commands
from youtube_dl.utils import YoutubeDLError

from .queue import TrackQueue
from .utils import check_bot_connected, check_bot_voice, check_channel, check_voice
from .youtube import yt_search


class Music(commands.Cog):
    def __init__(self, bot):
        # TODO: multiple guilds
        self.bot = bot
        self.queue = TrackQueue()
        self.bound_channel = None

    async def cog_command_error(self, ctx, error):
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

        else:
            search_result.requested_by = ctx.author
            embed = self.queue.enqueue(search_result)
            await self.speak(embed=embed)

        if not ctx.voice_client.is_playing():
            return await self.next_track(ctx)

    async def next_track(self, ctx):
        if ctx.voice_client is None:
            return

        (track, embed) = self.queue.pop()

        if track is None:
            print("Track is None")
            ctx.voice_client.stop()
            return

        if not track.processed:
            print("Processing...")
            await self.bot.loop.run_in_executor(None, track.update_info)

        await self.speak(embed=embed)

        if not ctx.voice_client.is_playing():

            def after(error):
                if error:
                    print(f"Playback error: {error}")
                    return

                future = asyncio.run_coroutine_threadsafe(
                    self.next_track(ctx), self.bot.loop
                )

                try:
                    future.result()
                except BaseException:
                    pass

            ctx.voice_client.play(track.as_audio(), after=after)

        else:
            ctx.voice_client.source = track.as_audio()

    @commands.command()
    @check_channel()
    @check_voice()
    @check_bot_voice()
    async def skip(self, ctx):
        await ctx.send("**Skipping current track.**")
        return await self.next_track(ctx)

    @commands.command()
    @check_channel()
    @check_voice()
    @check_bot_voice()
    async def pause(self, ctx):
        ctx.voice_client.pause()
        return await ctx.send("**Playback paused.**")

    @commands.command()
    @check_channel()
    @check_voice()
    @check_bot_connected()
    async def resume(self, ctx):
        if not ctx.voice_client.is_paused():
            return await ctx.send("**I am not paused.**")
        ctx.voice_client.resume()
        return await ctx.send("**Playback resumed.**")

    @commands.command()
    @check_channel()
    @check_voice()
    @check_bot_connected()
    async def disconnect(self, ctx):
        self.bound_channel = None
        self.queue.reset()
        await ctx.voice_client.disconnect()
        return await ctx.send("**Successfully disconnected.**")
