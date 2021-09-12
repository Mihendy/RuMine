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
                            messages REAL,
                            voice    REAL,
                            bonus    REAL,
                            total    REAL);''')
                self.con.commit()
            except sqlite3.OperationalError:
                pass
            except sqlite3.DatabaseError:
                pass
        self.cur = self.con.cursor()
        self.voice = {}
        bot.remove_command('help')
        self.bot = bot
        self.bot.activity = discord.Activity(name='!help', type=discord.ActivityType.listening)
        self.messages = {}

    @commands.command(pass_context=True, aliases=['points', 'баллы'])
    async def get_points(self, ctx):
        if ctx.guild is None:
            return

        if ctx.guild.id != GUILD_ID:
            return

        author = ctx.author.id
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
        await ctx.reply(embed=emb)

    @commands.has_role(ROLE)
    @commands.command(pass_context=True, aliases=['add_points', 'добавитьбаллы'])
    async def _add_points(self, ctx, aim, points):
        if ctx.guild is None:
            return

        if ctx.guild.id != GUILD_ID:
            return

        aim = await bot.fetch_user(int(''.join(i for i in aim if i.isdigit())))

        await ctx.send(f"{aim.mention}, поздравляю! Тебе начислили бонусные баллы: {int(points)}")

        result = self.cur.execute(f"""SELECT * FROM users
                                      WHERE user_id = '{aim.id}'""").fetchall()
        if result:
            self.cur.execute(f"""UPDATE users
                                 SET bonus = {result[0][3] + int(points)},
                                 total = {result[0][4] + int(points)}
                                 WHERE user_id = '{aim.id}'""")
            await self.roles_check(ctx.channel.guild, ctx.author, result[0][4] + int(points))
        else:
            self.cur.execute(f"""INSERT INTO users(user_id,messages,voice,bonus,total)
                                 VALUES('{aim.id}',0,0,{int(points)},{int(points)})""")
            await self.roles_check(ctx.channel.guild, ctx.author, int(points))
        self.con.commit()

    @commands.has_role(ROLE)
    @commands.command(pass_context=True, aliases=['remove_points', 'снятьбаллы'])
    async def _remove_points(self, ctx, aim, points):
        if ctx.guild is None:
            return

        if ctx.guild.id != GUILD_ID:
            return

        aim = await bot.fetch_user(int(''.join(i for i in aim if i.isdigit())))
        await ctx.send(f"{aim.mention}, мне очень жаль! Тебя оштрафовали: {int(points)}")

        result = self.cur.execute(f"""SELECT * FROM users
                                      WHERE user_id = '{aim.id}'""").fetchall()

        if result:
            self.cur.execute(f"""UPDATE users
                                         SET bonus = {result[0][3] - int(points)},
                                         total = {result[0][4] - int(points)}
                                         WHERE user_id = '{aim.id}'""")
        else:
            self.cur.execute(f"""INSERT INTO users(user_id,messages,voice,bonus,total)
                                         VALUES('{aim.id}',0,0,{-int(points)},{-int(points)})""")

        self.con.commit()

    @commands.command(pass_context=True, aliases=['help', 'info', 'инфо'])
    async def information(self, ctx):
        if ctx.guild is None:
            return

        if ctx.guild.id != GUILD_ID:
            return

        await ctx.reply(''.join(open('info.txt', encoding='UTF-8').readlines()))

    @commands.command(pass_context=True, aliases=['рейтинг', 'rating'])
    async def top(self, ctx):
        if ctx.guild is None:
            return

        if ctx.guild.id != GUILD_ID:
            return

        result = enumerate(self.cur.execute(f"""SELECT user_id, total
                                      FROM users ORDER BY total DESC LIMIT 10""").fetchall())

        value = '\n'.join(map(lambda x: f'`{x[0] + 1}.` <@{x[1][0]}> • {x[1][1]}', result))

        emb = discord.Embed(color=GREEN)

        result = self.cur.execute(
            f"""SELECT user_id, total FROM users ORDER BY total DESC LIMIT {TOP_LIMIT}""").fetchall()

        if ctx.author.id in list(map(lambda x: x[0], result)):
            ind = list(map(lambda x: x[0], result)).index(ctx.author.id)
            if ind not in range(0, 10):
                value += '\n`...`\n' + f'`{ind + 1}.` <@{result[ind][0]}> • {result[ind][1]}'
        else:
            value += '\n`...`\n' + f'*Вы не входите в топ {TOP_LIMIT} по рейтингу*'
        emb.add_field(name='Лидеры:',
                      value=value,
                      inline=False)
        await ctx.reply(embed=emb)

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

        premium_subscribers = tuple(map(lambda x: x.id, ctx.guild.premium_subscribers))

        if author not in self.messages:
            self.messages[author] = int(datetime.datetime.now().timestamp())
            points = 1
        elif author in premium_subscribers:
            dt = int(datetime.datetime.now().timestamp())
            if dt - self.messages[author] > 65:
                points = 1.5
            elif dt - self.messages[author] > 45:
                points = 1
            elif dt - self.messages[author] > 15:
                points = 0.5
            else:
                points = 0.1
        else:
            dt = int(datetime.datetime.now().timestamp())
            if dt - self.messages[author] > 65:
                points = 1
            elif dt - self.messages[author] > 45:
                points = 0.5
            elif dt - self.messages[author] > 15:
                points = 0.2
            else:
                points = 0
            self.messages[author] = dt
        if result:
            self.cur.execute(f"""UPDATE users
                                         SET messages = {"%.1f" % (result[0][1] + points)},
                                         total = {"%.1f" % (result[0][4] + points)}
                                         WHERE user_id = '{author}'""")
            await self.roles_check(ctx.channel.guild, ctx.author, result[0][4])
        else:
            self.cur.execute(f"""INSERT INTO users(user_id,messages,voice,bonus, total)
                                         VALUES('{author}',{"%.1f" % points},0,0,{"%.1f" % points})
                                """)
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
                await self.roles_check(before.channel.guild, member, result[0][4] + voice)
            else:
                self.cur.execute(f"""INSERT INTO users(user_id,messages,voice,bonus,total)
                                                     VALUES('{member_id}',0,{voice},0,{voice})""")
                await self.roles_check(before.channel.guild, member, voice)
            self.con.commit()

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


intents = discord.Intents.default()
bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents)
bot_cog = RuMineCog(bot)
bot.add_cog(bot_cog)
bot.add_cog(CommandErrorHandler(bot))
