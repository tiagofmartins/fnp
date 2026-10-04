#!/usr/bin/env python3
"""Parses the contents and periods data from a Google Sheet
and determines which content should be playing at a given
moment, based on each period date/time rules and priority.
"""

from datetime import date, datetime, time, timedelta

import holidays

SHEET_CONTENTS = "Contents"
SHEET_PERIODS = "Periods"

VALUE_YES = "sim"
DATE_ANY_DAY = "qualquer"
DATE_WEEKDAY = "2a-6a"
DATE_WEEKEND = "sab-dom"
DATE_WEEKDAYS = ["2a", "3a", "4a", "5a", "6a", "sab", "dom"]
DATE_HOLIDAY = "feriado"
DATE_RANGE = "dias ->"
DATE_SPECIFIC = "dia ->"
DATE_TODAY = "hoje"

DATE_PRIORITY = {
    DATE_ANY_DAY: 1,
    DATE_WEEKDAY: 2,
    DATE_WEEKEND: 2,
    **{day: 3 for day in DATE_WEEKDAYS},
    DATE_HOLIDAY: 4,
    DATE_RANGE: 5,
    DATE_SPECIFIC: 6,
    DATE_TODAY: 7,
}

DATE_MATCHERS = {
    DATE_ANY_DAY: lambda check_date, d1, d2: True,
    DATE_WEEKDAY: lambda check_date, d1, d2: check_date.weekday() < 5,
    DATE_WEEKEND: lambda check_date, d1, d2: check_date.weekday() >= 5,
    **{day: (lambda d: lambda check_date, d1, d2: check_date.weekday() == d)(d) for d, day in enumerate(DATE_WEEKDAYS)},
    DATE_HOLIDAY: lambda check_date, d1, d2: check_date in holidays.country_holidays("PT"),
    DATE_RANGE: lambda check_date, d1, d2: d1 <= check_date <= d2,
    DATE_SPECIFIC: lambda check_date, d1, d2: check_date == d1,
    DATE_TODAY: lambda check_date, d1, d2: True,
}


def rows_to_dicts(rows, header_rows=1):
    """Convert a list of lists (rows) into a list of dicts,
    using the first row as the column names.
    Ignores empty rows and columns with no name.
    Raises ValueError if duplicate column names are found."""
    # Extract the header row and create a list of column names
    header = rows[0]
    col_names = [cell.split("(")[0] for cell in header] # Ignore anything in parentheses
    col_names = [name.strip().lower() for name in col_names] # Lowercase and strip whitespace
    col_names = [name.replace(" ", "_") for name in col_names] # Replace spaces with underscores

    # Check for duplicate column names and raise an error if found
    col_names_duplicated = {name for name in col_names if name and col_names.count(name) > 1}
    if col_names_duplicated:
        raise ValueError(f"Duplicate column names: {col_names_duplicated}")

    # Parse the remaining rows into a list of dictionaries
    parsed_rows = []
    for row in rows[header_rows:]:
        row = [value.strip() for value in row]
        if not any(row):
            continue # Skip empty rows
        parsed_rows.append({name: value for name, value in zip(col_names, row) if name}) # Ignore columns with no name
    return parsed_rows


def parse_contents(rows):
    parsed_contents = []
    for row in rows:
        try:
            if any(not value for name, value in row.items() if name != "notes"):
                continue # Skip rows with missing required fields
            if row["active"].lower() != VALUE_YES:
                continue # Skip inactive rows
            if row["id"] in (c["id"] for c in parsed_contents):
                continue # Skip duplicate ids
            content = {}
            content["id"] = row["id"]
            content["random"] = row["random"].lower() == VALUE_YES
            content["cmd_lines"] = [line for line in (line.strip() for line in row["cmd"].split("\n")) if line]
            parsed_contents.append(content)
        except Exception as e:
            # print(f"Error parsing row: {row}\n{type(e).__name__}: {e}")
            pass
    return parsed_contents


