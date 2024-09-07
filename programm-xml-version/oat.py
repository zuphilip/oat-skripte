#!/usr/bin/env python3

import re
import requests

from bs4 import BeautifulSoup
from datetime import date, datetime
from xml.dom import minidom

from pentabarf.Conference import Conference
from pentabarf.Day import Day
from pentabarf.Event import Event
from pentabarf.Room import Room

global_counter = 0
seen_ids = []
rooms_list = []

conference = Conference(
    title="Open Access Tage 2024",
    start=date(2024, 9, 10),
    end=date(2024, 9, 12),
    days=3,
    timeslot_duration="00:30",
    venue="TH Köln",
    city="Köln"
)

def generate_id(title_short):
    if title_short.startswith(("Session", "Workshop", "Keynote")):
        counter = title_short.split(" ")[1]
        if counter.isdigit():
            return title_short[0].lower() + counter
        else:
            print("ERROR: Failed to create an id. Unexpected format (title_short):", title_short)
    else:
        return "counter"
def determine_track(title_short):
    if title_short in ["Postersession", "Tool-Marktplatz", "Toolmarktplatz"]:
        return title_short
    elif "Session" in title_short or "Keynote" in title_short:
        return "Vortragssession"
    elif "Workshop" in title_short:
        return "Workshop"
    else:
        return "Sonstige"

