import discord

from datetime import datetime
import json, copy
import functools
import traceback

class Manager():
    def __init__(self):
        self.command_json = json.load(open('./static/text/command_info.json'))
        self.error_json = json.load(open('./static/text/error_info.json'))

    def current_time(self):
        return datetime.strftime(datetime.now(), "%I:%M %p")

    def get_role_by_name(self, guild, role_name):
        for role in guild.roles:
            if role.name == role_name:
                return role

    def usage_information(self, command_name, prefix):
        command_dict = copy.deepcopy(self.command_json)[command_name]
        field_names = []
        field_values = []

        command_description = command_dict.pop('description')
        command_dict['usage'] = prefix + command_dict['usage']

        for k, v in command_dict.items():
            field_names.append(k.capitalize())
            formatted_val = '\n'.join(v) if type(v) == list else str(v)
            field_values.append(formatted_val)

        return self.create_embed(f'Usage: {command_name}', command_description, 0xA9A9A9, '', field_names, field_values)

    def error_information(self, error_name, author):
        error_dict = copy.deepcopy(self.error_json)[error_name]
        field_names = []
        field_values = []

        error_description = error_dict.pop('description')

        for k, v in error_dict.items():
            field_names.append(k.capitalize())
            formatted_val = ','.join(v) if type(v) == list else str(v)
            field_values.append(formatted_val)

        formatted_error_name = ' '.join([word.capitalize() for word in error_name.split('_')])
        
        return self.create_embed(f'Error: {formatted_error_name}', error_description, 0xFF3000, '', field_names, field_values, 
        footer=[f'{author.display_name}  \u2022  {self.current_time()}', author.avatar_url])

    def create_embed(self, title, description, color, thumbnail, field_names, field_values, footer=[], url='', sign_embed=True):
        embed = discord.Embed(title=title, description=description, color=color)
        if url:
            embed.url = url
        if sign_embed:
            embed.set_author(name="KZ", url="https://github.com/kozzza/alice-bot")
        if footer:
            embed.set_footer(text=footer[0], icon_url=footer[1])
        embed.set_thumbnail(url=thumbnail)
        for i in range(len(field_names)):
            embed.add_field(name=field_names[i], value=field_values[i], inline=False)
        return embed

def detect_help(expected_arg_count=0, split_by=None):
    """Detect commands with missing arguments or "help" as the first argument"""
    def decorator(coro):
        @functools.wraps(coro)
        async def wrapper(*args, **kwargs):
            ctx = args[1]
            channel = ctx.channel
            command_name = ctx.command.name
            curr_prefix = ctx.prefix
            command_args_str = ctx.message.content[len(curr_prefix+ctx.invoked_with):].strip()
            command_args = [command_args_str] if split_by == None else command_args_str.split(split_by)
            command_args = list(filter(None, command_args))
            manager = Manager()
            
            try:
                channel_occupied = channel.overwrites_for(manager.get_role_by_name(channel.guild, 'alice tournament')).pair()[0]
                if not expected_arg_count and not len(command_args):
                    return await coro(*args, **kwargs)
                elif command_args[0] == 'help' or len(command_args) < expected_arg_count:
                    if not channel_occupied.read_messages and not channel_occupied.send_messages:
                        await ctx.message.delete()
                        await ctx.author.send(embed=manager.usage_information(command_name, curr_prefix))
                    else:
                        await channel.send(embed=manager.usage_information(command_name, curr_prefix))
                    return None
                return await coro(*args, **kwargs)

            except IndexError:
                if not channel_occupied.read_messages and not channel_occupied.send_messages:
                    await ctx.message.delete()
                    await ctx.author.send(embed=manager.usage_information(command_name, curr_prefix))
                else:
                    await channel.send(embed=manager.usage_information(command_name, curr_prefix))

            return None

        return wrapper

    return decorator

def check_channel_perms(coro):
    """Verify that channel is enabled for alice to receive commands in"""
    @functools.wraps(coro)
    async def wrapper(*args, **kwargs):
        ctx = args[1]
        channel = ctx.channel
        author = ctx.author
        manager = Manager()
        
        if isinstance(ctx.channel, discord.channel.TextChannel):
            channel_perms = channel.overwrites_for(manager.get_role_by_name(channel.guild, 'alice dnd')).pair()[0]
            if channel_perms.read_messages and channel_perms.send_messages:
                return await coro(*args, **kwargs)
            
            embed = manager.error_information('channel_disabled', author)
            embed.add_field(name='Guild', value=ctx.guild.name, inline=False)
            embed.add_field(name='Channel', value=f'#{channel.name}', inline=False)
            await author.send(embed=embed)
            return None
        
        return await coro(*args, **kwargs)

    return wrapper

def check_ongoing_tournament(coro):
    """Verify that channel is open for a new tournament"""
    @functools.wraps(coro)
    async def wrapper(*args, **kwargs):
        ctx = args[1]
        channel = ctx.channel
        author = ctx.author
        manager = Manager()

        try:
            if isinstance(ctx.channel, discord.channel.TextChannel):
                channel_occupied = channel.overwrites_for(manager.get_role_by_name(channel.guild, 'alice tournament')).pair()[0]
                if channel_occupied.read_messages and channel_occupied.send_messages:
                    return await coro(*args, **kwargs)
                
                await ctx.message.delete()
                embed = manager.error_information('channel_occupied', author)
                embed.add_field(name='Guild', value=ctx.guild.name, inline=False)
                embed.add_field(name='Channel', value=f'#{channel.name}', inline=False)
                await author.send(embed=embed)
                return None
            
            return await coro(*args, **kwargs)
        except Exception as e:
            print(e)
            traceback.print_exc()

    return wrapper