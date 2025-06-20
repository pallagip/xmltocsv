"""
Script: make_June4ReadyInsCarb.py

Description:
    Reads “outputJune4.csv” in the current folder, filters rows to two date ranges:
      1) 2024-02-12 12:00:00+01:00 through 2024-02-22 04:00:00+01:00
      2) 2025-05-21 12:00:00+02:00 through 2025-06-04 17:00:00+02:00

    From those rows, extracts:
      - Heart rate (HKQuantityTypeIdentifierHeartRate)
      - Blood glucose (HKQuantityTypeIdentifierBloodGlucose)
      - Bolus insulin dose (HKQuantityTypeIdentifierInsulinDelivery, metadata indicator == “2”)
      - Dietary carbohydrates (HKQuantityTypeIdentifierDietaryCarbohydrates)

    Outputs a CSV named “June4ReadyInsCarb.csv” with header:
        creationDate,heart_rate,blood_glucose,insulin_dose,dietary_carbohydrates

Usage:
    Place this script in the same folder as “outputJune4.csv” and run:
        python3 make_June4ReadyInsCarb.py
"""

import csv
import datetime
import sys

def parse_date(date_string):
    """Parse date strings in various formats (ISO-like with or without space before timezone)."""
    original = date_string

    # Handle explicit “YYYY-MM-DD HH:MM:SS ±ZZZZ” (space before tz)
    if ' +' in date_string or ' -' in date_string:
        try:
            # Split date/time vs. offset
            if ' +' in date_string:
                main, tz_part = date_string.split(' +', 1)
                tz_sign = '+'
            else:
                main, tz_part = date_string.split(' -', 1)
                tz_sign = '-'

            # main: "YYYY-MM-DD HH:MM:SS"
            date_part, time_part = main.split(' ')
            year, month, day = map(int, date_part.split('-'))
            hour, minute, second = map(int, time_part.split(':'))

            # tz_part: e.g. “0200” or “0130”
            if len(tz_part) >= 4:
                tz_hour = int(tz_part[:2])
                tz_min = int(tz_part[2:4])
                offset_minutes = tz_hour * 60 + tz_min
                if tz_sign == '-':
                    offset_minutes = -offset_minutes
                tzinfo = datetime.timezone(datetime.timedelta(minutes=offset_minutes))
                return datetime.datetime(year, month, day, hour, minute, second, tzinfo=tzinfo)
        except Exception:
            pass

    # Try native fromisoformat (handles “YYYY-MM-DDTHH:MM:SS±HH:MM”)
    try:
        return datetime.datetime.fromisoformat(date_string)
    except ValueError:
        pass

    # Handle “YYYY-MM-DDTHH:MM:SS±ZZZZ” (no colon in offset)
    if 'T' in date_string and ('+' in date_string or (date_string.count('-') > 2)):
        try:
            # Split at T
            date_part, rest = date_string.split('T', 1)
            # Look for “+” or “-” in rest to find offset
            if '+' in rest:
                time_part, tz_part = rest.split('+', 1)
                if len(tz_part) == 4:
                    tz_formatted = f"+{tz_part[:2]}:{tz_part[2:]}"
                    iso = f"{date_part}T{time_part}{tz_formatted}"
                    return datetime.datetime.fromisoformat(iso)
            elif '-' in rest:
                # rsplit in case date “-” appears more than once
                time_base, tz_part = rest.rsplit('-', 1)
                if len(tz_part) == 4:
                    iso = f"{date_part}T{time_base}-{tz_part[:2]}:{tz_part[2:]}"
                    return datetime.datetime.fromisoformat(iso)
        except Exception:
            pass

    # Fallback: replace T with space and try again
    if 'T' in date_string:
        fallback = date_string.replace('T', ' ')
        try:
            return datetime.datetime.fromisoformat(fallback)
        except ValueError:
            pass

    # If everything fails:
    raise ValueError(f"Cannot parse date: {original}")


def is_in_date_range(dt: datetime.datetime) -> bool:
    """
    Return True if dt falls within one of the four target ranges:
      1) 2024-02-12 12:00:00+01:00 → 2024-02-22 04:00:00+01:00
      2) 2025-05-21 12:00:00+02:00 → 2025-06-04 17:00:00+02:00
      3) 2025-06-04 23:00:00+02:00 → 2025-06-11 21:00:00+02:00
      4) 2025-06-11 23:00:00+02:00 → 2025-06-18 22:00:00+02:00
    """
    # Range 1: CET is +01:00 in February
    range1_start = datetime.datetime.fromisoformat("2024-02-12T12:00:00+01:00")
    range1_end   = datetime.datetime.fromisoformat("2024-02-22T04:00:00+01:00")
    # Range 2: CEST is +02:00 in May/June
    range2_start = datetime.datetime.fromisoformat("2025-05-21T12:00:00+02:00")
    range2_end   = datetime.datetime.fromisoformat("2025-06-04T17:00:00+02:00")
    # Range 3: CEST is +02:00 in June
    range3_start = datetime.datetime.fromisoformat("2025-06-04T23:00:00+02:00")
    range3_end   = datetime.datetime.fromisoformat("2025-06-11T21:00:00+02:00")
    # Range 4: CEST is +02:00 in June
    range4_start = datetime.datetime.fromisoformat("2025-06-11T23:00:00+02:00")
    range4_end   = datetime.datetime.fromisoformat("2025-06-18T22:00:00+02:00")

    return (
        (range1_start <= dt <= range1_end) or 
        (range2_start <= dt <= range2_end) or 
        (range3_start <= dt <= range3_end) or
        (range4_start <= dt <= range4_end)
    )


