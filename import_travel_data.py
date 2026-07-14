"""Import PlanGo travel knowledge-base data from CSV files.

Run from the project folder:
    python import_travel_data.py data/rajasthan_starter

Use --dry-run to validate files without saving data:
    python import_travel_data.py data/rajasthan_starter --dry-run
"""

import argparse
import csv
from datetime import datetime
from pathlib import Path

from app import app, db, State, City, Attraction, Hotel, Restaurant


FILES = {
    "states.csv": ("state_name", "code", "description"),
    "cities.csv": ("city_name", "state_name", "country", "description"),
    "attractions.csv": (
        "city_name", "state_name", "name", "category", "description", "latitude",
        "longitude", "opening_time", "closing_time", "average_visit_duration",
        "entry_fee", "rating", "image_url",
    ),
    "hotels.csv": (
        "city_name", "state_name", "hotel_name", "description", "address", "latitude",
        "longitude", "price_range", "rating", "contact_number", "website", "amenities",
        "image_url",
    ),
    "restaurants.csv": (
        "city_name", "state_name", "restaurant_name", "description", "cuisine", "address",
        "latitude", "longitude", "average_cost_for_two", "opening_time", "closing_time",
        "vegetarian_available", "rating", "contact_number", "website", "image_url",
    ),
}


def required(row, field):
    value = (row.get(field) or "").strip()
    if not value:
        raise ValueError(f"{field} is required")
    return value


def optional_float(row, field, minimum=None, maximum=None):
    value = (row.get(field) or "").strip()
    if not value:
        return None
    number = float(value)
    if minimum is not None and number < minimum:
        raise ValueError(f"{field} must be at least {minimum}")
    if maximum is not None and number > maximum:
        raise ValueError(f"{field} must be at most {maximum}")
    return number


def optional_integer(row, field, minimum=None):
    value = (row.get(field) or "").strip()
    if not value:
        return None
    number = int(value)
    if minimum is not None and number < minimum:
        raise ValueError(f"{field} must be at least {minimum}")
    return number


def optional_time(row, field):
    value = (row.get(field) or "").strip()
    if not value:
        return None
    try:
        return datetime.strptime(value, "%H:%M").time()
    except ValueError as error:
        raise ValueError(f"{field} must use HH:MM (24-hour) format") from error


def optional_boolean(row, field):
    value = (row.get(field) or "").strip().lower()
    if not value:
        return False
    if value in {"true", "yes", "1"}:
        return True
    if value in {"false", "no", "0"}:
        return False
    raise ValueError(f"{field} must be true or false")


