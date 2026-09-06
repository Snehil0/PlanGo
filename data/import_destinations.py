import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app import app, import_destination_csv  


def import_destinations():
    with app.app_context():
        return import_destination_csv()


def main():
    summary = import_destinations()
    print(f"Rows read: {summary['rows_read']}")
    print(f"Duplicate rows skipped: {summary['duplicate_rows_skipped']}")
    print(f"New states created: {summary['new_states_created']}")
    print(f"New destinations created: {summary['new_destinations_created']}")
    print(f"Existing destinations skipped: {summary['existing_destinations_skipped']}")
    print(f"Total destinations: {summary['total_destinations']}")


if __name__ == "__main__":
    main()
