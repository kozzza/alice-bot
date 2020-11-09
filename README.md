# alice
[![forthebadge made-with-python](http://ForTheBadge.com/images/badges/made-with-python.svg)](https://www.python.org/)
[![TopGG](https://img.shields.io/badge/Invite-alice-2c2f33?logo=discord&logoColor=white&labelColor=7289d9&style=for-the-badge)](https://top.gg/bot/723813871881551932)

## Purpose
alice can host tournaments for your Discord server by utilizing the Challonge API. This bot brings the riveting tournament experience to a Discord channel for simplicity and convenience.

## Features
alice's tournament feature consists of a round-robin to seed players followed by a bracket to determine the winner. The round-robin is all done through the Discord channel while the bracket is played using the Challonge API. At the end of the tournament, players can visit the bracket hosted on Challonge to view their match history.

alice also provides capabilities to play round-robins and brackets, separate from a tournament. As of now the bracket is seeded randomly the same as a round-robin.

## Usage
alice has many commands to help manage matches in your server. To view all available commands, use !help when alice joins your server. The most up to date commands are displayed here:

<img src=https://github.com/kozzza/alice-bot/blob/master/static/project-examples/example-1.png width="700">

One of the commands "prefix" allows you to change the prefix alice uses to respond to commands. Once set, alice will only respond to this prefix so make sure not to forget it.

Another command that needs some explanation is the "open" command. When a tournament is ongoing in a channel, alice will remove all commands entered in that channel to keep the chat clean. However, if you decide not to complete the tournament alice will not be aware of this and will continue to block commands. In that case, admins can use !open to forcibly end the tournament.

Something to note is that all channels are disabled by default other than the one alice sends the hello message in. Use !enable if you'd like to use commands in other channels.