def main():
    # Determine input file based on current date
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=2)))
    if now.year == 2025 and now.month == 6 and now.day == 18:
        input_file = "/Volumes/Lacie2/Health Data/June20/apple_health_export/20250618_output.csv"
    else:
        input_file = "20250618_output.csv"
    output_file = "June18ReadyInsCarb.csv"

    try:
        fin = open(input_file, newline='', encoding='utf-8')
    except FileNotFoundError:
        print(f"Error: Cannot find '{input_file}' in the current directory.", file=sys.stderr)
        sys.exit(1)

    reader = csv.reader(fin)
    header = next(reader)

    # Find indices of the key columns
    try:
        type_idx = header.index("type")
        value_idx = header.index("value")
        date_idx = header.index("creationDate")
    except ValueError as e:
        print(f"Error: Expected column not found in header: {e}", file=sys.stderr)
        fin.close()
        sys.exit(1)

    # First pass: detect which column holds the insulin-type indicator (“1” vs. “2”)
    insulin_positions = {}  # count occurrences of “1” or “2” per column index

    # We’ll scan up to first 500 insulin rows to figure out which column stores the metadata indicator
    scanned_insulin = 0
    fin.seek(0)
    next(reader)  # skip header again

    for row in reader:
        if scanned_insulin >= 500:
            break
        if len(row) <= max(type_idx, value_idx, date_idx):
            continue

        if row[type_idx] == "HKQuantityTypeIdentifierInsulinDelivery":
            scanned_insulin += 1
            # Look for any cell in this row that is exactly “1” or “2”
            for pos, cell in enumerate(row):
                if cell in ("1", "2"):
                    insulin_positions[pos] = insulin_positions.get(pos, 0) + 1

    fin.seek(0)
    next(reader)

    if not insulin_positions:
        print("Warning: No insulin metadata indicators found in first 500 insulin rows.", file=sys.stderr)
        # We’ll still proceed but insulin_dose will remain blank.
        insulin_type_idx = None
    else:
        # Choose the column index that appeared most frequently with “1” or “2”
        insulin_type_idx = max(insulin_positions, key=lambda k: insulin_positions[k])
        print(f"Detected insulin-type indicator at column index {insulin_type_idx} (most frequent).")

    # Prepare data container: creationDate → dict of fields
    data_by_time = {}

    # Counters for summary
    total_rows = 0
    parsing_errors = 0
    insulin_examined = 0
    bolus_found = 0

    # Second pass: actually extract filtered data
    fin.seek(0)
    next(reader)

    for row in reader:
        total_rows += 1
        if len(row) <= max(type_idx, value_idx, date_idx):
            continue

        data_type = row[type_idx]

        # Parse date (with error handling)
        try:
            dt = parse_date(row[date_idx])
        except ValueError:
            parsing_errors += 1
            continue

        # Filter by our two date ranges
        if not is_in_date_range(dt):
            continue

        # Normalize timestamp to “YYYY-MM-DD HH:MM:SS±HHMM” without colon in offset
        date_str = dt.strftime("%Y-%m-%d %H:%M:%S%z")

        # Ensure we have an entry dict for this timestamp
        if date_str not in data_by_time:
            data_by_time[date_str] = {
                "heart_rate": "",
                "blood_glucose": "",
                "insulin_dose": "",
                "dietary_carbohydrates": "",
            }

        # Extract the correct field
        if data_type == "HKQuantityTypeIdentifierHeartRate":
            data_by_time[date_str]["heart_rate"] = row[value_idx]

        elif data_type == "HKQuantityTypeIdentifierBloodGlucose":
            data_by_time[date_str]["blood_glucose"] = row[value_idx]

        elif data_type == "HKQuantityTypeIdentifierDietaryCarbohydrates":
            data_by_time[date_str]["dietary_carbohydrates"] = row[value_idx]

        elif data_type == "HKQuantityTypeIdentifierInsulinDelivery":
            insulin_examined += 1

            # If we never detected a metadata column for insulin, skip
            if insulin_type_idx is None or insulin_type_idx >= len(row):
                continue

            # Only keep bolus insulin (indicator == "2")
            if row[insulin_type_idx] == "2":
                bolus_found += 1
                data_by_time[date_str]["insulin_dose"] = row[value_idx]
            # Otherwise, skip (indicator == "1" is not bolus)

    fin.close()

    # Write out to the output CSV
    with open(output_file, "w", newline="", encoding="utf-8") as fout:
        fieldnames = [
            "creationDate",
            "heart_rate",
            "blood_glucose",
            "insulin_dose",
            "dietary_carbohydrates",
        ]
        writer = csv.DictWriter(fout, fieldnames=fieldnames)
        writer.writeheader()

        # Sort timestamps lexicographically (equivalent to chronological order for "%Y-%m-%d %H:%M:%S%z")
        for creationDate in sorted(data_by_time.keys()):
            out_row = {"creationDate": creationDate}
            out_row.update(data_by_time[creationDate])
            writer.writerow(out_row)

    # Print summary
    print("Processing complete.")
    print(f"- Total rows read:             {total_rows}")
    print(f"- Date parsing errors:         {parsing_errors}")
    print(f"- Insulin entries examined:    {insulin_examined}")
    print(f"- Bolus insulin entries kept:  {bolus_found}")
    print(f"- Total output timestamps:     {len(data_by_time)}")
    print(f"Output written to '{output_file}'.")
    

if __name__ == "__main__":
    main()