import pytz
import re
import requests
import uuid
import random

from bs4 import BeautifulSoup
from datetime import datetime
from babel.dates import get_month_names
from flask import Flask, render_template, request, jsonify, send_file
from io import BytesIO
from typing import List
from functools import lru_cache

app = Flask(__name__)

@lru_cache(maxsize=128)
def get_fun_fact_for_date(date_str):
    # date_str format: 'YYYY-MM-DD'
    try:
        month = int(date_str.split('-')[1])
        day = int(date_str.split('-')[2])
        url = f"https://byabbe.se/on-this-day/{month}/{day}/events.json"
        response = requests.get(url, timeout=.5)
        if response.ok:
            data = response.json()
            # Pick a random event or the first one
            if data.get("events"):
                event = data["events"][0]
                year = event.get("year", "")
                description = event.get("description", "")
                return f"In {year}: {description}"
    except Exception:
        pass
    return "No fun fact available for this date."


def parse_date(date: str) -> str:
    """Parses dates from text to datetimes

    Args:
        date (str): Date string, e.g. Monday 15 November

    Returns:
        str: Parsed date in ymd format.
    """
    date_format = "%d %m"
    current_date = datetime.now()
    date_parts = date.split(" ")
    day = date_parts[1]
    month_name = date_parts[2].lower()
    month_names = get_month_names(width="wide", locale="nl_NL")
    month_map = {name.lower(): idx for idx, name in month_names.items()} 
    month = month_map[month_name]
    parsed_date = datetime.strptime(f"{day} {month}", date_format).date()
    # parsed_date = datetime.strptime(day_month, date_format).date()
    if current_date.month == 12 and parsed_date.month == 1:
        # Shift the year by 1 if the date lies in january
        parsed_date = parsed_date.replace(year=current_date.year + 1)
    else:
        parsed_date = parsed_date.replace(year=current_date.year)
    return parsed_date


def fetch_pool_data(locations: List[str]) -> List[dict]:
    """Fetches all the pool times for the 3 different pools in Rotterdam centre.

    Returns:
        List[dict]: List of all fetched times for the "Banenzwemmen" activity
        for Rotterdam pools. Includes start_time, end_time, location.
    """
    base_attr = "block-roster__program-item-"
    all_activities = []

    for location in locations:
        url = f"https://www.sportbedrijfrotterdam.nl/locatie/{location}#roster"
        response = requests.get(url)

        if response.ok:
            soup = BeautifulSoup(response.content, "html.parser")

            for roster_day in soup.find_all(attrs={"class": "block-roster__day"}):
                date = roster_day.find(attrs="block-roster__title").text.strip()
                date = parse_date(date)
                if date < datetime.now().date():
                    continue

                banenzwemmen = roster_day.find_all(
                    ["span", "a"],
                    string=re.compile("Banenzwemmen( (?!55\\+)\\d+ banen)?$"),
                )
                if len(banenzwemmen) > 0:
                    for baanzwem_element in banenzwemmen:
                        baan = baanzwem_element.parent
                        times = baan.find(attrs=base_attr + "time").text.strip()
                        all_activities.append(
                            {
                                "date_for_sorting": date.strftime("%Y%m%d"),
                                "date": date.strftime("%d-%m-%Y"),
                                "day": date.strftime("%A"),
                                "fun_fact": get_fun_fact_for_date(date.strftime("%Y-%m-%d")),
                                "location": location,
                                "start_time": times[0:5],
                                "end_time": times[8:13],
                                "activity": baan.find(
                                    attrs=base_attr + "activity"
                                ).text.strip(),
                                "bad_details": baan.find(
                                    attrs=base_attr + "location"
                                ).text.strip(),
                            }
                        )
        else:
            print(f"Fetching error for {location}.")
    # Sort all activities by date
    all_activities.sort(key=lambda x: (x["date_for_sorting"], x["start_time"]))
    return all_activities

