"""Some utilities to split data according to time or location."""


def normalize_date(date):
    """Returns a normalized string representation of a date string."""
    original_argument = date
    date = date.replace(".", "-")
    date = date.replace("/", "-")
    parts = date.split("-")
    for part in parts:
        if len(part) not in [1, 2, 4]:
            raise TypeError("I can't make sense of this date format: "
                            "'" + original_argument + "'")
    if len(parts[0]) <= 2 and len(parts[1]) <= 2 and len(parts[2]) <= 2:
        raise TypeError("This date format is ambiguous: "
                        "'" + original_argument + "'. "
                        "Please make sure to use 4 digits for the year.")
    # Reverse DD-MM-YYYY into YYYY-MM-DD so that alphabetical order is the
    # same as chronological.
    if len(parts[0]) != 4:
        parts.reverse()
    # Zero-pad the month and day.
    parts[1] = parts[1].zfill(2)
    parts[2] = parts[2].zfill(2)
    return "-".join(parts)


def daily_slice(new_cases, total_cases):
    # full starts from new cases by location/date
    # structure for daily slice YYYY-MM-DD.json
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

    return {"date": new_cases.name, "features": features}


def chunks(new_cases, total_cases, quiet=False):
    """
    Yields successive equal-sized chunks from the input list.
    """
    for i in range(len(new_cases)):
        if not quiet:
            print(".", end="", flush=True)
        yield (new_cases.iloc[i], total_cases.iloc[i])
