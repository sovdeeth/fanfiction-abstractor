import re
from functools import cached_property
import config
from parsing.common import Parser, FicHubWork

FFN_MATCH = re.compile(  # looks for a valid FFN link. Group 1 is the id of the work
    "(?<!{})https?://(?:www\\.|m\\.)?fanfiction.net/s/(\\d+)[^ ]*"
    .format(re.escape(config.prefix)))


class FFNParser(Parser):
    """
    Parser for fanfiction.net links.
    """

    def is_valid_link(self, link) -> bool:
        """
        Determines whether a link is valid for parsing with this parser.
        """
        match = FFN_MATCH.match(link)
        return match is not None

    def parse(self, link):
        """
        Parse an FFN link and return a representation of the fic.
        """
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


class FFNWork(FicHubWork):

    def __init__(self, fic_id, load=True):
        super().__init__(fic_id, load)
        self.fic_id = fic_id
        self.url = "https://www.fanfiction.net/s/" + fic_id
        self.metadata = None
        if load:
            self.reload()

    def generate_summary(self):
        """
        Generate the summary of a work, series, or other object.
        """
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
