[Fanfiction Abstractor](https://github.com/sovdeeth/fanfiction-abstractor)
=======================

Fanfiction Abstractor is a discord bot which provides information about works on FFN and AO3 based on any links sent in the server.

Features
- Replies to any messages containing a link to a fanfiction.net story, or an archiveofourown.org work or series, with information about the work.
- Optionally allows users to delete bot messages by replying to them.
- Optionally allows users to get information about a particular work in a series by reacting to the bot's message with the work number.

This version of Fanfiction Abstractor is based on the wonderful work done by [quihi](https://github.com/quihi) on the original 
[Fanfiction Abstractor](https://github.com/quihi/fanfiction-abstractor) bot. Significant changes have been made to the codebase,
mainly centering around restructuring the parser code.

Running Fanfiction Abstractor
=============================

To add the bot to servers, you must set up an application through the [discord developer portal](https://discord.com/developers/applications).

To run the bot:
1. Clone or download the repository.
2. Fill out the `config.py` file.
3. If you do not have all the dependencies, run `pip3 install -r requirements.txt`.
4. Run `python3 bot.py`.

In discord, send `@Fanfiction Abstractor help` for more instructions on using the bot.
