import re
from functools import cached_property
import requests
import config
from parsing.parser import Parser

FFN_MATCH = re.compile(  # looks for a valid FFN link. Group 1 is the id of the work
    "(?<!{})https?://(?:www\\.|m\\.)?fanfiction.net/s/(\\d+).*"
    .format(re.escape(config.prefix)))


class FFNParser(Parser):
    """Parser for fanfiction.net links."""

    def is_valid_link(self, link) -> bool:
        match = FFN_MATCH.match(link)
        return match is not None
    def parse(self, link):
        """Parse an FFN link and return a representation of the fic."""
        # check if link a valid FFN link
        match = FFN_MATCH.match(link)
        if not match:
            raise ValueError("Invalid FFN link")

        unique_id = match.group(1)

        if unique_id in self._parsed_objects:
            return self._parsed_objects[unique_id]

        parsed = FFNWork(unique_id)

        if parsed:
            self._parsed_objects[unique_id] = parsed
        return parsed

    def generate_summaries(self, limit=3) -> list[str]:
        """Generate the summary of a work, series, or other object."""
        return [parsed.generate_summary() for parsed in list(self._parsed_objects.values())[:limit]]


class FFNWork:

    def __init__(self, fic_id, load = True):
        self.fic_id = fic_id
        self.url = "https://www.fanfiction.net/s/" + fic_id
        self.metadata = None
        if load:
            self.reload()

    def reload(self):
        """
        Loads information about this work. Based on ao3-api.
        """

        for attr in self.__class__.__dict__:
            if isinstance(getattr(self.__class__, attr), cached_property):
                if attr in self.__dict__:
                    delattr(self, attr)

        HEADERS = {"User-Agent": config.name}
        response = requests.get(f"https://fichub.net/api/v0/epub?q={self.url}", headers=HEADERS)
        if response.status_code != requests.codes.ok:
            raise ValueError("Invalid FFN link")
        self.metadata = response.json()["meta"]

    def generate_summary(self):
        output = "**{}** (<{}>) by **{}**\n".format(self.title, self.url, self.author)
        # output += "**Fandoms:** {}\n".format(fandoms)
        if self.genre:
            output += "**Rating:** {}          **Genre:** {}\n".format(self.rating, self.genre)
        else:
            output += "**Rating:** {}\n".format(self.rating)
        if self.characters:
            output += "**Characters:** {}\n".format(self.characters)
        if self.summary:
            output += "**Summary:** {}\n".format(self.summary)
        # output += "**Reviews:** {} **Favs:** {} **Follows:** {}\n".format(\
        #     reviews, favs, follows)
        if self.status == "complete":
            chapters = str(self.chapters) + "/" + str(self.chapters)
        else:
            chapters = str(self.chapters) + "/?"
        output += "**Words:** {} **Chapters:** {} **Favs:** {} **Updated:** {}".format(
            self.words, chapters, self.favs, self.updated)

        return output

    @cached_property
    def title(self):
        """
        Returns the title of the fic.
        """
        return self.metadata["title"]

    @cached_property
    def author(self):
        """
        Returns the author of the fic.
        """
        return self.metadata["author"]

    @cached_property
    def summary(self):
        """
        Returns the summary of the fic.
        """
        return self.metadata["description"].strip("<p>").strip("</p>")

    @cached_property
    def status(self):
        """
        Returns the status of the work.
        """
        return self.metadata["status"]

    @cached_property
    def chapters(self):
        """
        Returns the number of chapters in the work.
        """
        return self.metadata["chapters"]

    @cached_property
    def words(self):
        """
        Returns the number of words in the work.
        """
        return self.metadata["words"]

    @cached_property
    def updated(self):
        """
        Returns the date the work was last updated.
        """
        return self.metadata["updated"].split("T")[0]

    @cached_property
    def stats(self):
        """
        Returns the stats of the work.
        """
        return self.metadata["extraMeta"].split(" - ")

    @cached_property
    def genre(self):
        """
        Returns the genre of the work.
        """
        for field in self.stats:
            if "Genre: " in field:
                return field.replace("Genre: ", "")
        return None

    @cached_property
    def characters(self):
        """
        Returns the characters of the work.
        """
        for field in self.stats:
            if "Characters: " in field:
                return field.replace("Characters: ", "")
        return None

    @cached_property
    def reviews(self):
        """
        Returns the number of reviews of the work.
        """
        for field in self.stats:
            if "Reviews: " in field:
                return field.replace("Reviews: ", "")
        return 0

    @cached_property
    def favs(self):
        """
        Returns the number of favs of the work.
        """
        for field in self.stats:
            if "Favs: " in field:
                return field.replace("Favs: ", "")
        return 0

    @cached_property
    def follows(self):
        """
        Returns the number of follows of the work.
        """
        for field in self.stats:
            if "Follows: " in field:
                return field.replace("Follows: ", "")
        return 0

    @cached_property
    def rating(self):
        """
        Returns the rating of the work.
        """
        for field in self.stats:
            if "Rated: " in field:
                return field.replace("Rated: Fiction ", "")
        return None
