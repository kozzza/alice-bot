from discord.ext import commands
import discord

from decouple import config
import os

bot = commands.Bot(command_prefix='###')
bot.remove_command('help')

if __name__ == '__main__':
	for filename in os.listdir('./cogs_web'):
		if filename.endswith('.py'):
			bot.load_extension(f'cogs_web.{filename[:-3]}')
	
	bot.run(config('DISCORD_BOT_TOKEN'))