def parse_periods(rows, content_ids=[]):
    parsed_periods = []
    for row in rows:
        try:
            if any(not row[name] for name in ("active", "date", "content")):
                continue # Skip rows with missing required fields
            if row["active"].lower() != VALUE_YES:
                continue # Skip inactive rows
            period = {}

            # ---------- DATE

            # Parse date and determine its priority and matcher function
            period["date"] = row["date"].lower()
            period["priority"] = DATE_PRIORITY[period["date"]]
            period["matcher"] = DATE_MATCHERS[period["date"]]

            # Parse start and end dates if applicable
            period["start"], period["end"] = None, None
            if period["date"] in [DATE_RANGE, DATE_SPECIFIC]:
                period["start"] = date.fromisoformat(row["start"])
                if period["date"] == DATE_RANGE:
                    period["end"] = date.fromisoformat(row["end"])

            # Skip if start date is after end date
            if period["start"] and period["end"] and period["start"] > period["end"]:
                continue

            # ---------- TIME

            # Collect all columns with start and end times, allowing for multiple pairs of columns
            time_col_names = []
            pair_index = 1
            while f"start_{pair_index}" in row and f"end_{pair_index}" in row:
                time_col_names += [f"start_{pair_index}", f"end_{pair_index}"]
                pair_index += 1

            # Parse time strings into time objects, allowing for None if blank
            day_times = []
            for col in time_col_names:
                day_times.append(time.fromisoformat(row[col]) if row[col] else None)

            # Group the time periods into pairs (start, end)
            pair_times = list(zip(day_times[::2], day_times[1::2]))

            # Skip if time pairs are not both defined or both None
            if any((t1 is not None) != (t2 is not None) for t1, t2 in pair_times):
                continue

            # Filter out empty pairts
            pair_times = [pair for pair in pair_times if pair[0] is not None]

            # Skip if any time pair start is after or equal to its end
            if any(t1 >= t2 for t1, t2 in pair_times):
                continue

            # Default to the whole day if no times are specified
            if not pair_times:
                pair_times = [(time(0, 0), time(23, 59))]

            # Add parsed time pairs to the current period as a list of lists
            period["time"] = [list(pair) for pair in pair_times]

            # ---------- CONTENT

            # Parse comma-separated contents with optional durations
            period["content"] = []
            for item in row["content"].split(","):
                content_id, _, content_dur = item.strip().partition(":")
                content_dur = int(content_dur) if content_dur else None
                period["content"].append([content_id, content_dur])

            # Skip if the period references a content that does not exist
            if any(content_id not in content_ids for content_id, _ in period["content"]):
                continue

            # Add the parsed period to the list
            parsed_periods.append(period)

        except Exception as e:
            # print(f"Error parsing row: {row}\n{type(e).__name__}: {e}")
            pass
    return parsed_periods


def find_matching_period(check_datetime, periods):
    """Finds which period applies at a given moment.
    If more than one period matches, picks the most relevant one.
    Returns None if none match."""
    check_date, check_time = check_datetime.date(), check_datetime.time()
    matches = []
    for period in periods:
        if period["matcher"](check_date, period["start"], period["end"]):
            if any(start <= check_time <= end for start, end in period["time"]):
                matches.append(period)
    if not matches:
        return None
    return max(matches, key=lambda period: period["priority"])


def preview_periods(start_datetime, end_datetime, periods):
    """Walks through the time range, minute by minute, and records each moment
    the active period changes, as a list of [datetime, period] pairs."""
    changes = []
    prev_period = None
    check_datetime = start_datetime
    while check_datetime <= end_datetime:
        period = find_matching_period(check_datetime, periods)
        if period is not prev_period:
            changes.append([check_datetime, period])
            prev_period = period
        check_datetime += timedelta(minutes=1)
    return changes


if __name__ == "__main__":
    from data_read import SERVICE_ACCOUNT_FILE, SPREADSHEET_KEY_FILE, GSheetReader

    # Fetch the data from the Google Sheets
    reader = GSheetReader([SHEET_CONTENTS, SHEET_PERIODS],
                          SERVICE_ACCOUNT_FILE,
                          SPREADSHEET_KEY_FILE,
                          check_interval_secs=0,
                          debounce_secs=0)
    data = reader.get_data()

    # Parse the contents and periods from the fetched data
    contents = parse_contents(rows_to_dicts(data[SHEET_CONTENTS]))
    periods = parse_periods(rows_to_dicts(data[SHEET_PERIODS]), {c["id"] for c in contents})

    # Preview the periods for the next days
    preview = preview_periods(
        start_datetime=datetime.now(),
        end_datetime=datetime.now() + timedelta(days=15),
        periods=periods
    )
    for change in preview:
        dt, period = change
        content = ",".join(item[0] for item in period["content"]) if period else "off"
        print(dt.strftime("%Y-%m-%d %H:%M"), content)