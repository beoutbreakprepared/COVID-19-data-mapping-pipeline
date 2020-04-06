import json
import os
import sys

TOPLEVEL_KEY = "data"

def normalize_date(date):
  # Sometimes we get a date range instead of a single date.
  # Let's get the end of the range.
  if "-" in date:
    date = date.split("-")[1]
  if len(date) == len("D.MM.YYYY"):
    # Single day digit
    date = date.zfill(len("DD.MM.YYYY"))
  # Reverse DD.MM.YYYY into YYYY.MM.DD so that alphabetical order is the
  # same as chronological.
  date_parts = date.split(".")
  date_parts.reverse()
  return ".".join(date_parts)

def split_by_day(data, out_dir):
  # A dictionary from each date to a list of corresponding features
  daily_splits = {}
  if TOPLEVEL_KEY in data:
    for feature in data[TOPLEVEL_KEY]:
      if "date_confirmation" in feature:
        date = normalize_date(feature["date_confirmation"])
        if date in daily_splits:
          daily_splits[date].append(feature)
        else:
          daily_splits[date] = [feature]
  else:
    print("I was expecting to find a '" + TOPLEVEL_KEY + "' key in the data")

  for date in daily_splits:
    daily_slice_file_path = os.path.join(out_dir, date + ".json")
    if os.path.exists(daily_slice_file_path):
      print("I will not clobber '" + daily_slice_file_path + "', "
            "please delete it first")
      continue
    with open(os.path.join(out_dir, date + ".json"), "w") as f:
      f.write(json.dumps(daily_splits[date]))
      f.close()

def main():
  if len(sys.argv) < 2:
    print("I need the path of the file to parse as an argument")
    return
  in_file_path = sys.argv[1]
  with open(in_file_path) as f:
    split_by_day(json.loads(f.read()), ".")
    f.close()

if __name__ == '__main__':
    main()
