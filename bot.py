from discord.ext import commands
import discord

import sql_query 
from sql_query import initialize_connection, SQLQuery
from manager import Manager

from decouple import config
import os

initialize_connection()
sql_query = SQLQuery()
manager = Manager()

command_names = [alias for command in manager.command_json.values() for alias in command['aliases']]

async def get_prefix(bot, message):
	prefix = ['!']
	split_contents = message.content.split()
	if len(split_contents):
		if isinstance(message.channel, discord.channel.TextChannel) and [True for name in command_names if split_contents[0].endswith(name)]:
			print(message.content, message.guild.name)
			prefix = list(sql_query.select_data('guilds', ['prefix'], condition=[['guild_id'], [str(message.guild.id)]])[0])
	
	return commands.when_mentioned_or(*prefix)(bot, message)

bot = commands.Bot(command_prefix=get_prefix, case_insensitive=True)
bot.remove_command('help')

bot.sql_query = sql_query # add sql_query attribute to bot object as not to initialize a new pool for every cog

if __name__ == '__main__':
	for filename in os.listdir('./cogs'):
		if filename.endswith('.py'):
			bot.load_extension(f'cogs.{filename[:-3]}')
	
	bot.run(config('DISCORD_BOT_TOKEN'))