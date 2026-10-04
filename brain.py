#!/usr/bin/env python3
"""Keeps the contents scheduled in the Google Sheet running: periodically
checks which content should be playing right now and starts/stops the
underlying processes whenever that changes.
"""

import shlex
import time
from datetime import datetime

from data_parse import SHEET_CONTENTS, SHEET_PERIODS, find_matching_period, parse_contents, parse_periods, rows_to_dicts
from data_read import CHECK_INTERVAL_SECONDS, DEBOUNCE_SECONDS, SERVICE_ACCOUNT_FILE, SPREADSHEET_KEY_FILE, GSheetReader
from process_manager import Process

LOOP_INTERVAL_SECONDS = 5


def main():
    reader = GSheetReader(
        [SHEET_CONTENTS, SHEET_PERIODS],
        SERVICE_ACCOUNT_FILE,
        SPREADSHEET_KEY_FILE,
        check_interval_secs=CHECK_INTERVAL_SECONDS,
        debounce_secs=DEBOUNCE_SECONDS
    )
    running_processes = {} # content_id -> [Process, ...]
    contents_by_id = {}
    periods = []

    while True:
        # Fetch the data from the Google Sheets
        data = reader.get_data(only_if_modified=True)

        # If the data has changed, parse the contents and periods from the fetched data
        if data is not None:
            print(f"Fetched data at {datetime.now()}")
            contents = parse_contents(rows_to_dicts(data[SHEET_CONTENTS]))
            contents_by_id = {content["id"]: content for content in contents}
            periods = parse_periods(rows_to_dicts(data[SHEET_PERIODS]), contents_by_id.keys())

        # Determine which period applies at the current time
        period = find_matching_period(datetime.now(), periods)

        # Determine which content should be running based on the current period
        scheduled_content_ids = {content_id for content_id, _ in period["content"]} if period else set()

        # Compare the scheduled content with the currently running content
        # and start or stop processes as needed
        running_content_ids = set(running_processes.keys())
        if scheduled_content_ids != running_content_ids:

            # Stop any content that is running but not scheduled
            content_ids_to_stop = running_content_ids - scheduled_content_ids
            for content_id in content_ids_to_stop:
                print(f"Stopping: {content_id}")
                for process in running_processes.pop(content_id):
                    process.stop()

            # Start any content that is scheduled but not running
            content_ids_to_start = scheduled_content_ids - running_content_ids
            for content_id in content_ids_to_start:
                print(f"Starting: {content_id}")
                content = contents_by_id[content_id]
                running_processes[content_id] = []
                for i, cmd_line in enumerate(content["cmd_lines"]):
                    process = Process(f"{content_id}_{i}", shlex.split(cmd_line))
                    process.start()
                    running_processes[content_id].append(process)

        time.sleep(LOOP_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
