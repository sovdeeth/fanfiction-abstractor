"""Abstractor is the discord client class.

This class contains the bot's handling of discord events.
"""

import logging
import re
import discord
import config
import messages
from parsing.common import GlobalParser

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
# matches https://, then an optional subdomain, then a site name, then any non-whitespace characters
# the negative lookahead prevents the bot from responding to links that start with the prefix (! by default)
LINK_PATTERN = re.compile(
    "(?<!{})https?://(?:\\S*\\.)?(?:{})\\S*".format(
        re.escape(config.prefix), "|".join([re.escape(link) for link in VALID_SITES])))

# dictionary of emoji to numbers, for parsing reacts
REACTS = {"1️⃣": 1, "2️⃣": 2, "3️⃣": 3, "4️⃣": 4, "5️⃣": 5,
          "6️⃣": 6, "7️⃣": 7, "8️⃣": 8, "9️⃣": 9, "🔟": 10}


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
        # todo: consider whether the logic should be moved to the parser
        from parsing.ao3 import AO3_MATCH, AO3SeriesWrapper
        if reaction.message.guild.id in config.servers_no_reacts:
            return
        if reaction.message.author != self.user or reaction.count != 1:
            return
        content = reaction.message.content
        match = AO3_MATCH.search(content)
        link_type = match.group(1)
        if link_type != "series":
            return

        fic = REACTS.get(reaction.emoji)
        if not fic:
            return

        series = AO3SeriesWrapper(match.group(2))
        output = ""
        async with reaction.message.channel.typing():
            try:
                work = series.get_work(fic)
                output = work.generate_summary()
            except Exception:
                logger.exception("Failed to generate summary for work in series")
        if len(output) > 0:
            await reaction.message.channel.send(output)
