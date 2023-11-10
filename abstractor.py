"""Abstractor is the discord client class.

This class contains the bot's handling of discord events.
"""

import logging
import re
import discord
import config
import messages
from parsing import parser
from parsing.parser import GlobalParser

# Import the logger from another file
logger = logging.getLogger('discord')

# Sites that the bot should attempt to parse links from
# The parser is ultimately responsible for determining if a link is valid,
# but this is used as a first pass to avoid unnecessary parsing.
# Exclude any prefixes (http://, https://, www.) and any subdomains (m., forums.) from this list.
VALID_SITES = [
    "archiveofourown.org",
    "fanfiction.net",
    "spacebattles.com"
]

# The regular expression to identify possible website links
# matches https://, then an optional www., then a site name, then anything until a word boundary or end of string
# the negative lookahead prevents the bot from responding to links that start with the prefix (! by default)
LINK_PATTERN = re.compile(
    "(?<!{})https?://(?:.*\\.)?(?:{}).*(?:\\b|$)".format(
        re.escape(config.prefix), "|".join([re.escape(link) for link in VALID_SITES])))


class Abstractor(discord.Client):
    """The discord bot client itself."""

    async def on_ready(self):
        """When starting bot, print the servers it is part of."""
        s = "Logged on!\nMember of:\n"
        for guild in self.guilds:
            owner = await self.fetch_user(guild.owner_id)
            s += "{}\t{}\t{}\t{}\n".format(
                guild.id, guild.name, owner, guild.owner_id)
        logger.info(s)

    async def on_guild_join(self, guild):
        """Print a message when the bot is added to a server."""
        logger.info("Joined a new guild!\n")
        owner = await self.fetch_user(guild.owner_id)
        s = "\t".join((guild.id, guild.name, owner, guild.owner_id))
        logger.info(s)

    async def on_guild_remove(self, guild):
        """Print a message when the bot is removed a server."""
        logger.info("Removed from a guild.")
        owner = await self.fetch_user(guild.owner_id)
        s = "\t".join((guild.id, guild.name, owner, guild.owner_id))
        logger.info(s)

    async def on_message(self, message):
        """Parse messages and respond if they contain a fanfiction link."""
        # ignore own messages
        if message.author == self.user:
            return
        # ignore bots unless specifically permitted
        if message.author.bot and message.author.id not in config.bots_allow:
            return

        # post a greeting if tagged
        content = message.content.lower()
        if "<@!1170971760028557352>" in content or "<@1170971760028557352>" \
                in content or "<@&1170971760028557352>" in content:
            if "help" in content or "info" in content:
                output = messages.introduction(message.guild.id)
                await message.channel.send(output)

        # if a bot message is replied to with "delete", delete the message and exit early
        if message.guild.id not in config.servers_no_deletion:
            if message.reference and message.reference.resolved:
                if message.reference.resolved.author == self.user:
                    if message.content == "delete":
                        await message.reference.resolved.delete()
                        return

        # check for valid links
        logger.info("Checking message for links: {}".format(content))
        possible_links = LINK_PATTERN.finditer(content)
        global_parser = GlobalParser()
        parsed_links = 0
        for link in possible_links:
            # make sure we don't parse more links than we'll send:
            if parsed_links >= config.max_links:
                break

            # if a link is found, parse it and send the summary
            if global_parser.is_valid_link(link.group(0)):
                async with message.channel.typing():
                    try:
                        parsed_item = global_parser.parse(link.group(0))
                        if parsed_item:
                            parsed_links += 1
                    except Exception:
                        logger.exception("Failed to parse link: {}".format(link.group(0)))

        number_sent = 0
        if parsed_links > 0:
            for summary in global_parser.generate_summaries(config.max_links):
                if number_sent > 1:
                    summary = "** **\n" + summary
                number_sent += 1
                await message.channel.send(summary)


    async def on_reaction_add(self, reaction, user):
        """If react is added to bot's series message, send work information.

        This can be disabled per server in config.py.
        """
        if reaction.message.guild.id in config.servers_no_reacts:
            return
        if reaction.message.author != self.user or reaction.count != 1:
            return
        content = reaction.message.content
        if "https://archiveofourown.org/series/" not in content.split("\n")[0]:
            return
        fic = parsing.REACTS.get(reaction.emoji)
        if not fic:
            return
        series = AO3_MATCH.search(content).group(0)
        # regex match may include an extra character at the start
        if not series.startswith("https://"):
            series = series[1:]
        link = "https://archiveofourown.org" \
               + parsing.identify_work_in_ao3_series(series, fic)
        if link:
            output = ""
            async with reaction.message.channel.typing():
                try:
                    output = parsing.generate_ao3_work_summary(link)
                except Exception:
                    logger.exception("Failed to generate summary for work in series")
            if len(output) > 0:
                await reaction.message.channel.send(output)
