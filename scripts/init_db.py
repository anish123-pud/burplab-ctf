import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.database import recreate_db  # noqa: E402


def main() -> None:
    database_path = recreate_db()
    print(f"Initialized and seeded database: {database_path}")


if __name__ == "__main__":
    main()
