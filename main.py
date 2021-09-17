from discord.ext import commands

from music.cog import Music

bot = commands.Bot(
    command_prefix=commands.when_mentioned_or(">"),
    description="Wooloo's favourite music bot",
)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("------")


bot.add_cog(Music(bot))
bot.run("ODg3MzczNjAyMjMwNTIxODg2.YUDNEQ.ktfn89y23cp0p2IMs1pJYyNlYW4")
