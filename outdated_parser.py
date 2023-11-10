"""outdated_parser.py downloads, parses, and creates messages from FFN and AO3 pages."""

from bs4 import BeautifulSoup
import AO3
# import cloudscraper
import config
import json
import re
import requests


FFN_GENRES = set()
# create scraper to bypass cloudflare, always download desktop pages
# options = {"desktop": True, "browser": "firefox", "platform": "linux"}
# scraper = cloudscraper.create_scraper(browser=options)

# generate set of possible FFN genres
genres_list = ["Adventure", "Angst", "Crime", "Drama", "Family", "Fantasy",
               "Friendship", "General", "Horror", "Humor", "Hurt/Comfort",
               "Mystery", "Parody", "Poetry", "Romance", "Sci-Fi", "Spiritual",
               "Supernatural", "Suspense", "Tragedy", "Western"]
for g1 in genres_list:
    for g2 in genres_list:
        FFN_GENRES.add(g1 + "/" + g2)
    FFN_GENRES.add(g1)

# dictionary of emoji to numbers, for parsing reacts
REACTS = {"1️⃣": 1, "2️⃣": 2, "3️⃣": 3, "4️⃣": 4, "5️⃣": 5,
          "6️⃣": 6, "7️⃣": 7, "8️⃣": 8, "9️⃣": 9, "🔟": 10}






def generate_sb_summary(link):
    """Generate summary of SpaceBattles work.

    link should be a link to a spacebattles fic
    Returns the message with the fic info, or else a blank string
    """

    fichub_link = "https://fichub.net/api/v0/epub?q=" + link
    MY_HEADER = {"User-Agent": config.name}
    r = requests.get(fichub_link, headers=MY_HEADER)
    if r.status_code != requests.codes.ok:
        return None
    metadata = json.loads(r.text)["meta"]

    title = metadata["title"]
    author = metadata["author"]
    summary = metadata["description"].strip("<p>").strip("</p>")
    complete = metadata["status"]
    chapters = metadata["chapters"]
    words = metadata["words"]
    updated = metadata["updated"].replace("T", " ")

    output = "**{}** (<{}>) by **{}**\n".format(title, link, author)
    # if summary:
    #     output += "**Summary:** {}\n".format(summary)
    if complete == "complete":
        chapters = str(chapters) + "/" + str(chapters)
    else:
        chapters = str(chapters) + "/?"
    output += "**Words:** {} **Chapters:** {} **Updated:** {}".format(
        words, chapters, updated)

    return output
