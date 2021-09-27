from typing import Callable, Dict, Generic, TypeVar

from discord.ext import commands

T = TypeVar("T")


class GuildVar(Generic[T]):
    def __init__(self, constructor: Callable[[], T]):
        self.constructor = constructor
        self.guild_dict: Dict[int, T] = dict()

    def __getitem__(self, ctx: commands.Context):
        if ctx.guild is None:
            raise commands.NoPrivateMessage

        return self.guild_dict.setdefault(ctx.guild.id, self.constructor())

    def __setitem__(self, ctx: commands.Context, value: T):
        if ctx.guild is None:
            raise commands.NoPrivateMessage

        self.guild_dict[ctx.guild.id] = value
