from discord.ext import commands
import discord

from manager import Manager
from manager import check_channel_perms, check_ongoing_tournament, detect_help
from challonge_bracket import ChallongeTournament

from datetime import datetime
import random
import asyncio


class Tournament(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.sql_query = self.bot.sql_query
        self.manager = Manager()

        self.tournament_reactions = ['\U0001F39F', '\U0001F3C1']
        self.match_reactions = ['\u2B05', '\u27A1']
        self.finalize_reaction = '\U0001F397'

        self.round_robin_color = 0xD55746
        self.bracket_color = 0x0064FF
        

    async def user_reaction_on_message(self, desired_reactions, desired_user_ids, desired_messages, timeout=120, delete_on_timeout=False, channel_to_open=None):
        def check(reaction, user):
            return user.id in desired_user_ids and str(reaction.emoji) in desired_reactions and reaction.message.id in [message.id for message in desired_messages]
        try:
            reaction, user = await self.bot.wait_for('reaction_add', check=check, timeout=timeout)
        except Exception as e:
            if delete_on_timeout:
                for message in desired_messages:
                    await message.delete()
            if channel_to_open:
                ongoing_tournament_role = self.manager.get_role_by_name(channel.guild, 'alice tournament')
                await channel_to_open.set_permissions(ongoing_tournament_role, read_messages=True, send_messages=True)
            return None
        else:
            return reaction
    
    async def get_cache(self, channel, messages):
        cache_messages = [await channel.fetch_message(message.id) for message in messages]
        return cache_messages
    
    def match_result_string(self, participants_dict, match, winner_index):
        match_result = [f'**{participants_dict[participant]}**' if participant == match[winner_index] else participants_dict[participant] for participant in match]
        return '  vs.  '.join(match_result)

    async def round_robin(self, channel, author, participants_dict, participant_ids, tournament_name):
        footer_text = f'Hosted by {author.display_name}  \u2022  '
        avatar_url = author.avatar_url

        rounds = self.generate_round_robin(participant_ids)
        wins_log = dict.fromkeys(participant_ids, 0)
        for i in range(len(rounds)):
            matches = rounds[i]
            bye_message = ''
            for match in matches:
                if 'BYE' in match:
                    bye_message = f'  \u2022  <@{[participant for participant in match if participant != "BYE"][0]}> has a bye'
                    matches.remove(match)
                    break

            round_complete = False
            bot_messages = []
            matches_block = []

            await channel.send(embed=self.manager.create_embed(f'Round {i+1}', f'Total matches: {len(matches)}{bye_message}', 
                self.round_robin_color, '', [], [], sign_embed=False))

            for j in range(len(matches)):
                player1 = matches[j][0]
                player2 = matches[j][1]
                embed = self.manager.create_embed('Match', f'<@{player1}>  vs.  <@{player2}>', self.round_robin_color, '', 
                    ['Wins'], [f'{participants_dict[player1]}: {wins_log[matches[j][0]]}\n{participants_dict[player2]}: {wins_log[matches[j][1]]}'],
                    footer=[footer_text+self.manager.current_time(), avatar_url], sign_embed=False)
                bot_message = await channel.send(embed=embed)
                
                bot_messages.append(bot_message)

                for emote in self.match_reactions:
                    await bot_message.add_reaction(emote)
            
            while not round_complete:
                await self.user_reaction_on_message(self.match_reactions, [int(participant_id) for participant_id in participant_ids], 
                    bot_messages, timeout=3600, channel_to_open=channel)
                cache_messages = await self.get_cache(channel, bot_messages)
                match_votes = []
                for message in cache_messages:
                    match_votes.append([reaction.count for reaction in message.reactions])
                
                round_complete = all(len(set(match)) > 1 for match in match_votes)
            
            for j in range(len(matches)):
                match = list(matches[j])
                winner_index = match_votes[j].index(max(match_votes[j]))

                wins_log[match[winner_index]] += 1

                matches_block.append(self.match_result_string(participants_dict, match, winner_index))
                await bot_messages[j].delete()

            leader = max(wins_log, key=wins_log.get)
            embed = self.manager.create_embed('Matches', f'<@{leader}> is in the lead with {wins_log[leader]}'
                f' {"wins" if wins_log[leader] > 1 else "win"}', self.round_robin_color, '', ['Results'], 
                ['\n'.join(matches_block)], footer=[footer_text+self.manager.current_time(), avatar_url])
            await channel.send(embed=embed)

        wins_log = {k: v for k, v in reversed(sorted(wins_log.items(), key=lambda item: item[1]))}
        rankings = ''
        place = 1
        for k, v in wins_log.items():
            rankings += (f'**{place}.** {participants_dict[k]}: {v}\n')
            place += 1

        formatted_date = datetime.now().strftime('%B %d, %Y | %I:%M %p')
        embed = self.manager.create_embed('Round Robin Standings', f'{tournament_name} \u2022 {formatted_date}', 
            self.round_robin_color, 'attachment://podium.png', ['Rankings'], [rankings], footer=[footer_text+self.manager.current_time(), avatar_url])
        await channel.send(embed=embed, file=discord.File('./static/images/podium.png', filename='podium.png'))

        return participants_dict, wins_log

    async def bracket(self, channel, author, participants_dict, ranked_participants, tournament_name, game_name, tournament_type):
        footer_text = f'Hosted by {author.display_name}  \u2022  '
        avatar_url = author.avatar_url

        bot_tournament_loading_message = await channel.send('*Generating bracket...*')
        participant_ids = list(ranked_participants.keys())
         # prefix participant id with 'id' to prevent integer conversion
        tournament = ChallongeTournament([participants_dict[participant] for participant in participant_ids],
            ['id'+participant_id for participant_id in participant_ids], tournament_name, game_name, tournament_type=tournament_type)
        tournament_url = tournament.create_tournament()
         # skip two characters to offset for the 'id' prefix
        tournament_participants = dict([(participant['id'], participant['misc'][2:]) for participant in tournament.fetch_participants()])
        print(tournament_participants)

        formatted_date = datetime.now().strftime('%B %d, %Y | %I:%M %p')
        embed = self.manager.create_embed(f'{tournament_type.title()} Bracket', f'{tournament_name} \u2022 {formatted_date}', self.bracket_color, 
            'attachment://challonge.png', [], [], footer=[footer_text+self.manager.current_time(), avatar_url], url=f'https://challonge.com/{tournament_url}')
        await bot_tournament_loading_message.delete()
        await channel.send(embed=embed, file=discord.File('./static/images/challonge.png', filename='challonge.png'))

        wins_log = dict.fromkeys(participant_ids, 0)
        round_count = 0
        while tournament.fetch_tournament()['state'] != 'awaiting_review':
            round_complete = False
            bot_messages = []
            matches_block = []
            matches = tournament.fetch_matches(match_state='open')
            round_players = [[match["player1_id"], match["player2_id"]] for match in matches]

            await channel.send(embed=self.manager.create_embed(f'Round {round_count+1}', f'Total matches: {len(matches)}', 
                self.bracket_color, '', [], [], sign_embed=False))

            for i in range(len(matches)):
                player1 = str(tournament_participants[round_players[i][0]])
                player2 = str(tournament_participants[round_players[i][1]])
                embed = self.manager.create_embed('Match', f'<@{player1}>  vs.  <@{player2}>', self.bracket_color, '', ['Wins'], 
                    [f'{participants_dict[player1]}: {wins_log[player1]}\n{participants_dict[player2]}: {wins_log[player2]}'], 
                    footer=[footer_text+self.manager.current_time(), avatar_url], sign_embed=False)
                bot_message = await channel.send(embed=embed)

                bot_messages.append(bot_message)
                for emote in self.match_reactions:
                    await bot_message.add_reaction(emote)

            while not round_complete:
                await self.user_reaction_on_message(self.match_reactions, [int(participant_id) for participant_id in participant_ids], 
                    bot_messages, timeout=3600, channel_to_open=channel)
                cache_messages = await self.get_cache(channel, bot_messages)
                match_votes = []
                for message in cache_messages:
                    match_votes.append([reaction.count for reaction in message.reactions])

                round_complete = all(len(set(match)) > 1 for match in match_votes)

            for i in range(len(matches)):
                winner_index = match_votes[i].index(max(match_votes[i]))
                
                wins_log[tournament_participants[round_players[i][winner_index]]] += 1
                matches_block.append(self.match_result_string(participants_dict, 
                    [tournament_participants[player] for player in round_players[i]], winner_index))
                await bot_messages[i].delete()

                score = [0, 0]
                score[winner_index] = 1 
                tournament.set_match_score(matches[i]['id'], round_players[i][winner_index], [score])
            
            leader = max(wins_log, key=wins_log.get)
            embed = self.manager.create_embed('Matches', f'<@{leader}> is on a streak with {wins_log[leader]}'
                f' {"wins" if wins_log[leader] > 1 else "win"}', self.bracket_color, '', ['Results'], 
                ['\n'.join(matches_block)], footer=[footer_text+self.manager.current_time(), avatar_url])
            await channel.send(embed=embed)
            round_count += 1
        
        tournament_winner = tournament_participants[round_players[i].pop(winner_index)]
        tournament_runnerup = tournament_participants[round_players[i][0]]
            
        embed = self.manager.create_embed('Finalize Results', 'React with :reminder_ribbon: to finalize the results of the tournament',
            self.bracket_color, '', [], [], sign_embed=False)
        bot_finalize_message = await channel.send(embed=embed)

        await bot_finalize_message.add_reaction(self.finalize_reaction)
        await self.user_reaction_on_message([self.finalize_reaction], [author.id], [bot_finalize_message], channel_to_open=channel)

        tournament.finalize()

        await bot_finalize_message.delete()
        formatted_date = datetime.now().strftime('%B %d, %Y | %I:%M %p')
        embed = self.manager.create_embed('Placings', f'{tournament_name} \u2022 {formatted_date}', 
            self.bracket_color, 'attachment://winner.png', ['Winner', 'Runner-Up'], [f'**<@{tournament_winner}>**', f'<@{tournament_runnerup}>'],
            footer=[footer_text+self.manager.current_time(), avatar_url], url=f'https://challonge.com/{tournament_url}/standings')
        await channel.send(embed=embed, file=discord.File('./static/images/winner.png', filename='winner.png'))

    @ commands.guild_only()
    @ commands.command(name='roundrobin', aliases=['rr'])
    @ check_channel_perms
    @ check_ongoing_tournament
    @ detect_help(expected_arg_count=1)
    async def prompt_round_robin(self, ctx):
        channel = ctx.channel
        author = ctx.author

        tournament_name = ctx.message.content[len(ctx.prefix+ctx.invoked_with):].strip()

        footer_text = f'Hosted by {author.display_name}  \u2022  '
        avatar_url = author.avatar_url
        embed = self.manager.create_embed(f'{tournament_name}', '- Enter the round-robin using :tickets:\n- Start the round-robin with :checkered_flag:',
            self.round_robin_color, 'attachment://robin.png', [], [], footer=[footer_text+self.manager.current_time(), avatar_url])
        bot_prompt_message = await channel.send(embed=embed, file=discord.File('./static/images/robin.png', filename='robin.png'))
        for emote in self.tournament_reactions:
            await bot_prompt_message.add_reaction(emote)
        if not await self.user_reaction_on_message(self.tournament_reactions[1:], [author.id], [bot_prompt_message], delete_on_timeout=True):
            return

        bot_prompt_message = await channel.fetch_message(bot_prompt_message.id)
        participants = [member if isinstance(member, discord.Member) else await channel.guild.fetch_member(member.id) 
                        async for member in bot_prompt_message.reactions[0].users(limit=65)][1:]
        participants.append(await channel.guild.fetch_member(750868970659119214)) # TEST
        participants.append(await channel.guild.fetch_member(723813871881551932)) # TEST
        participants.append(await channel.guild.fetch_member(218561502968283137)) # TEST
        if len(participants) < 2:
            bot_error_message = await channel.send(f'*Need more players to start the round-robin, restarting...*')
            await asyncio.sleep(3)
            await bot_prompt_message.delete()
            await bot_error_message.delete()
            return await self.prompt_round_robin(ctx)
        
        participants_dict = {str(member.id): member.display_name for member in participants}
        participant_ids = list(participants_dict.keys())
        random.shuffle(participant_ids)

        channel_occupied_role = self.manager.get_role_by_name(ctx.guild, 'alice tournament')
        channel_occupied = channel.overwrites_for(channel_occupied_role).pair()[0]
        # secondary check to verify another tournament hasn't started between command call and participant entry time
        if channel_occupied.read_messages and channel_occupied.send_messages:
            await channel.set_permissions(channel_occupied_role, read_messages=False, send_messages=False)

            await self.round_robin(channel, author, participants_dict, participant_ids, tournament_name)

            await channel.set_permissions(channel_occupied_role, read_messages=True, send_messages=True)
            
            self.sql_query.update_by_increment('guilds', ['round_robin_count'], ['guild_id'], [[str(ctx.guild.id)]])
        else:
            embed = self.manager.error_information('channel_occupied', author)
            embed.add_field(name='Guild', value=ctx.guild.name, inline=False)
            embed.add_field(name='Channel', value=f'#{channel.name}', inline=False)
            await author.send(embed=embed)

    @ commands.guild_only()
    @ commands.command(name='bracket')
    @ check_channel_perms
    @ check_ongoing_tournament
    @ detect_help(expected_arg_count=2, split_by=',')
    async def prompt_bracket(self, ctx):
        channel = ctx.channel
        author = ctx.author

        command_args = [arg.strip() for arg in ctx.message.content[len(ctx.prefix+ctx.invoked_with):].split(',')]
        tournament_name, game_name = command_args[0], command_args[1]
        try:
            tournament_type = 'single elimination' if (command_args[2] == 'se' or command_args[2] == 'single elimination') else 'double elimination'
        except:
            tournament_type = 'double elimination'

        footer_text = f'Hosted by {author.display_name}  \u2022  '
        avatar_url = author.avatar_url
        embed = self.manager.create_embed(f'{tournament_name}', '- Enter the bracket using :tickets:\n- Start the bracket with :checkered_flag:',
            self.bracket_color, 'attachment://trophy.png', [], [], footer=[footer_text+self.manager.current_time(), avatar_url])
        bot_prompt_message = await channel.send(embed=embed, file=discord.File('./static/images/bracket.png', filename='trophy.png'))
        for emote in self.tournament_reactions:
            await bot_prompt_message.add_reaction(emote)
        if not await self.user_reaction_on_message(self.tournament_reactions[1:], [author.id], [bot_prompt_message], delete_on_timeout=True):
            return

        bot_prompt_message = await channel.fetch_message(bot_prompt_message.id)
        participants = [member if isinstance(member, discord.Member) else await channel.guild.fetch_member(member.id) 
                        async for member in bot_prompt_message.reactions[0].users(limit=65)][1:]
        if len(participants) < 2:
            bot_error_message = await channel.send(f'*Need more players to start the bracket, restarting...*')
            await asyncio.sleep(3)
            await bot_prompt_message.delete()
            await bot_error_message.delete()
            return await self.prompt_bracket(ctx)
        
        participants_dict = {str(member.id): member.display_name for member in participants}
        participant_ids = list(participants_dict.keys())
        random.shuffle(participant_ids)
        ranked_participants = dict.fromkeys(participant_ids, 0)

        channel_occupied_role = self.manager.get_role_by_name(ctx.guild, 'alice tournament')
        channel_occupied = channel.overwrites_for(channel_occupied_role).pair()[0]
        # secondary check to verify another tournament hasn't started between command call and participant entry time
        if channel_occupied.read_messages and channel_occupied.send_messages:
            await channel.set_permissions(channel_occupied_role, read_messages=False, send_messages=False)

            await self.bracket(channel, author, participants_dict, ranked_participants, tournament_name, game_name, tournament_type)

            await channel.set_permissions(channel_occupied_role, read_messages=True, send_messages=True)
            
            self.sql_query.update_by_increment('guilds', ['bracket_count'], ['guild_id'], [[str(ctx.guild.id)]])
        else:
            embed = self.manager.error_information('channel_occupied', author)
            embed.add_field(name='Guild', value=ctx.guild.name, inline=False)
            embed.add_field(name='Channel', value=f'#{channel.name}', inline=False)
            await author.send(embed=embed)

    @ commands.guild_only()
    @ commands.command(name='tournament', aliases=['tourney'])
    @ check_channel_perms
    @ check_ongoing_tournament
    @ detect_help(expected_arg_count=2, split_by=',')
    async def prompt_tournament(self, ctx):
        channel = ctx.channel
        author = ctx.author

        command_args = [arg.strip() for arg in ctx.message.content[len(ctx.prefix+ctx.invoked_with):].split(',')]
        tournament_name, game_name = command_args[0], command_args[1]
        try:
            tournament_type = 'single elimination' if (command_args[2] == 'se' or command_args[2] == 'single elimination') else 'double elimination'
        except:
            tournament_type = 'double elimination'

        footer_text = f'Hosted by {author.display_name}  \u2022  '
        avatar_url = author.avatar_url
        embed = self.manager.create_embed(f'{tournament_name}', '- Enter the tournament using :tickets:\n- Start the tournament with :checkered_flag:',
            0x59B99E, 'attachment://trophy.png', [], [], footer=[footer_text+self.manager.current_time(), avatar_url])
        bot_prompt_message = await channel.send(embed=embed, file=discord.File('./static/images/trophy.png', filename='trophy.png'))
        for emote in self.tournament_reactions:
            await bot_prompt_message.add_reaction(emote)
        if not await self.user_reaction_on_message(self.tournament_reactions[1:], [author.id], [bot_prompt_message], delete_on_timeout=True):
            return

        bot_prompt_message = await channel.fetch_message(bot_prompt_message.id)
        participants = [member if isinstance(member, discord.Member) else await channel.guild.fetch_member(member.id) 
                        async for member in bot_prompt_message.reactions[0].users(limit=65)][1:]
        if len(participants) < 2:
            bot_error_message = await channel.send(f'*Need more players to start the tournament, restarting...*')
            await asyncio.sleep(3)
            await bot_prompt_message.delete()
            await bot_error_message.delete()
            return await self.prompt_tournament(ctx)
        
        participants_dict = {str(member.id): member.display_name for member in participants}
        participant_ids = list(participants_dict.keys())
        random.shuffle(participant_ids)

        channel_occupied_role = self.manager.get_role_by_name(ctx.guild, 'alice tournament')
        channel_occupied = channel.overwrites_for(channel_occupied_role).pair()[0]
        # secondary check to verify another tournament hasn't started between command call and participant entry time
        if channel_occupied.read_messages and channel_occupied.send_messages:
            await channel.set_permissions(channel_occupied_role, read_messages=False, send_messages=False)

            participants_dict, ranked_participants = await self.round_robin(channel, author, participants_dict, participant_ids, tournament_name)
            await self.bracket(channel, author, participants_dict, ranked_participants, tournament_name, game_name, tournament_type)

            await channel.set_permissions(channel_occupied_role, read_messages=True, send_messages=True)
            
            self.sql_query.update_by_increment('guilds', ['tournament_count'], ['guild_id'], [[str(ctx.guild.id)]])
        else:
            embed = self.manager.error_information('channel_occupied', author)
            embed.add_field(name='Guild', value=ctx.guild.name, inline=False)
            embed.add_field(name='Channel', value=f'#{channel.name}', inline=False)
            await author.send(embed=embed)

    def generate_round_robin(self, contenders):
        players = contenders.copy()
        if len(players) % 2:
            players.append('BYE')
        n = len(players)
        matches = []
        fixtures = []
        return_matches = []
        for fixture in range(1, n):
            for i in range(int(n/2)):
                matches.append((players[i], players[n - 1 - i]))
                return_matches.append((players[n - 1 - i], players[i]))
            players.insert(1, players.pop())
            fixtures.insert(int(len(fixtures)/2), matches)
            fixtures.append(return_matches)
            matches = []
            return_matches = []

        return(fixtures[:(len(players)-1)])


def setup(bot):
    bot.add_cog(Tournament(bot))