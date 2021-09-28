from typing import Callable, Dict, Generic, TypeVar, Union

import discord
from discord.ext import commands

T = TypeVar("T")
# Represents a type that contains a guild ID
GuildIdProxy = Union[commands.Context, discord.Guild, int]


def _get_guild_id(proxy: GuildIdProxy) -> int:
    """Extracts the guild ID from its parameter."""
    if isinstance(proxy, commands.Context):
        if proxy.guild is None:
            raise commands.NoPrivateMessage
        return proxy.guild.id
    elif isinstance(proxy, discord.Guild):
        return proxy.id
    else:
        return proxy


class GuildVar(Generic[T]):
    def __init__(self, constructor: Callable[[], T]):
        self.constructor = constructor
        self.guild_dict: Dict[int, T] = dict()

    def __getitem__(self, param: GuildIdProxy):
        return self.guild_dict.setdefault(_get_guild_id(param), self.constructor())

    def __setitem__(self, param: GuildIdProxy, value: T):
        self.guild_dict[_get_guild_id(param)] = value
