import re
import AO3
import config
from parsing.common import Parser

AO3Session = AO3.Session(config.AO3_USERNAME, config.AO3_PASSWORD)

AO3_MATCH = re.compile(  # looks for a valid AO3 link. Group 1 is the type of link, group 2 is the ID.
    "(?<!{})https?://(?:www\\.)?archiveofourown.org(?:/collections/\\w+)?/(works|series|chapters)/(\\d+)"
    .format(re.escape(config.prefix)))


class AO3Parser(Parser):
    """Parser for AO3 links."""

    def is_valid_link(self, link) -> bool:
        match = AO3_MATCH.match(link)
        return match is not None

    def parse(self, link):
        """Parse an AO3 link and return a representation of a work, series, or other object."""
        # check if link a valid AO3 link
        match = AO3_MATCH.match(link)
        if not match:
            return None

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
            chapter = AO3.Chapter(link_id, None, AO3Session)
            parsed = AO3WorkWrapper.from_work(chapter.work)
        else:
            raise ValueError("Invalid AO3 link")

        if parsed:
            self._parsed_objects[unique_id] = parsed
        return parsed

    def generate_summaries(self, limit=3) -> list[str]:
        """Generate the summary of a work, series, or other object."""
        return [parsed.generate_summary() for parsed in list(self._parsed_objects.values())[:limit]]


class AO3WorkWrapper:
    work: AO3.Work

    @classmethod
    def from_work(cls, work: AO3.Work):
        """Create an AO3WorkParser from an existing AO3.Work."""
        parser = cls.__new__(cls)
        parser.work = work
        return parser

    def __init__(self, work_id):
        self.work = AO3.Work(work_id, AO3Session)

    def _get_characters_from_relationships(self) -> set[str]:
        """Get the characters from the relationships."""
        already_listed = set()
        for relationship in self.work.relationships[:3]:
            relationship = relationship.replace(" & ", "/")
            relationship = relationship.split("/")
            for character in relationship:
                if " (" in character:
                    character = character.split(" (")[0]
                already_listed.add(character)
        return already_listed

    def generate_summary(self) -> str:
        """Generate a summary of the work."""
        output = ":lock:" if self.work.restricted else ""
        # Title, link, authors
        output += "**{}** (<https://archiveofourown.org/works/{}>) by **{}**\n" \
            .format(self.work.title, self.work.id, ", ".join(map(lambda x: x.username, self.work.authors)))
        # Series
        if series := self._series_with_positions():
            series = series[:2]
            for s, index in series:
                output += "**Part {}** of the **{}** series (<https://archiveofourown.org/series/{}>)\n" \
                    .format(index, s.name, s.id)

        # Fandoms
        if self.work.fandoms:
            fandoms = self.work.fandoms
            if len(fandoms) > 5:
                fandoms = ", ".join(fandoms[:5]) + ", …"
            else:
                fandoms = ", ".join(fandoms)
            output += "**Fandoms:** {}\n".format(fandoms)

        # Rating, Warnings, Category
        rating = self.work.rating
        if self.work.categories:
            category = ", ".join(self.work.categories)
            output += "**Rating:** {}          **Category:** {}\n".format(rating, category)
        else:
            output += "**Rating:** {}\n".format(rating)

        warnings = ", ".join(self.work.warnings)
        output += "**Warnings:** {}\n".format(warnings)

        # Relationships, Characters
        if self.work.relationships:
            relationships = self.work.relationships.copy()
            if len(relationships) > 3:
                relationships = ", ".join(relationships[:3]) + ", …"
            else:
                relationships = ", ".join(relationships)
            output += "**Relationships:** {}\n".format(relationships)

        if self.work.characters:
            # clear out characters that are already listed in relationships
            characters = self.work.characters.copy()
            already_listed = self._get_characters_from_relationships()
            for character in self.work.characters:
                stripped_character = character
                if " (" in stripped_character:
                    stripped_character = stripped_character.split(" (")[0]
                if " - " in stripped_character:
                    stripped_character = stripped_character.split(" - ")[0]
                if stripped_character in already_listed:
                    characters.remove(character)

            if len(characters) > 3:
                characters = ", ".join(characters[:3]) + ", …"
            else:
                characters = ", ".join(characters)

            if len(characters) > 0:
                if self.work.relationships:
                    output += "**Additional Characters:** {}\n".format(characters)
                else:
                    output += "**Characters:** {}\n".format(characters)

        # Freeform Tags
        if self.work.tags:
            if len(self.work.tags) > 5:
                freeform = ", ".join(self.work.tags[:5]) + ", …"
            else:
                freeform = ", ".join(self.work.tags)
            output += "**Tags:** {}\n".format(freeform)

        # Summary
        if self.work.summary:
            output += "**Summary:** {}\n".format(self._get_formatted_summary())

        # Stats
        expected_chapters = self.work.expected_chapters if self.work.expected_chapters else "?"
        output += "**Words:** {} **Chapters:** {}/{} **Kudos:** {} **Updated:** {}\n" \
            .format(self.work.words, self.work.nchapters, expected_chapters,
                    self.work.kudos, self.work.date_updated.strftime("%Y-%m-%d"))

        return output

    def _get_formatted_summary(self):
        """Get the formatted summary of the series."""
        summary = self.work.soup.find("div", {"class": "summary"})
        if summary is None:
            return ""
        return format_ao3_html(summary)

    def _series_with_positions(self) -> list[tuple[AO3.Series, int]]:
        """Get the position of the work in the series."""

        # todo: this should be cached but nooooooooooooo the attribute didn't exist
        # i hate python

        dd = self.work.soup.find("dd", {"class": "series"})
        if dd is None:
            return []

        s = []
        for span in dd.find_all("span", {"class": "position"}):
            series = AO3.Series(span.a["href"].split("/")[-1], AO3Session)
            index = re.match(r"Part (\d+)", span.text.strip()).group(1)
            s.append((series, int(index)))

        self._series_with_positions_cache = s
        return s


