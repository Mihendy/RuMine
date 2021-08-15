import discord
from discord.ext import commands
from constants import *
import datetime
import json
from os.path import exists
from os import mkdir
from config import IDEALIST, SUPPORTER, OPENER, MEMBER, ROLE

from error_handler import CommandErrorHandler


class RuMineCog(commands.Cog):
    """Набор фунций для управления ботом"""

    def __init__(self, bot):
        self.data = json.load(open(DATA_JSON_PATH, 'r')) if exists(DATA_JSON_PATH) else {}
        self.voice = {}
        self.bot = bot

    @commands.command(name="баллы")
    async def get_points(self, ctx):
        if ctx.guild is None:
            return

        author = ctx.author.id
        user = await bot.fetch_user(int(author))
        emb = discord.Embed(color=GREY)
        # emb.set_author(name='Баллы:', icon_url=ctx.author.avatar_url)
        if str(author) in self.data:
            emb.add_field(name=f'Твои баллы:',
                          value=f'{sum(self.data[str(author)].values())}',
                          inline=False)
            emb.add_field(name=f'За активность в текстовых каналах:',
                          value=f'{self.data[str(author)]["messages"]}',
                          inline=False)
            emb.add_field(name=f'За активность в голосовых каналах:',
                          value=f'{self.data[str(author)]["voice"]}',
                          inline=False)
            emb.add_field(name=f'Бонус / штраф:',
                          value=f'{self.data[str(author)]["bonus"]}',
                          inline=False)
        else:
            emb.add_field(name=f'Твои баллы:',
                          value=f'{0}',
                          inline=False)
        await user.send(embed=emb)

    @commands.has_role(ROLE)
    @commands.command(name="добавитьбаллы")
    async def add_points(self, ctx, aim, points):
        if ctx.guild is None:
            return

        if aim is None or points is None:
            emb = discord.Embed(color=RED)
            emb.set_author(name='Ошибка синтаксиса:')
            emb.add_field(name='использование команды:',
                          value='!добавитьбаллы @name <кол-во>',
                          inline=False)
            await ctx.semd(embed=emb)
            return
        aim = await bot.fetch_user(int(''.join(i for i in aim if i.isdigit())))
        await aim.send(f"Поздравляю! Тебе начислили бонусные баллы: {int(points)}")

        if str(aim.id) in self.data:
            self.data[str(aim.id)]['bonus'] += int(points)
        else:
            self.data[str(aim.id)] = {'messages': 0, 'voice': 0, 'bonus': int(points)}
        await self.roles_check(ctx.channel.guild, ctx.author)

    @commands.command(name="снятьбаллы")
    @commands.has_role(ROLE)
    async def remove_points(self, ctx, aim, points):
        if ctx.guild is None:
            return

        aim = await bot.fetch_user(int(''.join(i for i in aim if i.isdigit())))
        await aim.send(f"Мне очень жаль! Тебя оштрафовали: {int(points)}")

        if str(aim.id) in self.data:
            self.data[str(aim.id)]['bonus'] -= int(points)
        else:
            self.data[str(aim.id)] = {'messages': 0, 'voice': 0, 'bonus': -int(points)}
        await self.roles_check(ctx.channel.guild, ctx.author)

    @commands.command(name="инфо")
    async def info(self, ctx):
        if ctx.guild is None:
            return
        aim = await bot.fetch_user(ctx.author.id)
        await aim.send(f"Информация.")

    @commands.command(name="рейтинг")
    async def top(self, ctx):
        if ctx.guild is None:
            return
        output = []
        for person, points in self.data.items():
            output.append((person, sum(points.values())))
            # output.append(((await bot.fetch_user(int(person))).mention, sum(points.values())))
        output.sort(key=lambda x: x[1], reverse=True)
        value = '\n'.join(map(lambda x: f'{x[0]} • {x[1]}', output[:10]))
        emb = discord.Embed(color=GREEN)
        emb.add_field(name='Лидеры:',
                      value=value,
                      inline=False)
        await ctx.send(embed=emb)

    @commands.Cog.listener()
    async def on_message(self, ctx):
        """Слушатель сообщений"""

        if ctx.author == self.bot.user or ctx.content.startswith(COMMAND_PREFIX) or ctx.author.bot:
            return

        if isinstance(ctx.channel, discord.DMChannel):
            return

        author = ctx.author.id

        if str(author) in self.data:
            self.data[str(author)]['messages'] += 1
            await self.roles_check(ctx.channel.guild, ctx.author)
        else:
            self.data[str(author)] = {'messages': 1, 'voice': 0, 'bonus': 0}

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        member_id = member.id
        if before.channel is None and after.channel is not None:
            """Подключение к войсу"""
            self.voice[str(member_id)] = int(datetime.datetime.now().timestamp())

        elif before.channel is not None and after.channel is None:
            """Отключение от войса"""
            voice = int(datetime.datetime.now().timestamp() - self.voice[str(member_id)]) // 300
            if str(member_id) in self.data:
                self.data[str(member_id)]['voice'] += voice
            else:
                self.data[str(member_id)] = {'messages': 0, 'voice': voice, 'bonus': 0}
            await self.roles_check(before.channel.guild, member)

    async def roles_check(self, guild, user):
        total_points = sum(self.data[str(user.id)].values())
        if total_points > 30000:
            discord_role = guild.get_role(IDEALIST)
            await user.add_roles(discord_role)
        if total_points > 1000:
            discord_role = guild.get_role(SUPPORTER)
            await user.add_roles(discord_role)
        if total_points > 500:
            discord_role = guild.get_role(MEMBER)
            await user.add_roles(discord_role)
        if total_points > 100:
            discord_role = guild.get_role(OPENER)
            await user.add_roles(discord_role)
        self.save_changes()

    def save_changes(self):
        try:
            mkdir(DIR)
        except FileExistsError:
            pass
        finally:
            with open(DATA_JSON_PATH, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=4)


bot = commands.Bot(command_prefix=COMMAND_PREFIX)
mafia_cog = RuMineCog(bot)
bot.add_cog(mafia_cog)
bot.add_cog(CommandErrorHandler(bot))
