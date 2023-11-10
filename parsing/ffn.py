import re

import config
from parsing.parser import Parser

FFN_MATCH = re.compile(  # looks for a valid AO3 link. Group 1 is the id of the work
    "(?<!{})https?://(?:www\\.|m\\.)?fanfiction.net/s/(\\d+).*"
    .format(re.escape(config.prefix)))


class FFNParser(Parser):
    """Parser for fanfiction.net links."""

    def parse(self, link):
        """Parse an AO3 link and return a representation of a work, series, or other object."""
        # check if link a valid AO3 link
        match = FFN_MATCH.match(link)
        if not match:
            raise ValueError("Invalid AO3 link")

        link_type = match.group(1)
        link_id = match.group(2)

        unique_id = link_type + ":" + link_id
        if unique_id in self._parsed_objects:
            return self._parsed_objects[unique_id]

        # check if link is to a series
        if link_type == "series":
            parsed = AO3SeriesWrapper(link_id)
        # check if link is to a work
        elif link_type == "works":
            parsed = AO3WorkWrapper(link_id)
        # check if link is to a chapter
        elif link_type == "chapters":
            chapter = AO3.Chapter(link_id, AO3Session)
            parsed = AO3WorkWrapper.from_work(chapter.work)
        else:
            raise ValueError("Invalid AO3 link")

        self._parsed_objects[unique_id] = parsed
        return parsed

    def generate_summaries(self, limit=3) -> list[str]:
        """Generate the summary of a work, series, or other object."""
        return [parsed.generate_summary() for parsed in list(self._parsed_objects.values())[:limit]]


def generate_ffn_work_summary(link):
    """Generate summary of FFN work.

    link should be a link to an FFN fic
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

    stats = metadata["extraMeta"].split(" - ")
    # next field varies.  have fun identifying it!
    # it's much easier using ficlab's data.
    # order: rating, language, genre, characters, ~chapters, words,~~
    #     reviews, favs, follows, ~~updated, published, status, id~~
    genre = None
    characters = None
    reviews = 0
    favs = 0
    follows = 0

    for field in stats:
        if "Rated: " in field:
            rating = field.replace("Rated: Fiction ", "")
        if "Genre: " in field:
            genre = field.replace("Genre: ", "")
        if "Characters: " in field:
            characters = field.replace("Characters: ", "")
        if "Reviews: " in field:
            reviews = field.replace("Reviews: ", "")
        if "Favs: " in field:
            favs = field.replace("Favs: ", "")
        if "Follows: " in field:
            follows = field.replace("Follows: ", "")

    output = "**{}** (<{}>) by **{}**\n".format(title, link, author)
    # output += "**Fandoms:** {}\n".format(fandoms)
    if genre:
        output += "**Rating:** {}          **Genre:** {}\n".format(rating, genre)
    else:
        output += "**Rating:** {}\n".format(rating)
    if characters:
        output += "**Characters:** {}\n".format(characters)
    if summary:
        output += "**Summary:** {}\n".format(summary)
    # output += "**Reviews:** {} **Favs:** {} **Follows:** {}\n".format(\
    #     reviews, favs, follows)
    if complete == "complete":
        chapters = str(chapters) + "/" + str(chapters)
    else:
        chapters = str(chapters) + "/?"
    output += "**Words:** {} **Chapters:** {} **Favs:** {} **Updated:** {}".format(
        words, chapters, favs, updated)

    return output