# returns start time and duration both in the format hh:mm
def extract_start_time(time_span):
    [start, end] = time_span.split('–')
    start_time = [int(x) for x in re.split("\.|:", start)]
    end_time = [int(x) for x in re.split("\.|:", end)]
    diff = (end_time[0]-start_time[0])*60+(end_time[1]-start_time[1])
    if len(start) == 4: # e.g. 9:00
        start = "0" + start

    return start.replace(".", ":"), '%02d:%02d' % (diff // 60, diff % 60)

for url in ["https://open-access-tage.de/open-access-tage-2024-koeln/koeln/programm/dienstag-10092024",
            "https://open-access-tage.de/open-access-tage-2024-koeln/koeln/programm/mittwoch-11092024",
            "https://open-access-tage.de/open-access-tage-2024-koeln/koeln/programm/donnerstag-12092024"]:

    # for each day round it up to the new X00 for better distinguishable ids
    global_counter = (int(str(global_counter)[0])+1)*100

    day_string = "-".join((url[-4:], url[-6:-4], url[-8:-6]))
    day = Day(date=datetime.strptime(day_string, "%Y-%m-%d"))
    conference.add_day(day)

    try:
        with open("oat24-rooms.txt", 'r', encoding="utf-8") as room_file:
            for line in room_file:
                # the main rooms in this order will be written first in the schedule
                day.add_room(Room(name=line.rstrip()))
    except FileNotFoundError:
        print('No rooms file found')

    response = requests.get(url=url)
    soup = BeautifulSoup(response.content, 'html.parser')
    # The website contains of two different sides with times (left)
    # and the different sessions/workshops (right side), but in the html
    # structure they simply follow each other. The characteristics of the
    # left hand side is a header element and on the right hand side usually
    # the different sessions/workshops starts with a h3 element.
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
        if left_side is None:
            print("ERROR: No left side with times is found.")
        else:
            time_span = left_side.text.strip()
        # We will only create events if we reach a new element. In order to make this also work for
        # the last children, we will add a new artificial h3 element at the end.
        new_h3 = soup.new_tag("h3")
        element.append(new_h3)
        for child in element.children:
            # each session starts with a h3 title and is then followed by several other nodes as its content,
            # until the next h3 title starts (exception like the opening might exist)
            if child.name == 'h3':
                if title in ["Eröffnung und Keynote 1", "Keynote 3: Umsetzung der Open Science-Agenda – Der Beitrag der Deutschen UNESCO-Kommission"] and child.text != "":
                    content += str(child)
                    continue
                # save information so far before dealing with this new session/workshop starting with another h3 element
                if len(title) > 0:
                    new_id = generate_id(title_short)
                    if new_id == "counter":
                        global_counter += 1
                        new_id = global_counter
                    if new_id in seen_ids:
                        print("Warning: Same id used multiple times:", new_id)
                    else:
                        seen_ids.append(new_id)
                    start, duration = extract_start_time(time_span)
                    track = determine_track(title_short)

                    session_object = Event(
                        id=new_id,
                        date=datetime.fromisoformat(day_string + "T" + start + ":00+02:00"),
                        start=start,
                        duration=duration,
                        track=track,
                        abstract=content.strip().replace(u'\xa0', u' '),
                        title=title,
                        type='Vortrag'
                    )

                    if room == "TBA":
                        room = "-".join((room, str(new_id)))
                    # there are different whitespaces used in the names of rooms
                    # and therefore we need to normalize them first
                    room = " ".join(room.split())
                    if room not in [r.name for r in day.room_objects]:
                        day.add_room(Room(name=room))
                    for r in day.room_objects:
                        if r.name == room:
                            r.add_event(session_object)
                            break
                    if room not in rooms_list and track != "Sonstige":
                        # add main rooms to list which will be written into file
                        rooms_list.append(room)

                # restart with the next one
                title = child.text.strip().replace(u'\xa0', u' ')
                if title.startswith(("Session", "Workshop", "Keynote")):
                    title_short = title.split(":")[0]
                else:
                    title_short = title
                content = ""
                if title_short.startswith("Führung "):
                    room = " ".join(title_short.split(" ")[1:])
                else:
                    room = "TBA"
            else:
                if child.text.strip() == "Zusammenfassung":
                    continue
                elif child.text.startswith("Ort:"):
                    room = child.contents[0][child.contents[0].find(": ") + 1:].strip()
                    if room == "":
                        room = child.text[4:].strip()
                    # The same node with the room information also contains the name
                    # of the moderation and a br node inbetween. Thus we go through all
                    # child nodes and ignore the first text node (room) as well as the
                    # following br node.
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
                    if cleaned.strip() != "":
                        content += cleaned.strip() + "<br/><br/>"
                else:
                    content += str(child)


xmldata = conference.generate("Erzeugt von https://github.com/zuphilip/oat-skripte um " + str(datetime.now()))
reparsed = minidom.parseString(xmldata.decode("utf-8"))
# delete day_change as it cannot be empty
for node in reparsed.getElementsByTagName('day_change'):
    node.parentNode.removeChild(node)
# delete some empty nodes and empty attributes
deleted = 0
for ignore in ['description', 'conf_url', 'full_conf_url', 'released']:
    for node in reparsed.getElementsByTagName(ignore):
        if node.toxml() == "<" + ignore + "/>":
            node.parentNode.removeChild(node)
            deleted += 1
# delete all date nodes which are unneccessary and make trouble because of the timezoning
#for node in reparsed.getElementsByTagName('date'):
#    node.parentNode.removeChild(node)
#    deleted += 1
print("INFO: Deleted", deleted, "empty nodes + date nodes")
for node in reparsed.getElementsByTagName('person'):
    if node.getAttribute('id') == "None":
        node.removeAttribute('id')

# Output in file
with open("oat24.xml", 'w', encoding="utf-8") as outfile:
    outfile.write(reparsed.toprettyxml(indent="  "))
# Save another copy which will not be overwritten, when rerun on another day
name = "oat24-" + str(date.today()) + ".xml"
with open(name, 'w', encoding="utf-8") as outfile:
    outfile.write(reparsed.toprettyxml(indent="  "))
# Inspect differences in the output files with e.g. git diff

# write rooms of main program sorted in file
if len(rooms_list)>0:
    with open("oat24-rooms.txt", 'w', encoding="utf-8") as outfile:
        for room in sorted(rooms_list):
            outfile.write(room + "\n")