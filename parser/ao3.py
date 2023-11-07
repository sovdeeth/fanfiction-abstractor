from parser.common import format_html, HEADERS, atoi
from bs4 import BeautifulSoup
import AO3
import config
import re
import requests

AO3Session = AO3.Session(config.AO3_USERNAME, config.AO3_PASSWORD)


class AO3WorkParser:
    work: AO3.Work

    def __init__(self, work_id):
        self.work = AO3.Work(work_id, AO3Session, load_chapters=False)

    def get_characters_from_relationships(self) -> set[str]:
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
        if self.work.series:
            series = self.work.series[:2]
            for s in series:
                output += "**Part {}** of the **{}** series (<https://archiveofourown.org/series/{}>)\n" \
                    .format("x", s.name, s.id)

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
            already_listed = self.get_characters_from_relationships()
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
            output += "**Summary:** {}\n".format(self.work.summary)

        # Stats
        output += "**Words:** {} **Chapters:** {}/{} **Kudos:** {} **Updated:** {}\n" \
            .format(self.work.words, self.work.nchapters, self.work.expected_chapters,
                    self.work.kudos, self.work.date_updated.strftime("%Y-%m-%d"))

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
