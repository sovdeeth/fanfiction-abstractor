from datetime import date
from enum import Enum

from parser.common import format_html, HEADERS, atoi
from bs4 import BeautifulSoup
import AO3
import config
import re
import requests


class AO3Response:
    """Represents a response from an AO3 request."""
    link: str
    soup: BeautifulSoup | None
    locked_fic: bool
    status_code: int

    def __init__(self, link, soup, locked_fic, status_code):
        self.link = link
        self.soup = soup
        self.locked_fic = locked_fic
        self.status_code = status_code


def make_ao3_request(link, headers=HEADERS) -> AO3Response:
    """Make a request to AO3.

    link should be a link to an AO3 work, chapter, or series
    Returns an AO3Response object.

    If the request fails, returns an AO3Response object with soup=None.
    """

    response = requests.get(link, headers)

    if response.status_code != requests.codes.ok:
        return AO3Response(link, None, False, response.status_code)

    soup = BeautifulSoup(response.text, "lxml")

    locked_fic = False
    if response.url == "https://archiveofourown.org/users/login?restricted=true":
        ao3_session = AO3.Session(config.AO3_USERNAME, config.AO3_PASSWORD)
        soup = ao3_session.request(link)
        locked_fic = True

    return AO3Response(link, soup, locked_fic, response.status_code)


class State(Enum):
    """Represents the internal state of an AO3Work."""
    REQUEST_FAILED = -1
    UNINITIALIZED = 0
    INITIALIZED = 1
    PARSED = 2


