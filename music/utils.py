import discord.ext.commands as commands


class NotInVoiceChannelFailure(commands.CheckFailure):
    message = "**You need to be in a voice channel to use this command.**"
    pass


class WrongVoiceChannelFailure(commands.CheckFailure):
    message = "**You are not in the right voice channel.**"
    pass


class WrongTextChannelFailure(commands.CheckFailure):
    pass


class BotNotPlayingFailure(commands.CheckFailure):
    message = "**I am not playing anything right now.**"
    pass


def check_voice():
    def predicate(ctx):
        bot_voice = ctx.voice_client
        user_voice = ctx.author.voice

        if user_voice is None:
            raise NotInVoiceChannelFailure
        elif (bot_voice is not None) and (bot_voice.channel != user_voice.channel):
            raise WrongVoiceChannelFailure

        return True

    return commands.check(predicate)


def check_channel():
    def predicate(ctx):
        if ctx.cog.bound_channel is not None and ctx.cog.bound_channel != ctx.channel:
            raise WrongTextChannelFailure

        return True

    return commands.check(predicate)


def check_bot_voice():
    def predicate(ctx):
        if not ctx.voice_client.is_playing():
            raise BotNotPlayingFailure

        return True

    return commands.check(predicate)
