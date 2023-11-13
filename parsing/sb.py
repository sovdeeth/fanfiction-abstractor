import re
import config
from parsing.common import Parser, FicHubWork

SB_MATCH = re.compile(  # looks for a valid SB link. Group 1 is the id of the work
    "(?<!{})https?://forums.spacebattles.com/threads/([-.\\w]+)/?[^ ]*"
    .format(re.escape(config.prefix)))

class SBParser(Parser):
    """
    Parser for spacebattles.com links.
    """

    def is_valid_link(self, link) -> bool:
        """
        Determines whether a link is valid for parsing with this parser.
        """
        match = SB_MATCH.match(link)
        return match is not None

    def parse(self, link):
        """
        Parse an SB link and return a representation of the fic.
        """
        # check if link a valid SB link
        match = SB_MATCH.match(link)
        if not match:
            raise ValueError("Invalid SB link")

        unique_id = match.group(1)

        if unique_id in self._parsed_objects:
            return self._parsed_objects[unique_id]

        parsed = SBWork(unique_id)

        if parsed:
            self._parsed_objects[unique_id] = parsed
        return parsed


class SBWork(FicHubWork):
    """
    Represents a work on SB. FicHubWork does most of the work.
    """
    def __init__(self, fic_id, load=True):
        super().__init__("https://forums.spacebattles.com/threads/" + fic_id, load)
