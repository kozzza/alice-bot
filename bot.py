from decouple import config
from challonge_bracket import ChallongeTourney
from datetime import datetime
import discord
import asyncio
import random
import inspect

token = config('DISCORD_BOT_TOKEN')

client = discord.Client()
print(discord.__version__)

class DiscordTournament():
    
    def __init__(self, message, members=[]):
        self.host = message.author
        self.channel = message.channel
        self.members = members

        arguments = {}
        message_arguments = ' '.join(message.content.split(' ')[1:]).split(',')
        for arg in message_arguments:
            arg = arg.strip().split('=')
            arguments[arg[0]] = arg[1]

        self.game = arguments['game']

    async def user_reaction_on_message(self, desired_reactions, desired_users):
        def check(reaction, user):
            return user in desired_users and str(reaction.emoji) in desired_reactions
        try:    
            reaction, user = await client.wait_for('reaction_add', check=check)
        except asyncio.TimeoutError:
            return self.channel.send('*Tournament closed.*')
        else:
            return

    async def get_cache(self, messages):
        cache_messages = [await self.channel.fetch_message(message.id) for message in messages]
        return cache_messages

    async def prompt_tournament(self):
        embed = discord.Embed(title='Tournament', description='\
        - Enter the tournament using \t:tickets:\n\
            - Start the tournament with \t:checkered_flag:', color=discord.Colour.teal())
        file = discord.File('./files/trophy.png', filename='trophy.png')
        embed.set_thumbnail(url="attachment://trophy.png")

        bot_tournament_start_message = await self.channel.send(file=file, embed=embed)

        reactions = ['\U0001F39F', '\U0001F3C1']
        for emote in reactions:
            await bot_tournament_start_message.add_reaction(emote)
        await self.user_reaction_on_message(reactions[1:], [self.host])

        cache_messages = await self.channel.fetch_message(bot_tournament_start_message.id)
        self.members = [member async for member in cache_messages.reactions[0].users()][1:]

        if len(self.members) < 2:
            bot_insufficient_players_message = await self.channel.send(f'*Need more players to start the tournament, restarting...*')
            await asyncio.sleep(3)
            await bot_tournament_start_message.delete()
            await bot_insufficient_players_message.delete()
            await self.prompt_tournament()
        else:
            await self.start_round_robin()

    async def start_round_robin(self):
        member_dict = dict([(str(member.id), member.name) for member in self.members])
        member_ids = list(member_dict.keys())
        random.shuffle(member_ids)
        rounds = self.generate_round_robin(member_ids)

        wins_dict = dict.fromkeys(member_ids, 0)
        reactions = ['\u2B05', '\u27A1']
        
        for i in range(len(rounds)):
            matches = rounds[i]
            round_complete = False
            bot_messages = []
            matches_block = []

            await self.channel.send(f'__**ROUND {i+1}:**__')
                
            for j in range(len(matches)):
                bot_message = await self.channel.send(' vs. '.join([member_dict[member_id] for member_id in matches[j]]))
                bot_messages.append(bot_message)
                for emote in reactions:
                    await bot_message.add_reaction(emote)
            
            while not round_complete:
                await self.user_reaction_on_message(reactions, self.members)
                cache_messages = await self.get_cache(bot_messages)
                match_reactions = []
                for message in cache_messages:
                    match_reactions.append([reaction.count for reaction in message.reactions])
                round_complete = all(len(set(match)) > 1 for match in match_reactions)
            
            for k in range(len(matches)):
                match = list(matches[k])
                winner = match.pop(match_reactions[k].index(max(match_reactions[k])))
                wins_dict[winner] += 1
                matches_block.append(f'**{member_dict[winner]}** vs. {member_dict[match[0]]}')
                await bot_messages[k].delete()

            await self.channel.send('\n'.join(matches_block))

        wins_dict = {k: v for k, v in reversed(sorted(wins_dict.items(), key=lambda item: item[1]))}

        await self.start_finals(wins_dict)
    
    async def start_finals(self, ranked_participants):
        member_dict = dict([(str(member.id), member.name) for member in self.members])
        reactions = ['\u2B05', '\u27A1']

        bot_tournament_loading_message = await self.channel.send('*Generating bracket...*')

        tournament_name = f'{self.game} Tournament: {datetime.now().strftime("%B %d, %Y | %I:%M %p")}'
        tournament = ChallongeTourney([member_dict[participant] for participant in list(ranked_participants.keys())], tournament_name, self.game)
        tournament_url = tournament.create_tournament()
        tournament_participants = dict([(participant['id'], participant['name']) for participant in tournament.fetch_participants()])

        await bot_tournament_loading_message.delete()

        rankings_list = []
        place = 0
        for k, v in ranked_participants.items():
            rankings_list.append(f'**{place+1}.** {member_dict[k]}: {v}')
            place += 1
        embed = discord.Embed(title='Finals', description=f'{tournament_name}\n',
        color=discord.Colour.red())
        embed.add_field(name='Rankings:\n', value='\n'.join(rankings_list))
        embed.url = f'https://challonge.com/{tournament_url}'
        file = discord.File('./files/challonge_logo.png', filename='challonge_logo.png')
        embed.set_thumbnail(url="attachment://challonge_logo.png")

        await self.channel.send(file=file, embed=embed)

        round_count = 0
        while tournament.fetch_tournament()['state'] != 'awaiting_review':

            round_complete = False
            bot_messages = []
            matches_block = []
            matches = tournament.fetch_matches(match_state='open')
            matches_players = [[match["player1_id"], match["player2_id"]] for match in matches]

            await self.channel.send(f'__**ROUND {round_count+1}:**__')

            for i in range(len(matches)):
                bot_message = await self.channel.send(' vs. '.join(
                    [tournament_participants[player] for player in matches_players[i]]))
                bot_messages.append(bot_message)
                for emote in reactions:
                    await bot_message.add_reaction(emote)

            while not round_complete:
                await self.user_reaction_on_message(reactions, self.members)
                cache_messages = await self.get_cache(bot_messages)
                match_reactions = []
                for message in cache_messages:
                    match_reactions.append([reaction.count for reaction in message.reactions])
                round_complete = all(len(set(match)) > 1 for match in match_reactions)

            for k in range(len(matches)):
                match = list(matches[k])
                winner_index = match_reactions[k].index(max(match_reactions[k]))
                winner_id = matches_players[k].pop(winner_index)
                matches_block.append(f'**{tournament_participants[winner_id]}** vs. {tournament_participants[matches_players[k][0]]}')

                score = [0, 0]
                score[winner_index] = 1 
                tournament.set_match_score(matches[k]['id'], winner_id, [score])
            
            for k in range(len(matches)):
                await bot_messages[k].delete()
            
            await self.channel.send('\n'.join(matches_block))
            round_count += 1

            if tournament.fetch_tournament()['state'] == 'awaiting_review':
                tournament_winner = tournament_participants[winner_id]
            
        bot_tournament_finalize_message = await self.channel.send(
            'React with :reminder_ribbon: to finalize the results')

        reactions = ['\U0001F397']
        await bot_tournament_finalize_message.add_reaction(reactions[0])
        await self.user_reaction_on_message(reactions, [self.host])

        tournament.finalize()

        await bot_tournament_finalize_message.delete()
        await self.channel.send(f'Your winner is: **{tournament_winner}**!')

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

        return([[match for match in fixture if 'BYE' not in match] for fixture in fixtures[:(len(players)-1)]])