def get_swim_quote():
    swim_quotes = [
        '"The water is your friend. You dont have to fight with water, just share the same spirit as the water, and it will help you move." — Alexandr Popov',
        '"Just keep swimming." — Dory (Finding Nemo)',
        '"The harder you work, the harder it is to surrender." — Vince Lombardi',
        '"Dont wait for your ship to come in - swim out to it."',
        '"If you want to be the best, you have to do things that other people arent willing to do." — Michael Phelps',
        '"Swimming is more than a sport; its a way of life."',
        '"The pool is my happy place."',
        '"Winners never quit and quitters never win." — Vince Lombardi',
        '"Believe in yourself, take on your challenges, dig deep within yourself to conquer fears." — Chantal Sutherland',
        '"Success is not final, failure is not fatal: It is the courage to continue that counts." — Winston Churchill',
        '"The body achieves what the mind believes."',
        '"If you have a lane, you have a chance."',
        '"Swimmers do it in the water."',
        '"Pain is temporary. Pride is forever."',
        '"You cant put a limit on anything. The more you dream, the farther you get." — Michael Phelps',
        '"The only difference between try and triumph is a little umph." — Marvin Phillips',
        '"Dont count the laps. Make the laps count."',
        '"In the water, your only competition is yourself."',
        '"Champions keep playing until they get it right." — Billie Jean King',
        '"The best swimmers are the ones who never give up."',
        '"Every stroke brings you closer to your goal."',
        '"Swim with your heart, not just your arms."',
        '"The pool is my canvas, and swimming is my art."',
        '"Great things never come from comfort zones."',
        '"Push yourself because no one else is going to do it for you."',
        '"The difference between ordinary and extraordinary is that little extra." — Jimmy Johnson',
        '"Dont dream of winning, train for it."',
        '"You miss 100% of the shots you dont take." — Wayne Gretzky',
        '"The pain you feel today will be the strength you feel tomorrow."',
        '"Its not about being the best. Its about being better than you were yesterday."',
        '"Swim fast, have fun, and always be a good sport." — Missy Franklin',
        '"Hard work beats talent when talent doesnt work hard." — Tim Notke',
        '"Success is the sum of small efforts, repeated day in and day out." — Robert Collier',
        '"Dont watch the clock; do what it does. Keep going." — Sam Levenson',
        '"The only way to define your limits is by going beyond them." — Arthur Clarke',
        '"You are only one swim away from a good mood."',
        '"The water doesnt know your age." — Dara Torres',
        '"The water doesnt know your name."',
        '"Swim like theres no tomorrow."',
        '"The greatest pleasure in life is doing what people say you cannot do." — Walter Bagehot',
        '"If you fail to prepare, youre prepared to fail." — Mark Spitz',
        '"Dont be afraid to fail. Be afraid not to try."',
        '"The only bad workout is the one that didnt happen."',
        '"You dont have to be great to start, but you have to start to be great." — Zig Ziglar',
        '"The secret of getting ahead is getting started." — Mark Twain',
        '"The harder you train, the luckier you get." — Gary Player',
        '"Swim with passion, finish with pride."',
        '"The pool is my sanctuary."',
        '"Swim hard, swim smart, swim strong."',
        '"Dont let your dreams be dreams." — Jack Johnson',
        '"The only time success comes before work is in the dictionary." — Vidal Sassoon',
        '"You are stronger than you think."',
        '"Swim for the moments you cant put into words."',
        '"The water is where I belong."',
        '"Swim like a champion."',
        '"The best way to predict the future is to create it." — Abraham Lincoln',
        '"Swim with determination, finish with satisfaction."',
        '"The pool is my playground."',
        '"Swim to win, train to succeed."',
        '"Dont stop when youre tired. Stop when youre done." — Marilyn Monroe',
        '"Swim with confidence, finish with pride."',
        '"The water is my escape."',
        '"Swim with purpose, finish with pride."',
        '"The pool is my second home."',
        '"Swim with intensity, finish with integrity."',
        '"The water is my therapy."',
        '"Swim with courage, finish with honor."',
        '"The pool is my happy place."',
        '"Swim with focus, finish with pride."',
        '"The water is my motivation."',
        '"Swim with strength, finish with pride."',
        '"The pool is my inspiration."',
        '"Swim with heart, finish with pride."',
        '"The water is my passion."',
        '"Swim with energy, finish with pride."',
        '"The pool is my motivation."',
        '"Swim with drive, finish with pride."',
        '"The water is my inspiration."',
        '"Swim with ambition, finish with pride."',
        '"The pool is my passion."',
        '"Swim with enthusiasm, finish with pride."',
        '"The water is my drive."',
        '"Swim with excitement, finish with pride."',
        '"The pool is my energy."',
        '"Swim with joy, finish with pride."',
        '"The water is my ambition."',
        '"Swim with happiness, finish with pride."',
        '"The pool is my enthusiasm."',
        '"Swim with love, finish with pride."',
        '"The water is my excitement."',
        '"Swim with hope, finish with pride."',
        '"The pool is my joy."',
        '"Swim with faith, finish with pride."',
        '"The water is my happiness."',
        '"Swim with optimism, finish with pride."',
        '"The pool is my love."',
        '"Swim with positivity, finish with pride."',
        '"The water is my hope."',
        '"Swim with gratitude, finish with pride."',
        '"The pool is my faith."',
        '"Swim with pride, finish with pride."',
        '"The water is my optimism."',
        '"Swim with respect, finish with pride."',
        '"The pool is my positivity."',
        '"Swim with honor, finish with pride."',
        '"The water is my gratitude."',
        '"Swim with integrity, finish with pride."',
        '"The pool is my respect."',
        '"Swim with dignity, finish with pride."',
        '"The water is my honor."',
        '"Swim with perseverance, finish with pride."',
        '"The pool is my integrity."',
        '"Swim with resilience, finish with pride."',
        '"The water is my dignity."',
    ]
    return random.choice(swim_quotes)