class AO3Work:
    """Represents an AO3 work."""

    # todo: consider scrapping this class in favor of the AO3-api library because this is reinventing the wheel

    _soup: BeautifulSoup = None

    state: State = None

    work_id: int = None
    locked: bool = None

    # preface
    title: str = None
    authors: list[str] = None
    summary: str = None

    # meta
    ratings: list[str] = None
    warnings: list[str] = None
    category: list[str] = None

    fandoms: list[str] = None

    relationships: list[str] = None
    characters: list[str] = None
    freeform: list[str] = None

    language: str = None

    series: list[(str, str, any)] = None
    collections: list[str] = None

    # stats
    words: int = 0
    chapters_written: int = 1
    chapters_expected: int = 1  # -1 means ? chapters
    kudos: int = 0
    comments: int = 0
    bookmarks: int = 0
    hits: int = 0
    updated: date = None
    published: date = None

    def __init__(self, work_id):
        self.work_id = work_id
        self.state = State.UNINITIALIZED

        response = make_ao3_request("https://archiveofourown.org/works/{}".format(work_id))
        if response.status_code != requests.codes.ok:
            self.state = State.REQUEST_FAILED
            return

        self.soup = response.soup
        self.locked = response.locked_fic
        self.state = State.INITIALIZED

        self._parse()
        self.state = State.PARSED

    def _parse(self) -> None:
        """Parse an AO3 work."""
        self._parse_preface()
        self._parse_meta()

    def _parse_meta(self) -> None:
        """Parse the meta of an AO3 work.
        Handles rating, category, fandoms, warnings, relationships, characters,
        freeform tags, series, words, chapters, kudos, updated, and published.

        Anything in the box of info above the work itself.
        """
        work_meta = self.soup.find(class_="work meta group")
        self._parse_tags(work_meta)
        self._parse_series(work_meta)
        self._parse_collections(work_meta)
        self._parse_stats(work_meta)

    def _parse_preface(self) -> None:
        """Parse the preface of an AO3 work.
        Handles title, authors, summary, and notes.
        """

        preface = self.soup.find(class_="preface group")

        # Title
        self.title = preface.h2.string.strip()

        # Authors
        # todo: Can authors really be something other than <a> tags?
        author_string = preface.h3.string
        if author_string is None:
            self.authors = list(map(lambda x: x.string, preface.h3.find_all("a")))
        else:
            self.authors = [author_string.strip()]

        # Summary
        summary = preface.find(class_="summary module")
        if summary:
            self.summary = format_html(summary)

        # Notes
        notes = preface.find(class_="notes module")
        if notes:
            self.notes = format_html(notes)

    def _parse_tags(self, work_meta=None) -> None:
        """Parse the tags of an AO3 work."""
        if work_meta is None:
            work_meta = self.soup.find(class_="work meta group")

        # Rating, Warnings, Category
        rating = work_meta.find("dd", class_="rating tags")
        self.ratings = list(map(lambda x: x.string, rating.find_all("a")))

        warnings = work_meta.find("dd", class_="warning tags")
        self.warnings = list(map(lambda x: x.string, warnings.find_all("a")))

        if category := work_meta.find("dd", class_="category tags"):
            self.category = list(map(lambda x: x.string, category.find_all("a")))

        # Fandoms
        fandoms = work_meta.find("dd", class_="fandom tags")
        self.fandoms = list(map(lambda x: x.string, fandoms.find_all("a")))

        # Relationships, Characters (optional)
        if relationships := work_meta.find("dd", class_="relationship tags"):
            self.relationships = list(map(lambda x: x.string, relationships.find_all("a")))

        if characters := work_meta.find("dd", class_="character tags"):
            self.characters = list(map(lambda x: x.string, characters.find_all("a")))

        # Freeform Tags
        if freeform := work_meta.find("dd", class_="freeform tags"):
            self.freeform = list(map(lambda x: x.string, freeform.find_all("a")))

        # Language (todo: find a better place for this)
        language = work_meta.find("dd", class_="language")
        self.language = language.string

    def _parse_series(self, work_meta=None) -> None:
        """Parse the series that an AO3 work is a part of."""
        if work_meta is None:
            work_meta = self.soup.find(class_="work meta group")

        if series := work_meta.find("dd", class_="series"):
            series = series.find_all(class_="position")

            self.series = []
            for element in series:
                series_text = element.text.split()
                # handles both old and new series formats
                # Todo: check if this is still necessary
                if series_text[3] == "the" and series_text[-1] == "series":
                    series_name = " ".join(series_text[4:-1])
                else:
                    series_name = " ".join(series_text[3:])
                # store position, series name, and link
                self.series.append((series_text[1], series_name, element.a["href"]))

    def _parse_collections(self, work_meta=None) -> None:
        pass

    def _parse_stats(self, work_meta=None) -> None:
        """Parse the stats of an AO3 work.
        Handles words, chapters, kudos, updated, published, etc.
        """
        if work_meta is None:
            work_meta = self.soup.find(class_="work meta group")

        # dates
        published = work_meta.find("dd", class_="published")
        self.published = date.fromisoformat(published.string)

        if updated := work_meta.find("dd", class_="status"):
            self.updated = date.fromisoformat(updated.string)
        else:
            self.updated = self.published

        # status
        # todo: distinguish between complete, in progress, and abandoned if possible

        # chapters
        chapters = work_meta.find("dd", class_="chapters")
        chapters = chapters.string.split("/")
        self.chapters_written = atoi(chapters[0])
        if chapters[1] == "?":
            self.chapters_expected = -1
        else:
            self.chapters_expected = atoi(chapters[1])

        # words, kudos, comments, hits
        words = work_meta.find("dd", class_="words")
        self.words = atoi(words.string)

        self.kudos = 0
        if kudos := work_meta.find("dd", class_="kudos"):
            self.kudos = atoi(kudos.string)

        self.comments = 0
        if comments := work_meta.find("dd", class_="comments"):
            self.comments = atoi(comments.string)

        hits = work_meta.find("dd", class_="hits")
        self.hits = atoi(hits.string)

        # bookmarks
        if bookmarks := work_meta.find("dd", class_="bookmarks"):
            self.bookmarks = atoi(bookmarks.find("a").string)

    def get_characters_from_relationships(self) -> set[str]:
        """Get the characters from the relationships."""
        already_listed = set()
        for relationship in self.relationships[:3]:
            relationship = relationship.replace(" & ", "/")
            relationship = relationship.split("/")
            for character in relationship:
                if " (" in character:
                    character = character.split(" (")[0]
                already_listed.add(character)
        return already_listed

    def generate_summary(self) -> str:
        """Generate a summary of the work."""
        output = ":lock:" if self.locked else ""
        # Title, link, authors
        output += "**{}** (<https://archiveofourown.org/works/{}>) by **{}**\n" \
            .format(self.title, self.work_id, ", ".join(self.authors))

        # Series
        if self.series:
            series = self.series[:2]
            for s in series:
                output += "**Part {}** of the **{}** series (<https://archiveofourown.org{}>)\n" \
                    .format(s[0], s[1], s[2])

        # Fandoms
        if self.fandoms:
            fandoms = self.fandoms
            if len(fandoms) > 5:
                fandoms = ", ".join(fandoms[:5]) + ", …"
            else:
                fandoms = ", ".join(fandoms)
            output += "**Fandoms:** {}\n".format(fandoms)

        # Rating, Warnings, Category
        rating = ", ".join(self.ratings)
        if self.category:
            category = ", ".join(self.category)
            output += "**Rating:** {}          **Category:** {}\n".format(rating, category)
        else:
            output += "**Rating:** {}\n".format(rating)

        warnings = ", ".join(self.warnings)
        output += "**Warnings:** {}\n".format(warnings)

        # Relationships, Characters
        if self.relationships:
            relationships = self.relationships.copy()
            if len(relationships) > 3:
                relationships = ", ".join(relationships[:3]) + ", …"
            else:
                relationships = ", ".join(relationships)
            output += "**Relationships:** {}\n".format(relationships)

        if self.characters:
            # clear out characters that are already listed in relationships
            characters = self.characters.copy()
            already_listed = self.get_characters_from_relationships()
            for character in self.characters:
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
                if self.relationships:
                    output += "**Additional Characters:** {}\n".format(characters)
                else:
                    output += "**Characters:** {}\n".format(characters)

        # Freeform Tags
        if self.freeform:
            if len(self.freeform) > 5:
                freeform = ", ".join(self.freeform[:5]) + ", …"
            else:
                freeform = ", ".join(self.freeform)
            output += "**Tags:** {}\n".format(freeform)

        # Summary
        if self.summary:
            output += "**Summary:** {}\n".format(self.summary)

        # Stats
        output += "**Words:** {} **Chapters:** {} **Kudos:** {} **Updated:** {}\n" \
            .format(self.words, self.chapters_written, self.kudos, self.updated)

        return output


