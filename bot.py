import sqlite3

import discord
from discord.ext import commands
from constants import *
import datetime
from os import mkdir
from config import IDEALIST, SUPPORTER, OPENER, MEMBER, ROLE, GUILD_ID

from error_handler import CommandErrorHandler


class RuMineCog(commands.Cog):
    """Набор фунций для управления ботом"""

    def __init__(self, bot):
        try:
            mkdir(DIR)
        except FileExistsError:
            pass
        finally:
            self.con = sqlite3.connect(DATA_DB_PATH)
            cur = self.con.cursor()
            try:
                cur.execute('''CREATE TABLE users (
                            user_id  STRING  PRIMARY KEY,
                            messages INTEGER,
                            voice    INTEGER,
                            bonus    INTEGER,
                            total    INTEGER);''')
                self.con.commit()
            except sqlite3.OperationalError:
                pass
            except sqlite3.DatabaseError:
                pass
        self.cur = self.con.cursor()

        self.voice = {}
        self.bot = bot

    @commands.command(name="баллы")
    async def get_points(self, ctx):
        if ctx.guild is None:
            return

        if ctx.guild.id != GUILD_ID:
            return

        author = ctx.author.id
        user = await bot.fetch_user(author)
        emb = discord.Embed(color=GREY)
        result = self.cur.execute(f"""SELECT * FROM users 
                                      WHERE user_id = '{author}'""").fetchall()
        if result:

            emb.add_field(name=f'Твои баллы:',
                          value=f'{result[0][4]}',
                          inline=False)
            emb.add_field(name=f'За активность в текстовых каналах:',
                          value=f'{result[0][1]}',
                          inline=False)
            emb.add_field(name=f'За активность в голосовых каналах:',
                          value=f'{result[0][2]}',
                          inline=False)
            emb.add_field(name=f'Бонус / штраф:',
                          value=f'{result[0][3]}',
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

        if ctx.guild.id != GUILD_ID:
            return

        # if aim is None or points is None:
        #     emb = discord.Embed(color=RED)
        #     emb.set_author(name='Ошибка синтаксиса:')
        #     emb.add_field(name='использование команды:',
        #                   value='!добавитьбаллы @name <кол-во>',
        #                   inline=False)
        #     await ctx.semd(embed=emb)
        #     return
        aim = await bot.fetch_user(int(''.join(i for i in aim if i.isdigit())))
        await aim.send(f"Поздравляю! Тебе начислили бонусные баллы: {int(points)}")

        result = self.cur.execute(f"""SELECT * FROM users
                                      WHERE user_id = '{aim.id}'""").fetchall()
        if result:
            self.cur.execute(f"""UPDATE users
                                 SET bonus = {result[0][3] + int(points)},
                                 total = {result[0][4] + int(points)}
                                 WHERE user_id = '{aim.id}'""")
            # self.data[str(aim.id)]['bonus'] += int(points)
        else:
            self.cur.execute(f"""INSERT INTO users(user_id,messages,voice,bonus, total)
                                 VALUES('{aim.id}',0,0,{int(points)},{int(points)})""")

            # self.data[str(aim.id)] = {'messages': 0, 'voice': 0, 'bonus': int(points)}

        self.con.commit()
        await self.roles_check(ctx.channel.guild, ctx.author, result[0][4])

    @commands.command(name="снятьбаллы")
    @commands.has_role(ROLE)
    async def remove_points(self, ctx, aim, points):
        if ctx.guild is None:
            return

        if ctx.guild.id != GUILD_ID:
            return

        aim = await bot.fetch_user(int(''.join(i for i in aim if i.isdigit())))
        await aim.send(f"Мне очень жаль! Тебя оштрафовали: {int(points)}")

        result = self.cur.execute(f"""SELECT * FROM users
                                      WHERE user_id = '{aim.id}'""").fetchall()

        if result:
            self.cur.execute(f"""UPDATE users
                                         SET bonus = {result[0][3] - int(points)},
                                         total = {result[0][4] - int(points)}
                                         WHERE user_id = '{aim.id}'""")
        else:
            self.cur.execute(f"""INSERT INTO users(user_id,messages,voice,bonus)
                                         VALUES('{aim.id}',0,0,{-int(points)},{-int(points)})""")

        self.con.commit()
        await self.roles_check(ctx.channel.guild, ctx.author, result[0][4])

    @commands.command(name="инфо")
    async def info(self, ctx):
        if ctx.guild is None:
            return

        if ctx.guild.id != GUILD_ID:
            return

        aim = await bot.fetch_user(ctx.author.id)
        await aim.send(f"Информация.")

    @commands.command(name="рейтинг")
    async def top(self, ctx):
        if ctx.guild is None:
            return

        if ctx.guild.id != GUILD_ID:
            return

        result = self.cur.execute(f"""SELECT user_id, total
                                      FROM users ORDER BY total DESC LIMIT 10""").fetchall()

        value = '\n'.join(map(lambda x: f'<@{x[0]}> • {x[1]}', result))

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

        if ctx.guild.id != GUILD_ID:
            return

        author = ctx.author.id

        result = self.cur.execute(f"""SELECT * FROM users
                                      WHERE user_id = '{author}'""").fetchall()
        if result:
            self.cur.execute(f"""UPDATE users
                                         SET messages = {result[0][1] + 1},
                                         total = {result[0][4] + 1}
                                         WHERE user_id = '{author}'""")
            await self.roles_check(ctx.channel.guild, ctx.author, result[0][4])
        else:
            self.cur.execute(f"""INSERT INTO users(user_id,messages,voice,bonus, total)
                                         VALUES('{author}',1,0,0,1)""")
        self.con.commit()

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.bot:
            return
        member_id = member.id
        if before.channel is None and after.channel is not None:
            """Подключение к войсу"""
            if after.channel.guild.id != GUILD_ID:
                return
            self.voice[str(member_id)] = int(datetime.datetime.now().timestamp())

        elif before.channel is not None and after.channel is None:
            """Отключение от войса"""
            if before.channel.guild.id != GUILD_ID:
                return
            voice = int(datetime.datetime.now().timestamp() - self.voice[str(member_id)]) // 300
            result = self.cur.execute(f"""SELECT * FROM users
                                                  WHERE user_id = '{member_id}'""").fetchall()
            if result:
                self.cur.execute(f"""UPDATE users
                                     SET voice = {result[0][2] + voice},
                                     total = {result[0][4] + voice}
                                     WHERE user_id = '{member_id}'""")
            else:
                self.cur.execute(f"""INSERT INTO users(user_id,messages,voice,bonus,total)
                                                     VALUES('{member_id}',0,{voice},0,{voice})""")
            self.con.commit()
            await self.roles_check(before.channel.guild, member, result[0][4])

    @staticmethod
    async def roles_check(guild, user, total_points):
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


bot = commands.Bot(command_prefix=COMMAND_PREFIX)
mafia_cog = RuMineCog(bot)
bot.add_cog(mafia_cog)
bot.add_cog(CommandErrorHandler(bot))
