#!/usr/bin/env python3

import requests

from bs4 import BeautifulSoup
from lxml import etree as ET

abstracts = {}
titles = {}
rooms = {}

for url in ["https://open-access-tage.de/open-access-tage-2022-bern/programm/mo-1992022",
            "https://open-access-tage.de/open-access-tage-2022-bern/programm/di-2092022",
            "https://open-access-tage.de/open-access-tage-2022-bern/programm/mi-2192022"]:

    response = requests.get(url=url)
    soup = BeautifulSoup(response.content, 'html.parser')
    all_results = soup.select('main div:has(header) div>div:has(h3)')

    for element in all_results:
        title = ""
        content = ""
        for child in element.children:
            # each session starts with a h3 title and is then followed by several other nodes as its content,
            # until the next h3 title starts
            if child.name == 'h3':
                # save information so far
                if len(title) > 0:
                    abstracts[title_short] = content.strip().replace(u'\xa0', u' ')
                    titles[title_short] = title
                # restart with the next one
                title = child.text.strip().replace(u'\xa0', u' ')
                title_short = title.split(":")[0]
                content = ""
            else:
                if child.text.strip() == "Zusammenfassung":
                    continue
                elif child.text.startswith("Ort:"):
                    room = next(child.children, None)
                    rooms[title_short] = room
                    cleaned = ""
                    for i, x in enumerate(child.children):
                        if i == 0:
                            continue
                        if x.name == "br" and len(cleaned) > 0:
                            cleaned += "<br/>"
                        else:

                            cleaned += x.text
                    content += cleaned.strip()
                else:
                    content += str(child)
        # save information from last session on that side
        if len(title) > 0:
            abstracts[title_short] = content.strip().replace(u'\xa0', u' ')
            titles[title_short] = title


tree = ET.parse('oat22.skeleton.xml')
root_node = tree.getroot()

for event in root_node.findall('day/room/event'):
    title = event.find('title').text.strip()
    title_short = title.split(":")[0]
    room = event.find('room').text.strip()
    abstract = event.find('abstract')
    if title in ["Kaffee", "Mittagspause"]:
        continue
    if title_short in abstracts:
        abstract.text = abstracts[title_short]
    else:
        print("\n")
        print(title_short, title, "NOT FOUND on website")
    if title_short in rooms and rooms[title_short].find(room) < 0:
        print("Warning: Rooms mismatch")
        print("\t" + room)
        print("\t" + rooms[title_short])
        print("\t" + title_short)
    if title != titles[title_short]:
        print("Warning: Title mismatch")
        print("\t" + title)
        print("\t" + titles[title_short])
    current_abstract = event.find('abstract')

tree.write("oat22.xml")