def read_rows(folder, filename):
    path = folder / filename
    if not path.exists():
        return []

    with path.open(encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        missing = set(FILES[filename]) - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{filename} is missing columns: {', '.join(sorted(missing))}")
        return list(reader)


def find_city(row):
    state_name = required(row, "state_name")
    city_name = required(row, "city_name")
    state = State.query.filter(db.func.lower(State.name) == state_name.lower()).first()
    if not state:
        raise ValueError(f"state '{state_name}' does not exist")
    city = City.query.filter(
        City.state_id == state.id,
        db.func.lower(City.name) == city_name.lower(),
    ).first()
    if not city:
        raise ValueError(f"city '{city_name}' does not exist in {state.name}")
    return city


def import_states(rows, report):
    for line, row in enumerate(rows, start=2):
        try:
            name = required(row, "state_name")
            if State.query.filter(db.func.lower(State.name) == name.lower()).first():
                report["skipped"] += 1
                continue
            db.session.add(State(
                name=name,
                code=(row.get("code") or "").strip() or None,
                description=(row.get("description") or "").strip() or None,
            ))
            db.session.flush()
            report["imported"] += 1
        except (ValueError, TypeError) as error:
            report["errors"].append(f"states.csv line {line}: {error}")


def import_cities(rows, report):
    for line, row in enumerate(rows, start=2):
        try:
            state_name = required(row, "state_name")
            name = required(row, "city_name")
            state = State.query.filter(db.func.lower(State.name) == state_name.lower()).first()
            if not state:
                raise ValueError(f"state '{state_name}' does not exist")
            if City.query.filter(City.state_id == state.id, db.func.lower(City.name) == name.lower()).first():
                report["skipped"] += 1
                continue
            db.session.add(City(
                state_id=state.id, name=name,
                country=(row.get("country") or "India").strip(),
                description=(row.get("description") or "").strip() or None,
            ))
            db.session.flush()
            report["imported"] += 1
        except (ValueError, TypeError) as error:
            report["errors"].append(f"cities.csv line {line}: {error}")


def import_attractions(rows, report):
    for line, row in enumerate(rows, start=2):
        try:
            city = find_city(row)
            name = required(row, "name")
            if Attraction.query.filter(Attraction.city_id == city.id, db.func.lower(Attraction.name) == name.lower()).first():
                report["skipped"] += 1
                continue
            latitude = optional_float(row, "latitude", -90, 90)
            longitude = optional_float(row, "longitude", -180, 180)
            db.session.add(Attraction(
                city_id=city.id, name=name, category=required(row, "category"),
                description=(row.get("description") or "").strip() or None,
                latitude=latitude, longitude=longitude,
                opening_time=optional_time(row, "opening_time"),
                closing_time=optional_time(row, "closing_time"),
                average_visit_duration=optional_integer(row, "average_visit_duration", 1),
                entry_fee=optional_float(row, "entry_fee", 0) or 0.0,
                rating=optional_float(row, "rating", 0, 5),
                image_url=(row.get("image_url") or "").strip() or None,
            ))
            report["imported"] += 1
        except (ValueError, TypeError) as error:
            report["errors"].append(f"attractions.csv line {line}: {error}")


def import_hotels(rows, report):
    for line, row in enumerate(rows, start=2):
        try:
            city = find_city(row)
            name = required(row, "hotel_name")
            if Hotel.query.filter(Hotel.city_id == city.id, db.func.lower(Hotel.hotel_name) == name.lower()).first():
                report["skipped"] += 1
                continue
            db.session.add(Hotel(
                city_id=city.id, hotel_name=name,
                description=(row.get("description") or "").strip() or None,
                address=(row.get("address") or "").strip() or None,
                latitude=optional_float(row, "latitude", -90, 90),
                longitude=optional_float(row, "longitude", -180, 180),
                price_range=(row.get("price_range") or "").strip() or None,
                rating=optional_float(row, "rating", 0, 5),
                contact_number=(row.get("contact_number") or "").strip() or None,
                website=(row.get("website") or "").strip() or None,
                amenities=(row.get("amenities") or "").strip() or None,
                image_url=(row.get("image_url") or "").strip() or None,
            ))
            report["imported"] += 1
        except (ValueError, TypeError) as error:
            report["errors"].append(f"hotels.csv line {line}: {error}")


def import_restaurants(rows, report):
    for line, row in enumerate(rows, start=2):
        try:
            city = find_city(row)
            name = required(row, "restaurant_name")
            if Restaurant.query.filter(Restaurant.city_id == city.id, db.func.lower(Restaurant.restaurant_name) == name.lower()).first():
                report["skipped"] += 1
                continue
            db.session.add(Restaurant(
                city_id=city.id, restaurant_name=name,
                description=(row.get("description") or "").strip() or None,
                cuisine=(row.get("cuisine") or "").strip() or None,
                address=(row.get("address") or "").strip() or None,
                latitude=optional_float(row, "latitude", -90, 90),
                longitude=optional_float(row, "longitude", -180, 180),
                average_cost_for_two=optional_float(row, "average_cost_for_two", 0),
                opening_time=optional_time(row, "opening_time"),
                closing_time=optional_time(row, "closing_time"),
                vegetarian_available=optional_boolean(row, "vegetarian_available"),
                rating=optional_float(row, "rating", 0, 5),
                contact_number=(row.get("contact_number") or "").strip() or None,
                website=(row.get("website") or "").strip() or None,
                image_url=(row.get("image_url") or "").strip() or None,
            ))
            report["imported"] += 1
        except (ValueError, TypeError) as error:
            report["errors"].append(f"restaurants.csv line {line}: {error}")


IMPORTERS = {
    "states.csv": import_states,
    "cities.csv": import_cities,
    "attractions.csv": import_attractions,
    "hotels.csv": import_hotels,
    "restaurants.csv": import_restaurants,
}


def main():
    parser = argparse.ArgumentParser(description="Import PlanGo CSV travel data.")
    parser.add_argument("folder", type=Path, help="Folder containing the CSV files")
    parser.add_argument("--dry-run", action="store_true", help="Validate without saving changes")
    args = parser.parse_args()

    if not args.folder.is_dir():
        parser.error(f"Folder not found: {args.folder}")

    with app.app_context():
        db.create_all()
        report = {"imported": 0, "skipped": 0, "errors": []}
        try:
            for filename, importer in IMPORTERS.items():
                importer(read_rows(args.folder, filename), report)
            if args.dry_run or report["errors"]:
                db.session.rollback()
            else:
                db.session.commit()
        except Exception:
            db.session.rollback()
            raise

    print(f"Imported: {report['imported']}")
    print(f"Duplicates skipped: {report['skipped']}")
    for error in report["errors"]:
        print(f"Validation error: {error}")
    if report["errors"]:
        raise SystemExit(1)
    if args.dry_run:
        print("Dry run complete. No changes were saved.")


if __name__ == "__main__":
    main()
