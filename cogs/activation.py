from discord.ext import commands
import discord

from manager import Manager

import random
import json

class Activation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.sql_query = self.bot.sql_query
        self.manager = Manager()
    
    @ commands.Cog.listener()
    async def on_ready(self):
        print(f'We have logged in as {self.bot.user}')
        await self.bot.change_presence(activity=discord.Game(name=f"!help | {len(list(self.bot.guilds))} guilds"))
    
    @ commands.Cog.listener()
    async def on_guild_join(self, guild):
        self.sql_query.insert_and_update('guilds', ['guild_id', 'prefix'], [str(guild.id), '!'], [])
        disable_channel_role = await guild.create_role(name='alice dnd', colour=discord.Colour(0xFF4500))
        ongoing_tournament_role = await guild.create_role(name='alice tournament', colour=discord.Colour(0xFFE614))

        introduced = False
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages and not introduced:
                await channel.set_permissions(disable_channel_role, read_messages=True, send_messages=True)
                
                hellos = json.load(open('./static/text/hellos.json'))
                random_hello = random.choice(list(hellos))
                embed = self.manager.create_embed(hellos[random_hello],
                    'Thanks for inviting me to your server. Get started with !help.\nConsider voting if you like what I do :)',
                    0x6FCE7B, 'attachment://alice.png', ['Vote'], ['[Link](https://top.gg/bot/723813871881551932/vote)'], 
                    footer=[f'Your random hello was in {random_hello}!', ''])
                await channel.send(embed=embed, file=discord.File('./static/images/alice.png', filename='alice.png'))
                introduced = True
            else:
                await channel.set_permissions(disable_channel_role, read_messages=False, send_messages=False)
            
            await channel.set_permissions(ongoing_tournament_role, read_messages=True, send_messages=True)
        
        await self.bot.change_presence(activity=discord.Game(name=f"!help | {len(list(self.bot.guilds))} guilds"))

    @ commands.Cog.listener()
    async def on_guild_remove(self, guild):
        await self.manager.get_role_by_name(guild, 'alice dnd').delete()
        await self.manager.get_role_by_name(guild, 'alice tournament').delete()
    
    @ commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        disable_channel_role = self.manager.get_role_by_name(channel.guild, 'alice dnd')
        ongoing_tournament_role = self.manager.get_role_by_name(channel.guild, 'alice tournament')

        await channel.set_permissions(disable_channel_role, read_messages=False, send_messages=False)
        await channel.set_permissions(ongoing_tournament_role, read_messages=True, send_messages=True)


def setup(bot):
    bot.add_cog(Activation(bot))