from discord.ext import commands
import discord

from sql_query import SQLQuery
from manager import Manager

from decouple import config
import os

command_names = [alias for command in Manager().command_json.values() for alias in command['aliases']]

async def get_prefix(bot, message):
	prefix = ['!']
	split_contents = message.content.split()
	if len(split_contents):
		if isinstance(message.channel, discord.channel.TextChannel) and [True for name in command_names if split_contents[0].endswith(name)]:
			print(message.content, message.guild.name)
			prefix = list(SQLQuery().select_data('guilds', ['prefix'], condition=[['guild_id'], [str(message.guild.id)]])[0])
	
	return commands.when_mentioned_or(*prefix)(bot, message)

bot = commands.Bot(command_prefix=get_prefix)
bot.remove_command('help')

if __name__ == '__main__':
	for filename in os.listdir('./cogs'):
		if filename.endswith('.py'):
			bot.load_extension(f'cogs.{filename[:-3]}')
	
	bot.run(config('DISCORD_BOT_TOKEN'))