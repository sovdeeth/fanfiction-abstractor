from abc import abstractmethod
from functools import cached_property

import requests

import config

HEADER = {"User-Agent": config.name}

class Parser:
    """
    Abstract class for parsers.

    Parsers should be able to parse a link or id and return a representation of a work, series, or other object,
    or create summaries of those objects.
    """

    # dict of parsed objects, to avoid parsing the same thing twice
    # key is the link or a specific unique id, value is the parsed object
    _parsed_objects: dict[any, any]

    def __init__(self):
        self._parsed_objects = {}

    def clear(self):
        """Clear the parsed objects."""
        self._parsed_objects = {}

    @property
    def parsed_objects(self) -> list[any]:
        """Return the parsed objects."""
        return list(self._parsed_objects.values())

    @property
    def num_processed(self):
        """Return the number of unique links processed."""
        return len(self._parsed_objects)

    @abstractmethod
    def is_valid_link(self, link) -> bool:
        """
        Determines whether a link is valid for parsing with this parser
        """
        pass

    @abstractmethod
    def parse(self, link):
        """
        Parse a link or id and return a representation of a work, series, or other object.
        Links which have already been parsed will return the same object.
        """
        pass

    @abstractmethod
    def generate_summaries(self, limit=3) -> list[str]:
        """
        Generate the summaries of the parsed objects for sending as a discord message.
        limit is the maximum number of summaries to generate.
        """
        pass


class GlobalParser(Parser):
    parsers: {}

    # ffn_parser: FFNParser
    # sb_parser: SBParser
    # sv_parser: SVParser

    def __init__(self):
        super().__init__()
        # import here to avoid circular imports
        from parsing.ao3 import AO3Parser
        from parsing.ffn import FFNParser
        from parsing.sb import SBParser
        # initialize parsers
        self.parsers = [
            AO3Parser(),
            FFNParser(),
            SBParser()
            # "sv": SVParser()
        ]

    def _get_parser_by_link(self, link) -> any:
        """
        Given a link, uses the parsers is_valid_link method to find the correct parser.
        """
        for parser in self.parsers:
            if parser.is_valid_link(link):
                return parser

        return None


    def is_valid_link(self, link) -> bool:
        """
        Attempts to validate the given link against all known parsers
        """
        return True if self._get_parser_by_link(link) else False

    def parse(self, link) -> any:
        """
        Parse a link or id and return a representation of a work, series, or other object.
        The global parser will attempt to match the link to a parser, then hand it off to that parser.
        """

        parser = self._get_parser_by_link(link)

        # not a link we should parse
        if not parser:
            return None

        return parser.parse(link)

    def generate_summaries(self, limit=3) -> list[str]:
        """generates summaries from all the parsers"""
        # todo: consider keeping track of link order so we don't prioritize one site over another
        summaries = []
        for parser in self.parsers:
            for s in parser.generate_summaries(limit):
                summaries.append(s)
                limit -= 1
            if limit <= 0:
                break
        return summaries

    @property
    def parsed_objects(self) -> list[any]:
        """returns all the parsed objects from all the parsers"""
        parsed_objects = []
        for parser in self.parsers:
            for item in parser.parsed_objects:
                parsed_objects.append(item)
        return parsed_objects

    @property
    def num_processed(self):
        """gets the number of successfully parsed objects from all the parsers"""
        return len(self.parsed_objects)


class FicHubWork:
    """
    Represents a fic from FicHub, with properties to access the metadata.
    Parsers like FFN and SB inherit from this class, as they use FicHub to get their metadata.
    """

    def __init__(self, url, load = True):
        self.url = url
        self.metadata = None
        if load:
            self.reload()

    def reload(self):
        """
        Loads information about this work. Clears out cached properties.
        """
        for attr in self.__class__.__dict__:
            if isinstance(getattr(self.__class__, attr), cached_property):
                if attr in self.__dict__:
                    delattr(self, attr)

        response = requests.get(f"https://fichub.net/api/v0/epub?q={self.url}", headers=HEADER)
        if response.status_code != requests.codes.ok:
            raise ValueError("Invalid link")
        self.metadata = response.json()["meta"]

    def generate_summary(self):
        """
        Default summary generator for FicHub works.
        """
        output = "**{}** (<{}>) by **{}**\n".format(self.title, self.url, self.author)
        if self.summary:
            output += "**Summary:** {}\n".format(self.summary)
        if self.status == "complete":
            chapters = str(self.chapters) + "/" + str(self.chapters)
        else:
            chapters = str(self.chapters) + "/?"
        output += "**Words:** {} **Chapters:** {} **Updated:** {}".format(
            self.words, chapters, self.updated)

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
        return format_html(self.metadata["description"])

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

def format_html(string):
    """
    Format an HTML text segment for discord markdown.
    """
    return string.replace("<br>", "\n") \
            .replace("<em>", "*") \
            .replace("</em>", "*") \
            .replace("<strong>", "**") \
            .replace("</strong>", "**") \
            .replace("<p>", "") \
            .replace("</p>", " ")

def atoi(text):
    """Convert a string to an int, or else return 0."""
    try:
        return int(text.replace(",", "").replace(".", "").replace(" ", ""))
    except ValueError:
        return 0
