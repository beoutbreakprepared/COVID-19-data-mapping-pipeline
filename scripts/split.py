"""Some utilities to split data according to time or location."""


def normalize_date(date):
    """Returns a normalized string representation of a date string."""
    date = date.replace(".", "-")
    date = date.replace("/", "-")
    if len(date) == len("D-MM-YYYY"):
        # Single day digit
        date = date.zfill(len("DD-MM-YYYY"))
    date_parts = date.split("-")
    # Reverse DD-MM-YYYY into YYYY-MM-DD so that alphabetical order is the
    # same as chronological.
    if len(date_parts[0]) != 4:
        date_parts.reverse()
    print(date + " -> " + "-".join(date_parts))
    return "-".join(date_parts)


def daily_slice(new_cases, total_cases):
    # full starts from new cases by location/date
    # structure for daily slice YYYY.MM.DD.json
    # {"date": "YYYY-MM-DD", "features": [{"properties": {"geoid": "lat|long",
    # "new": int, "total": int}}, ... ]

    assert new_cases.name == total_cases.name, "mismatched dates"

    features = []

    for geoid in new_cases.index:
        new = int(new_cases[geoid])
        total = int(total_cases[geoid])
        if new == total == 0:
            continue
        properties = {"geoid": geoid, "total": total}
        if new != 0:
            properties["new"] = new

        features.append({"properties": properties})

    return {"date": new_cases.name.replace(".", "-"), "features": features}


def chunks(new_cases, total_cases):
    """
    Yields successive equal-sized chunks from the input list.
    """
    for i in range(len(new_cases)):
        print(".", end="", flush=True)
        yield (new_cases.iloc[i], total_cases.iloc[i])
