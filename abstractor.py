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

# The regular expression to identify possible website links
# matches https://, then an optional www., then a site name, then anything until a word boundary or end of string
# the negative lookahead prevents the bot from responding to links that start with the prefix (! by default)
LINK_PATTERN = re.compile(
    "(?<!{})https?://(?:www\\.)?(?:{}).*(?:\\b|$)".format(
        re.escape(config.prefix), "|".join([re.escape(link) for link in parser.VALID_SITES])))


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

        # check for valid links
        possible_links = LINK_PATTERN.finditer(content)
        global_parser = GlobalParser()
        parsed_links = 0
        for link in possible_links:
            # make sure we don't parse more links than we'll send:
            if parsed_links >= config.max_links:
                break

            # if a link is found, parse it and send the summary
            if parser.is_valid_link(link.group(0)):
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

        # # Check for FFN links
        # ffn_links = FFN_MATCH.finditer(content)
        # for link in ffn_links:
        #     if num_processed >= max_links:
        #         break
        #     else:
        #         num_processed += 1
        #     # Standardize link format
        #     if "m.fanfiction.net" in link.group(0):
        #         mobile = True
        #     else:
        #         mobile = False
        #     if link.group(0).endswith("__cf_"):
        #         mobile = True
        #     link = link.group(0) \
        #         .replace("http://", "https://") \
        #         .replace("m.", "www.") \
        #         .replace("https://fanfiction.net", "https://www.fanfiction.net")
        #
        #     if link.endswith("__cf_"):
        #         link = link[:-6]
        #     # If a fic is linked multiple times, only send one message
        #     if link in links_processed:
        #         continue
        #     links_processed.add(link)
        #
        #     # Generate the summary and send it
        #     output = ""
        #     async with message.channel.typing():
        #         try:
        #             output = parser.generate_ffn_work_summary(link)
        #         # We can't resolve cloudflare errors
        #         # but if the link was a mobile link, send the normal one
        #         # should no longer happen with ficlab API
        #         except cloudscraper.exceptions.CloudflareException:
        #             if mobile:
        #                 output = link
        #         except Exception:
        #             logger.exception("Failed to get FFN summary")
        #     if len(output) > 0:
        #         if num_processed > 1:
        #             output = "** **\n" + output
        #         await message.channel.send(output)
        #
        # # spacebattles!
        # sb_links = SB_MATCH.finditer(content)
        # for link in sb_links:
        #     if num_processed >= max_links:
        #         break
        #     else:
        #         num_processed += 1
        #     # clean up link
        #     link = link.group(0).replace("http://", "https://")
        #
        #     # do not link a fic more than once per message
        #     if link in links_processed:
        #         continue
        #     links_processed.add(link)
        #
        #     # Attempt to get summary of SB work
        #     output = ""
        #     async with message.channel.typing():
        #         try:
        #             output = parser.generate_sb_summary(link)
        #         # if the process fails for an unhandled reason, print error
        #         except Exception:
        #             logger.exception("Failed to get SpaceBattles summary")
        #     if len(output) > 0:
        #         await message.channel.send(output)

        # if a bot message is replied to with "delete", delete the message
        if message.guild.id not in config.servers_no_deletion:
            if message.reference and message.reference.resolved:
                if message.reference.resolved.author == self.user:
                    if message.content == "delete":
                        await message.reference.resolved.delete()

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
