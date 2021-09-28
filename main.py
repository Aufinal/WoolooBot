import logging
from os import getenv

import discord
from discord.ext import commands

from music.cog import Music

logging.basicConfig(level=logging.INFO)

bot = commands.Bot(
    command_prefix=commands.when_mentioned_or(">"),
    description="Wooloo's favourite music bot",
    activity=discord.Game(name=">help | Wooloo supremacy"),
)


@bot.event
async def on_ready():
    assert bot.user is not None
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("------")


bot.add_cog(Music(bot))
bot.run(getenv("TOKEN"))
