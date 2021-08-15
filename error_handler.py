from constants import RED
import discord
import traceback
import sys
from discord.ext import commands
from constants import COMMAND_PREFIX


class CommandErrorHandler(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        embed = discord.Embed()

        if hasattr(ctx.command, 'on_error'):
            return

        cog = ctx.cog
        if cog:
            if cog._get_overridden_method(cog.cog_command_error) is not None:
                return

        ignored = (commands.CommandNotFound,)

        error = getattr(error, 'original', error)

        if isinstance(error, ignored):
            return
        if isinstance(error, commands.DisabledCommand):
            return
        if isinstance(error, commands.MissingRole):
            return
        if isinstance(error, commands.MissingRequiredArgument):
            emb = discord.Embed(color=RED)
            emb.set_author(name='Ошибка синтаксиса:')
            emb.add_field(name='Использование команды:',
                          value=f'!{ctx.command} @name <кол-во>',
                          inline=False)
            await ctx.send(embed=emb)
            return
        else:
            # All other Errors not returned come here. And we can just print the default TraceBack.
            print('Обнаружена ошибка в команде {}:'.format(ctx.command), file=sys.stderr)
            traceback.print_exception(type(error), error, error.__traceback_, file=sys.stderr)