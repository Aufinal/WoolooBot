from typing import Union

import discord
from discord.ext import commands
from youtube_dl.utils import YoutubeDLError

from ..youtube_utils import yt_search


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queue = []  # we want to be able to display all songs in queue

    @commands.command()
    async def play(self, ctx, *, query: str):
        self_voice = ctx.voice_client
        user_voice = ctx.author.voice

        try:
            tracks = await self.bot.loop.run_in_executor(None, yt_search, query)
            self.queue.extend(tracks)
        except YoutubeDLError as e:
            return await ctx.channel.send(f"Youtube-dl error : {e}")