def create_ics_event(event: dict) -> str:
    """Create calendar events for the selected time slots

    Args:
        event (dict): event details to parse in the calendar event

    Returns:
        str: Calendar event in ics format
    """
    locations = {
        "zwemcentrum-rotterdam": """Annie M G Schmidtplein 8\, 3083 NZ Rotterdam\, Netherlands""",
        "sportcentrum-feijenoord": "Laan op Zuid 1055\, 3072 DB Rotterdam\, Netherlands",
        "sportcentrum-west": "Spaanseweg 4\, 3028 HW Rotterdam\, Netherlands",
    }
    
    tz = pytz.timezone("Europe/Amsterdam")
    event_date = datetime.strptime(event["date"], "%d-%m-%Y").date()
    start_time = datetime.strptime(event["start_time"], "%H:%M").replace(
        year=event_date.year, month=event_date.month, day=event_date.day, tzinfo=tz
    )
    end_time = datetime.strptime(event["end_time"], "%H:%M").replace(
        year=event_date.year, month=event_date.month, day=event_date.day, tzinfo=tz
    )
    uid = str(uuid.uuid4())

    calendar_event = (
        "BEGIN:VEVENT\n"
        f"UID:{uid}\n"
        f"DTSTAMP:{start_time.strftime('%Y%m%dT%H%M%S')}\n"
        f"DTSTART:{start_time.strftime('%Y%m%dT%H%M%S')}\n"
        f"DTEND:{end_time.strftime('%Y%m%dT%H%M%S')}\n"
        f"SUMMARY:Banenzwemmen {event['location']}\n"
        f"LOCATION:{locations.get(event['location'], event['location'])}\n"
        f"DESCRIPTION:{get_swim_quote()}. {event['activity']}\n"
        "BEGIN:VALARM\n"
        "TRIGGER:-PT15M\n"
        "ACTION:DISPLAY\n"
        "END:VALARM\n"
        "END:VEVENT\n"
    )
    return calendar_event


@app.route("/")
def index():
    locations = [
        "zwemcentrum-rotterdam",
        "sportcentrum-feijenoord",
        "sportcentrum-west",
    ]
    activities = fetch_pool_data(locations=locations)
    return render_template("index.html", activities=activities, locations=locations)


@app.route("/export_calendar", methods=["POST"])
def export_calendar():
    selected_slots = request.json.get("selected_slots", [])

    if not selected_slots:
        return jsonify({"error": "No slots selected"}), 400

    # Begin the iCalendar file
    calendar_header = (
        "BEGIN:VCALENDAR\nVERSION:2.0\n"
        "PRODID:-//YourCompany//NONSGML v1.0//EN\n"
    )
    calendar_footer = "END:VCALENDAR"

    calendar_content = calendar_header

    for slot in selected_slots:
        calendar_content += create_ics_event(slot)

    calendar_content += calendar_footer

    ics_file = BytesIO()
    ics_file.write(calendar_content.encode("utf-8"))
    ics_file.seek(0)

    return send_file(
        ics_file,
        as_attachment=True,
        download_name="schedule.ics",
        mimetype="text/calendar",
    )

