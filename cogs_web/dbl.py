from discord.ext import commands, tasks
import discord
import dbl

from sql_query import initialize_connection, SQLQuery
from manager import Manager
from stitcher import Stitcher

from decouple import config
from os import environ

class TopGG(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.sql_query = SQLQuery(initialize_connection())
        self.manager = Manager()
        self.stitcher = Stitcher()
        self.dbl_token = config('DBL_TOKEN')
        self.webhook_auth_token = config('ALICE_WEBHOOK_AUTH_TOKEN')
        self.dblpy = dbl.DBLClient(self.bot, self.dbl_token, autopost=True, webhook_path='/dblwebhook', webhook_auth=self.webhook_auth_token, webhook_port=environ.get("PORT", 8000))

    @ commands.Cog.listener()
    async def on_dbl_vote(self, data):
        user_id = int(data['user'])
        user = await self.bot.fetch_user(user_id)
        thumbnail_data = self.stitcher.stitch_images(f'https://cdn.discordapp.com/avatars/{user.id}/{user.avatar}.png?size=1024',
        './static/images/medal.png')

        try:
            query_string_params = data['query'][1:].split('&')
            param_dict = {param.split('=')[0]:int(param.split('=')[1]) for param in query_string_params}
        except Exception as e:
            param_dict = {}
            print(e, param_dict)

        try:
            if param_dict:
                guild_triggered_in = [guild for guild in self.bot.guilds if guild.id == param_dict.get('guild')][0]
                channel_trigged_in = guild_triggered_in.get_channel(param_dict.get('channel'))
                embed = self.manager.create_embed(f'{user.name} has voted!', 'Thank you valued patron for supporting alice.'
                ' Your contribution will not go in vain as I award you the highest prestige I can bestow.'
                ' Your name will echo through the decades to come, enscribed with the flow of light on alloy whose origins stem from the creation of Earth.'
                ' Now come hero, accept your award and be off to privilege our world with more of your good deeds.',
                0xFFA500, 'attachment://user_awarded.png', ['Award'], ['You got a one of a kind medallion!'], 
                footer=[f'{user.name}  \u2022  {self.manager.current_time()}', user.avatar_url])
                await channel_trigged_in.send(embed=embed, file=discord.File(thumbnail_data, 'user_awarded.png'))

                self.sql_query.update_by_increment('guilds', ['vote_count'], ['guild_id'], [[param_dict.get('guild')]])
            
            else:
                embed = self.manager.create_embed('You voted!', 'Thank you valued patron for supporting alice.'
                ' Your contribution will not go in vain as I award you the highest prestige I can bestow.'
                ' Your name will echo through the decades to come, enscribed with the flow of light on alloy whose origins stem from the creation of Earth.'
                ' Now come hero, accept your award and be off to privilege our world with more of your good deeds.',
                0xFFA500, 'attachment://user_awarded.png', ['Award'], ['You got a one of a kind medallion!'],
                footer=[f'{user.name}  \u2022  {self.manager.current_time()}', user.avatar_url])
                await user.send(embed=embed, file=discord.File(thumbnail_data, 'user_awarded.png'))

        except Exception as e:
            print('dbl_vote ' + str(e))

    @ commands.Cog.listener()
    async def on_dbl_test(self, data):
        print(data)


def setup(bot):
    bot.add_cog(TopGG(bot))