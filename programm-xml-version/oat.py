#!/usr/bin/env python3

import requests

from bs4 import BeautifulSoup
from lxml import etree as ET

abstracts = {}
titles = {}
rooms = {}
times = {}

for url in ["https://open-access-tage.de/open-access-tage-2023-berlin/programm/mittwoch-27092023",
            "https://open-access-tage.de/open-access-tage-2023-berlin/programm/donnerstag-28092023",
            "https://open-access-tage.de/open-access-tage-2023-berlin/programm/freitag-29092023"]:

    response = requests.get(url=url)
    soup = BeautifulSoup(response.content, 'html.parser')
    all_results = soup.select('main div:has(header) div>div:has(h3)')

    for element in all_results:
        title = ""
        content = ""
        # save times, which are written on the left side
        ancestors = [element.parent, element.parent.parent, element.parent.parent.parent,
                     element.parent.parent.parent.parent]
        for a in ancestors:
            left_side = a.find("header")
            if left_side is not None:
                break
        for child in element.children:
            # each session starts with a h3 title and is then followed by several other nodes as its content,
            # until the next h3 title starts
            if child.name == 'h3':
                # save information so far
                if len(title) > 0:
                    abstracts[title_short] = content.strip().replace(u'\xa0', u' ')
                    titles[title_short] = title
                    times[title_short] = left_side.text.strip()
                # restart with the next one
                title = child.text.strip().replace(u'\xa0', u' ')
                if title.startswith(("Session", "Workshop", "Keynote")):
                    title_short = title.split(":")[0]
                else:
                    title_short = title
                content = ""
            else:
                if child.text.strip() == "Zusammenfassung":
                    continue
                elif child.text.startswith("Ort:"):
                    room = child.text[child.text.find(": ") + 1:].strip()#next(child.children, None)
                    rooms[title_short] = room
                    cleaned = ""
                    ignore = True
                    for i, x in enumerate(child.children):
                        if ignore:
                            if x.name == "br":
                                ignore = False
                        else:
                            if x.name == "br":
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
            times[title_short] = left_side.text.strip()



tree = ET.parse('oat23.skeleton.xml')
root_node = tree.getroot()
seen_ids = []

for event in root_node.findall('day/room/event'):
    ref = event.attrib["id"]
    if ref in seen_ids:
        print("Warning: Same id used multiple times:", ref)
    else:
        seen_ids.append(ref)
    # title, track, type
    title = event.find('title').text.strip()
    if title.startswith(("Session", "Workshop", "Keynote")):
        title_short = title.split(":")[0]
    else:
        title_short = title
    if title_short in ["Postersession", "Tool-Marktplatz"]:
        track = title_short
    elif "Session" in title_short or "Keynote" in title_short:
        track = "Vortragssession"
    elif "Workshop" in title_short:
        track = "Workshop"
    else:
        track = "Sonstige"
    if event.find("track") is None:
        track_node = ET.SubElement(event, "track")
        track_node.text = track
    # TODO: Is this necessary or can we also delete it?
    if event.find("type") is None:
        type_node = ET.SubElement(event, "type")
        type_node.text = "NA"
    # get room information from parent and write it as new node
    if event.find("room") is None:
        room_parent_node = event.getparent()
        room = room_parent_node.attrib["name"]
        room_node = ET.SubElement(event, "room")
        room_node.text = room
    else:
        room = event.find('room').text.strip()
    # get date information from parent and write it together with starting time as new node
    if event.find("date") is None:
        date_parent_node = event.getparent().getparent()
        date = date_parent_node.attrib["date"]
        date_node = ET.SubElement(event, "date")
        time = event.find("start").text
        date_node.text = date + "T" + time + ":00+02:00"

    abstract = event.find('abstract')
    if title in ["Kaffeepause", "Mittagspause", "Ausklang", "Ankommen und Registrierung"]:
        continue
    if title_short in times:
        [start, end] = times[title_short].split('–')
        start_time = [int(x) for x in start.split(".")]
        comparison_time = [int(x) for x in event.find("start").text.split(":")]
        if start_time != comparison_time:
            print("Warning: Mismatch starting times", start, event.find("start").text, "[" + title_short + "]")
    if title_short in abstracts:
        abstract.text = abstracts[title_short]
    else:
        print("\n")
        print(title_short, title, "NOT FOUND on website")
    # check for consistency
    if title_short in rooms and rooms[title_short].find(room) < 0:
        print("Warning: Rooms mismatch")
        print("\t" + room)
        print("\t" + rooms[title_short])
        print("\t" + title_short)
    if title != titles[title_short]:
        print("Warning: Title mismatch")
        print("\t" + title)
        print("\t" + titles[title_short])
    #current_abstract = event.find('abstract')
ET.indent(root_node, space="  ")
tree.write("oat23.xml", pretty_print=True)
