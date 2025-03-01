import locale
import pytz
import re
import requests
import uuid

from bs4 import BeautifulSoup
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file
from io import BytesIO
from typing import List

app = Flask(__name__)
locale.setlocale(locale.LC_TIME, "nl_NL")

def parse_date(date: str) -> str:
    """Parses dates from text to datetimes

    Args:
        date (str): Date string, e.g. Monday 15 November

    Returns:
        str: Parsed date in ymd format.
    """
    date_format = "%d %B"
    current_date = datetime.now()
    date_parts = date.split(" ")
    day_month = f"{date_parts[1]} {date_parts[2]}"
    parsed_date = datetime.strptime(day_month, date_format).date()
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


def create_ics_event(event: dict) -> str:
    """Create calendar events for the selected time slots

    Args:
        event (dict): event details to parse in the calendar event

    Returns:
        str: Calendar event in ics format
    """
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
        f"SUMMARY:{event['activity']}\n"
        f"LOCATION:{event['location']}\n"
        f"DESCRIPTION:{event['activity']}\n"
        "BEGIN:VALARM\n"
        "TRIGGER:-PT15M\n"
        "DESCRIPTION:Swimming time! :)\n"
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

