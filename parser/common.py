from abc import abstractmethod

HEADERS = {"User-Agent": "fanfiction-abstractor-bot"}


class Parser:
    """
    Abstract class for parsers.

    Parsers should be able to parse a link or id and return a representation of a work, series, or other object,
    or create summaries of those objects.
    """

    # dict of parsed objects, to avoid parsing the same thing twice
    # key is the link or a specific unique id, value is the parsed object
    _parsed_objects: dict[any, any] = {}

    def clear(self):
        """Clear the parsed objects."""
        self._parsed_objects = {}

    @property
    def parsed_objects(self):
        """Return the parsed objects."""
        return self._parsed_objects.values()

    @property
    def num_processed(self):
        """Return the number of unique links processed."""
        return len(self._parsed_objects)

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
