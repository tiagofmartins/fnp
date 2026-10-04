#!/usr/bin/env python3
"""Fetches worksheets of a Google Sheets spreadsheet, re-reading them only
when the spreadsheet has actually changed since the last fetch.
"""

import time
from datetime import datetime, timezone
from pathlib import Path

import gspread

SERVICE_ACCOUNT_FILE = Path(__file__).parent / "secrets" / "google_service_account.json"
SPREADSHEET_KEY_FILE = Path(__file__).parent / "secrets" / "gspread_key.txt"
CHECK_INTERVAL_SECONDS = 30
DEBOUNCE_SECONDS = 30


class GSheetReader:
    def __init__(self, worksheet_names,
                 service_account_file, spreadsheet_key_file,
                 check_interval_secs, debounce_secs):
        self._worksheet_names = worksheet_names
        self._service_account_file = service_account_file
        self._spreadsheet_key_file = spreadsheet_key_file
        self._check_interval_secs = check_interval_secs
        self._debounce_secs = debounce_secs
        self._spreadsheet = None
        self._last_modified_time = None
        self._last_checked_time = None
        self._data = {}

    def _get_spreadsheet(self):
        """Return the gspread Spreadsheet object, creating it if necessary."""
        if self._spreadsheet is None:
            client = gspread.service_account(filename=self._service_account_file)
            spreadsheet_key = self._spreadsheet_key_file.read_text().strip()
            self._spreadsheet = client.open_by_key(spreadsheet_key)
        return self._spreadsheet
    
    def _fetch_data(self):
        """Update self._data from the specified worksheets, but only if the
        spreadsheet has changed since the last fetch. Debounce the fetch to
        avoid reading a worksheet while an edit is still in progress. Checks
        for changes at most once every check_interval_secs, regardless of
        how often this is called."""
        # Check if enough time has passed since the last check
        now = time.time()
        if self._last_checked_time is not None and now - self._last_checked_time < self._check_interval_secs:
            return
        self._last_checked_time = now
        # Check if the spreadsheet has been modified since the last fetch
        modified_time_iso = self._get_spreadsheet().get_lastUpdateTime()
        modified_time = datetime.fromisoformat(modified_time_iso.replace("Z", "+00:00"))
        if modified_time == self._last_modified_time:
            return
        # Check if enough time has passed since the last edit to avoid reading a worksheet while being edited
        seconds_since_edit = (datetime.now(timezone.utc) - modified_time).total_seconds()
        if seconds_since_edit < self._debounce_secs:
            return
        # Fetch the data from the worksheets, or from all of them if none were specified
        worksheet_names = self._worksheet_names or [ws.title for ws in self._get_spreadsheet().worksheets()]
        self._data = {name: self._get_spreadsheet().worksheet(name).get_all_values() for name in worksheet_names}
        self._last_modified_time = modified_time
    
    def get_data(self, only_if_modified=False):
        """Return the data from the specified worksheets, refetching first if
        needed. If only_if_modified is True, return None instead whenever
        that refetch did not actually update the data."""
        previous_modified_time = self._last_modified_time
        self._fetch_data()
        if only_if_modified and self._last_modified_time == previous_modified_time:
            return None
        return self._data


if __name__ == "__main__":
    reader = GSheetReader(["Contents"],
                          SERVICE_ACCOUNT_FILE,
                          SPREADSHEET_KEY_FILE,
                          check_interval_secs=CHECK_INTERVAL_SECONDS,
                          debounce_secs=DEBOUNCE_SECONDS)
    while True:
        data = reader.get_data(only_if_modified=True)
        if data is not None:
            print(data)
        time.sleep(1)