@ client.event
async def on_ready():
    print(f'We have logged in as {client.user}')
    await client.change_presence(activity=discord.Game(name="!help"))

async def ping(message):
    await message.channel.send(f'Pong :ping_pong:  |  {client.latency} ms')

async def get_help(message):
    await message.channel.send('\n'.join(
    ['**!help:** provides a list and description of all commands',
    '**!ping:** returns the latency of the bot',
    '**!tourney game=\{game_name\}:** starts a tournament for the specified game']))

@ client.event
async def on_message(message):
        print(f'{message.channel}: {message.author}: {message.author.name}: {message.content}')
        if message.content:
            if message.content[0] == '!' and not message.author.bot:
                message_elements=message.content.split(' ')
                message_elements=[i for i in message_elements if i]
                command=message_elements[0][1:]
                command_switcher={
                    "tourney": DiscordTournament,
                    "tournament": DiscordTournament,
                    "ping": ping,
                    "help": get_help
                }
                try:
                    command_destination = command_switcher[command.lower()]
                    if inspect.isclass(command_destination):
                        try:
                            command_object = command_destination(message)
                            await command_object.prompt_tournament()
                        except IndexError as e:
                            await message.channel.send('Game not specified, please try again.')
                    else:
                        await command_destination(message)

                except KeyError:
                    None

client.run(token)