def generate_ao3_series_summary(link):
    """Generate the summary of an AO3 work.

    link should be a link to an AO3 series
    Returns the message with the series info, or else a blank string
    """
    r = requests.get(link, headers=HEADERS)
    if r.status_code != requests.codes.ok:
        return ""
    soup = BeautifulSoup(r.text, "lxml")
    if r.url == "https://archiveofourown.org/users/login?restricted=true":
        ao3_session = AO3.Session(config.AO3_USERNAME, config.AO3_PASSWORD)
        soup = ao3_session.request(link)
        locked_fic = True
    else:
        locked_fic = False

    title = soup.find("h2", class_="heading").text.strip()
    preface = soup.find(class_="series meta group")
    next_field = preface.dd
    author = ", ".join(map(lambda x: x.string, next_field.find_all("a")))
    next_field = next_field.find_next_sibling("dd")
    begun = next_field.string
    next_field = next_field.find_next_sibling("dd")
    updated = next_field.string
    next_field = next_field.find_next_sibling("dt")
    if next_field.string == "Description:":
        next_field = next_field.find_next_sibling("dd")
        description = format_html(next_field)
        next_field = next_field.find_next_sibling("dt")
    else:
        description = None
    if next_field.string == "Notes:":
        next_field = next_field.find_next_sibling("dd")
        notes = format_html(next_field)
        next_field = next_field.find_next_sibling("dt")
    else:
        notes = None
    next_field = next_field.find_next_sibling("dd").dl.dd
    words = next_field.string
    next_field = next_field.find_next_sibling("dd")
    works = next_field.string
    complete = next_field.find_next_sibling("dd").string

    # format output
    if not locked_fic:
        output = "**{}** (<{}>) by **{}**\n".format(title, link, author)
    else:
        output = ":lock: **{}** (<{}>) by **{}**\n".format(title, link, author)
    if description:
        output += "**Description:** {}\n".format(description)
    # if notes:
    #     output += "**Notes:** {}\n".format(notes)
    output += "**Begun:** {} **Updated:** {}\n".format(begun, updated)
    output += "**Words:** {} **Works:** {} **Complete:** {}\n\n".format(
        words, works, complete)

    # Find titles and links to first few works
    works = soup.find_all(class_=re.compile("work blurb group work-.*"))
    for i in range(min(3, len(works))):
        title = works[i].h4.a
        output += "{}. __{}__: <https://archiveofourown.org{}>\n".format(
            i + 1, title.string, title["href"])
    if len(works) == 4:
        title = works[3].h4.a
        output += "4. __{}__: <https://archiveofourown.org{}>".format(
            title.string, title["href"])
    elif len(works) > 4:
        output += "        [and {} more works]".format(len(works) - 3)
    else:
        output = output[:-1]

    return output


def identify_work_in_ao3_series(link, number):
    """Do something.

    link should be a link to a series, number is an int for which fic
    Returns the link to that number fic in the series, or else None
    """
    r = requests.get(link, headers=HEADERS)
    if r.status_code != requests.codes.ok:
        return None
    if r.url == "https://archiveofourown.org/users/login?restricted=true":
        return None
    soup = BeautifulSoup(r.text, "lxml")

    preface = soup.find(class_="series meta group")
    next_field = preface.find("dl", class_="stats").dd
    next_field = next_field.find_next_sibling("dd")
    works = atoi(next_field.string)
    if works < number:
        return None

    # Find link to correct work
    works = soup.find_all(class_=re.compile("work blurb group work-.*"))
    fic = works[number - 1]
    return fic.h4.a["href"]
