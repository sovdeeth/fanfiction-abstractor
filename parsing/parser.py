from abc import abstractmethod

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
        # initialize parsers
        self.parsers = [
            AO3Parser(),
            FFNParser()
            # "sv": SVParser()
            # "sb": SBParser()
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


def format_html(field):
    """Format an HTML segment for discord markdown.

    field should be a note or summary from AO3.
    """
    brs = field.find_all("br")
    for br in brs:
        br.replace_with("\n")
    ols = field.find_all("ol")
    for ol in ols:
        ol.name = "p"
    uls = field.find_all("ul")
    for ul in uls:
        ul.name = "p"
    for li in field.find_all("li"):
        li.string = "- {}".format(li.text.strip())
        li.unwrap()
    field = field.blockquote.find_all("p")
    result = list(map(lambda x: x.text.strip(), field))
    result = "\n\n".join(result)
    result = result.strip()
    while "\n\n\n" in result:
        result = result.replace("\n\n\n", "\n\n")
    if result.count("\n\n") > 2:
        result = "\n\n".join(result.split("\n\n")[:3])
    if len(result) > 250:
        result = result[:250].strip()
        # i = result.rfind(" ")
        # result = result[:i]
        result += "…"
    return result


def atoi(text):
    """Convert a string to an int, or else return 0."""
    try:
        return int(text.replace(",", "").replace(".", "").replace(" ", ""))
    except ValueError:
        return 0
