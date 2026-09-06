import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app import app, db, User  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="Make an existing PlanGo user an administrator.")
    parser.add_argument("email", help="Email address of an existing user")
    args = parser.parse_args()

    with app.app_context():
        user = User.query.filter_by(email=args.email.strip().lower()).first()
        if user is None:
            parser.error("No user exists with that email address. Register the user first.")

        user.is_admin = True
        db.session.commit()
        print(f"Administrator access granted to {user.email}.")


if __name__ == "__main__":
    main()
