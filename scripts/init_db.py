import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.database import initialize_db_if_needed, recreate_db  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize the BurpLab database.")
    parser.add_argument(
        "--if-needed",
        action="store_true",
        help="initialize only when the users table is missing",
    )
    args = parser.parse_args()

    if args.if_needed:
        if initialize_db_if_needed():
            print("Initialized and seeded database because the users table was missing.")
        else:
            print("Database already contains the users table; preserving existing data.")
        return

    database_path = recreate_db()
    print(f"Reinitialized and seeded database: {database_path}")


if __name__ == "__main__":
    main()
