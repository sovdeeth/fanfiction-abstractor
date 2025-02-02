#!/usr/bin/env python3

"""This is a duplicate of the Fanfic Rec Bot, but it works better.

Required files are: bot.py, config.py, abstractor.py, messages.py, and the parsing package.
To run the bot, execute bot.py and leave it running.

config.py must contain the bot token as a variable, token.
To make Abstractor respond to existing bots, put their user IDs in config.py in bots_allow.
To disable deleting bot messages by replying with "delete",
    put the server ID in config.py in servers_no_deletion.
To disable getting info about fics by replying to series messages,
    put the server ID in config.py in servers_no_reacts.
These must be blank lists or sets, otherwise.

quihi, sovdeeth
"""

import abstractor
import config
import discord
import logging


def main():
    """Run the discord bot."""
    # set up logging
    logger = logging.getLogger('discord')
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler(
        filename='discord.log', encoding='utf-8', mode='a')
    handler.setFormatter(logging.Formatter(
        '%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
    logger.addHandler(handler)

    # create discord client
    intents = discord.Intents(messages=True, reactions=True, guilds=True, message_content=True)
    activity = discord.Activity(
        name='@me help',
        type=discord.ActivityType.playing)
    description = "Posts information about fanfiction.  Contact {} for details.\
    \nhttps://github.com/sovdeeth/fanfiction-abstractor"\
        .format(config.name)
    client = abstractor.Abstractor(
        intents=intents, activity=activity, description=description)

    # run the bot
    print("Completed setup!")
    client.run(config.token)


if __name__ == '__main__':
    main()

"""
TODO:
- add way more configuration
  - limit summary length, how many blurbs are posted, etc.
- use sqlite or at least pickling for configuration
- handle external bookmarks
- flip to make weird stuff opt-in
- switch to aiohttp library
- something with what chapter is linked?
- add bookmark count for series?
- add more info on series (fandoms, tags, etc. off author page)
  - test Lomonaaeren for that
- change printing priority to be based on order of the links in the original message instead of by site?
- refactor reaction stuff to be not rely on the ao3 package?
- change summary message to use embeds instead of plain markdown?
- turn title into a link instead of keeping them separate?
- link author pages too
- add summaries for author links
- do something with notes?
"""
