from discord.ext import commands
import discord
import dbl

from manager import Manager
from manager import check_channel_perms, check_ongoing_tournament, detect_help

from decouple import config

class Basic(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.sql_query = self.bot.sql_query
        self.manager = Manager()

    @ commands.command(name='ping')
    @ check_channel_perms
    @ check_ongoing_tournament
    @ detect_help()
    async def ping_command(self, ctx):
        channel = ctx.channel

        await channel.send(embed=self.manager.create_embed(f'Pong :ping_pong:  |  {round(self.bot.latency, 3)} ms', '', 0xFFA500,
            '', [], [], sign_embed=False))

    @ commands.command(name='help')
    @ check_channel_perms
    @ detect_help()
    async def help_command(self, ctx):
        channel = ctx.channel
        help_field_names = [ctx.prefix + field_name for field_name in ['help', 'prefix', 'enable', 'disable', 'open', 'ping', 'tournament', 'roundrobin', 'bracket', 'vote']]
        help_field_values = ['Shows this message', 'Changes the command prefix for the bot', 
            'Grants alice permission to read and respond to commands in a channel', 'Denies alice permission to read and respond to commands in a channel', 
            'Concludes a tournament in a channel and opens the channel up', 'Returns the latency of the bot', 
            'Creates a tournament with a round-robin followed by a seeded bracket on Challonge', 'Creates a round-robin competition on your Discord server', 
            'Creates a bracket on Challonge using predetermined seeds', 'Vote for alice to receive a special token of gratitude']
        
        embed = self.manager.create_embed('Help', 'alice allows you to play tournaments without leaving the comfort of your Discord server!'
            ' Usage information for each command can be found by passing help into the first argument (i.e. !tournament help). Please consider voting!',
            0xC96FCA, '', help_field_names, help_field_values, footer=['Found a bug? DM koza#5339', ''])
        channel_occupied = channel.overwrites_for(self.manager.get_role_by_name(channel.guild, 'alice tournament')).pair()[0]
        if channel_occupied.read_messages and channel_occupied.send_messages:
            await channel.send(embed=embed)
        else:
            await ctx.message.delete()
            await ctx.author.send(embed=embed)
            
    @ commands.guild_only()
    @ commands.command(name='prefix')
    @ check_channel_perms
    @ check_ongoing_tournament
    @ commands.has_guild_permissions(administrator=True)
    @ detect_help(expected_arg_count=1)
    async def set_prefix_command(self, ctx):
        channel = ctx.channel
        current_prefix = ctx.prefix
        desired_prefix = ctx.message.content[len(current_prefix+ctx.invoked_with):].strip()

        if len(desired_prefix) <= 5 and ' ' not in desired_prefix:
            self.sql_query.insert_and_update('guilds', ['guild_id', 'prefix'], [str(channel.guild.id), desired_prefix], ['guild_id'])        
            await channel.send(embed=self.manager.create_embed(f'Prefix changed from {current_prefix} to {desired_prefix}', '', 0x4f545c,
                '', [], [], sign_embed=False))
        else:
            await channel.send(embed=self.manager.usage_information(ctx.command.name, current_prefix))
    
    @ commands.guild_only()
    @ commands.command(name='enable')
    @ commands.has_guild_permissions(administrator=True)
    @ detect_help(expected_arg_count=1)
    async def enable_channel_command(self, ctx):
        channel = ctx.channel
        author = ctx.author
        current_prefix = ctx.prefix
        toggled_channel_id = ctx.message.content[len(current_prefix+ctx.invoked_with):].strip()
        channel_perms_role = self.manager.get_role_by_name(ctx.guild, 'alice dnd')

        try:
            if toggled_channel_id.startswith('<'):
                toggled_channel_id = toggled_channel_id[2:-1]
            toggled_channel = ctx.guild.get_channel(int(toggled_channel_id))

            await toggled_channel.set_permissions(channel_perms_role, read_messages=True, send_messages=True)
            
            embed = self.manager.create_embed('Enabled Channel', f'Enabled permissions for {toggled_channel.mention} to receive commands.',
                0x5CB3F2, '', [], [], footer=[f'{author.display_name}  \u2022  {self.manager.current_time()}', author.avatar_url])
            await channel.send(embed=embed)
        except Exception as e:
            await channel.send(embed=self.manager.usage_information(ctx.command.name, current_prefix))

    @ commands.guild_only()
    @ commands.command(name='disable')
    @ commands.has_guild_permissions(administrator=True)
    @ detect_help(expected_arg_count=1)
    async def disable_channel_command(self, ctx):
        channel = ctx.channel
        author = ctx.author
        current_prefix = ctx.prefix
        toggled_channel_id = ctx.message.content[len(current_prefix+ctx.invoked_with):].strip()
        channel_perms_role = self.manager.get_role_by_name(ctx.guild, 'alice dnd')

        try:
            if toggled_channel_id.startswith('<'):
                toggled_channel_id = toggled_channel_id[2:-1]
            toggled_channel = ctx.guild.get_channel(int(toggled_channel_id))

            await toggled_channel.set_permissions(channel_perms_role, read_messages=False, send_messages=False)
            
            embed = self.manager.create_embed('Disabled Channel', f'Disabled permissions for {toggled_channel.mention} to receive commands.',
                0xFF577A, '', [], [], footer=[f'{author.display_name}  \u2022  {self.manager.current_time()}', author.avatar_url])
            await channel.send(embed=embed)
        except Exception as e:
            await channel.send(embed=self.manager.usage_information(ctx.command.name, current_prefix))

    @ commands.guild_only()
    @ commands.command(name='open')
    @ check_channel_perms
    @ commands.has_guild_permissions(administrator=True)
    @ detect_help(expected_arg_count=1)
    async def open_channel_command(self, ctx):
        channel = ctx.channel
        author = ctx.author
        current_prefix = ctx.prefix
        tournament_channel_id = ctx.message.content[len(current_prefix+ctx.invoked_with):].strip()
        channel_perms_role = self.manager.get_role_by_name(ctx.guild, 'alice tournament')

        try:
            if tournament_channel_id.startswith('<'):
                tournament_channel_id = tournament_channel_id[2:-1]
            tournament_channel = ctx.guild.get_channel(int(tournament_channel_id))

            await tournament_channel.set_permissions(channel_perms_role, read_messages=True, send_messages=True)
            
            embed = self.manager.create_embed('Channel Opened', f'Ongoing tournament forcibly concluded and {tournament_channel.mention} opened.',
                0x00B400, '', [], [], footer=[f'{author.display_name}  \u2022  {self.manager.current_time()}', author.avatar_url])
            await channel.send(embed=embed)
        except Exception as e:
            await channel.send(embed=self.manager.usage_information(ctx.command.name, current_prefix))

    @ commands.command(name='vote')
    @ check_channel_perms
    @ detect_help()
    async def vote_command(self, ctx):
        channel = ctx.channel
        vote_url = 'https://top.gg/bot/723813871881551932/vote'
        
        if ctx.guild:
            vote_url += f'?guild={ctx.guild.id}&channel={channel.id}'
        
        embed = self.manager.create_embed('Vote', 'If you enjoy what alice does please vote so alice can garner more attention!'
            f' As an incentive, you will receive a special thanks and a reward customized to you. Vote [here]({vote_url}).',
            0xFFD500, '', [], [], url=vote_url)
        channel_occupied = channel.overwrites_for(self.manager.get_role_by_name(channel.guild, 'alice tournament')).pair()[0]
        if channel_occupied.read_messages and channel_occupied.send_messages:
            await channel.send(embed=embed)
        else:
            await ctx.message.delete()
            await ctx.author.send(embed=embed)

    @ commands.command(name='announce')
    @ check_channel_perms
    async def announcement_command(self, ctx):
        user_id = ctx.author.id
        if user_id == int(config('BOT_OWNER_ID')):
            for guild in self.bot.guilds:
                for channel in guild.text_channels:
                    if channel.permissions_for(guild.me).send_messages:
                        await channel.send(ctx.message.content[len(ctx.prefix+ctx.invoked_with):].strip())
                        break

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        channel = ctx.channel

        if isinstance(error, commands.MissingPermissions):
            await channel.send(embed=self.manager.error_information('missing_permissions', ctx.author))


def setup(bot):
    bot.add_cog(Basic(bot))