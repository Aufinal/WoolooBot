import functools
from time import gmtime, strftime

import discord.ext.commands as commands


class MessageableException(commands.CommandError):
    message: str


class NotInVoiceChannelFailure(MessageableException):
    message = "**You need to be in a voice channel to use this command.**"
    pass


class WrongVoiceChannelFailure(MessageableException):
    message = "**You are not in the right voice channel.**"
    pass


class WrongTextChannelFailure(MessageableException):
    pass


class BotNotPlayingFailure(commands.CheckFailure):
    message = "**I am not playing anything right now.**"
    pass


class BotNotConnectedFailure(commands.CheckFailure):
    message = "**I am not connected to a voice channel.**"
    pass


def check_voice(func):
    @functools.wraps(func)
    async def _wrapped_func(self, ctx, *args, **kwargs):
        bot_voice = ctx.voice_client
        user_voice = ctx.author.voice

        if user_voice is None:
            raise NotInVoiceChannelFailure
        elif (bot_voice is not None) and (bot_voice.channel != user_voice.channel):
            raise WrongVoiceChannelFailure(bot_voice.channel, user_voice.channel)

        return await func(self, ctx, *args, **kwargs)

    return _wrapped_func


def check_channel(func):
    @functools.wraps(func)
    async def _wrapped_func(self, ctx, *args, **kwargs):
        if (
            ctx.cog.bound_channel[ctx] is not None
            and ctx.cog.bound_channel[ctx] != ctx.channel
        ):
            raise WrongTextChannelFailure(ctx.cog.bound_channel, ctx.channel)

        return await func(self, ctx, *args, **kwargs)

    return _wrapped_func


def check_bot_voice(func):
    @functools.wraps(func)
    async def _wrapped_func(self, ctx, *args, **kwargs):
        if not ctx.voice_client.is_playing():
            raise BotNotPlayingFailure

        return await func(self, ctx, *args, **kwargs)

    return _wrapped_func


def check_bot_connected(func):
    @functools.wraps(func)
    async def _wrapped_func(self, ctx, *args, **kwargs):
        if not ctx.voice_client.is_connected():
            raise BotNotConnectedFailure

        return await func(self, ctx, *args, **kwargs)

    return _wrapped_func


def format_time(seconds: float) -> str:
    """Takes a time in seconds and formats in HH:mm:ss or mm:ss,
    depending on whether it's above an hour."""

    strformat = "%M:%S" if seconds < 3600 else "%H:%M:%S"
    return strftime(strformat, gmtime(seconds))