class AO3SeriesWrapper:
    series: AO3.Series

    @classmethod
    def from_series(cls, series: AO3.Series):
        """Create an AO3SeriesParser from an existing AO3.Series."""
        parser = cls.__new__(cls)
        parser.series = series
        return parser

    def __init__(self, series_id, parse=True):
        if parse:
            self.parse(series_id)

    def parse(self, series_id):
        self.series = AO3.Series(series_id, AO3Session)

    def generate_summary(self) -> str:
        """Generate a summary of the series."""
        output = ":lock:" if self.series.soup.find("img", {"title": "Restricted"}) is not None else ""
        # Title, link, authors
        output += "**{}** (<{}>) by **{}**\n" \
            .format(self.series.name, self.series.url, ", ".join(map(lambda x: x.username, self.series.creators)))

        if self.series.description:
            output += "**Description:** {}\n".format(self.series.description)

        # date created, date updated
        output += "**Begun:** {} **Updated:** {}\n".format(self.series.series_begun, self.series.series_updated)

        # stats
        output += "**Words:** {} **Works:** {} **Complete:** {}\n\n".format(
            self.series.words, self.series.nworks, "Yes" if self.series.complete else "No")

        # Find titles and links to first few works
        for i in range(min(3, len(self.series.work_list))):
            work = self.series.work_list[i]
            output += "{}. __{}__: <{}>\n".format(
                i + 1, work.title, work.url)
        # add the fourth work if there are four works, or else ellipsis
        if len(self.series.work_list) == 4:
            work = self.series.work_list[3]
            output += "4. __{}__: <{}>".format(
                work.title, work.url)
        elif len(self.series.work_list) > 4:
            output += "        [and {} more works]".format(self.series.nworks - 3)

        return output

    def get_work(self, number):
        """Get the work at the given number in the series."""
        work = self.series.work_list[number - 1]
        work.reload()
        return AO3WorkWrapper.from_work(work)


def format_ao3_html(field):
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
