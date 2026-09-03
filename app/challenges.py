import hmac
from contextlib import closing
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP

from app.database import get_connection


PUBLIC_COLUMNS = (
    "id",
    "title",
    "description",
    "difficulty",
    "category",
    "points",
    "active",
)
HINT_COLUMNS = ("hint_1", "hint_2", "hint_3")
HINT_POINT_MULTIPLIERS = {
    0: Decimal("1.00"),
    1: Decimal("0.90"),
    2: Decimal("0.75"),
    3: Decimal("0.50"),
}
RAPID_SUBMISSION_WINDOW = timedelta(seconds=5)


def _selected_columns(include_hints: bool) -> str:
    columns = PUBLIC_COLUMNS + (HINT_COLUMNS if include_hints else ())
    # Deliberately omit flag: metadata reads must never expose challenge answers.
    return ", ".join(columns)


def list_challenges(
    *, include_hints: bool = False, include_inactive: bool = False
) -> list[dict]:
    """List challenge metadata, optionally including hints for trusted callers."""
    query = f"SELECT {_selected_columns(include_hints)} FROM challenges"
    parameters = ()
    if not include_inactive:
        query += " WHERE active = ?"
        parameters = (1,)
    query += " ORDER BY id"

    with closing(get_connection()) as connection:
        rows = connection.execute(query, parameters).fetchall()
    return [dict(row) for row in rows]


def get_challenge(
    challenge_id: int,
    *,
    include_hints: bool = False,
    include_inactive: bool = False,
) -> dict | None:
    """Get one challenge's metadata without ever selecting its flag."""
    query = f"SELECT {_selected_columns(include_hints)} FROM challenges WHERE id = ?"
    parameters: list[int] = [challenge_id]
    if not include_inactive:
        query += " AND active = ?"
        parameters.append(1)

    with closing(get_connection()) as connection:
        row = connection.execute(query, parameters).fetchone()
    return dict(row) if row is not None else None


def list_user_completions(user_id: int) -> list[dict]:
    """List challenge completion records belonging to one user."""
    with closing(get_connection()) as connection:
        rows = connection.execute(
            """
            SELECT challenge_id, completed_at, points_awarded, hints_used, attempts
            FROM challenge_completions
            WHERE user_id = ?
            ORDER BY completed_at, challenge_id
            """,
            (user_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_user_challenge_summary(user_id: int) -> dict:
    """Return active-challenge progress and the user's total awarded score."""
    with closing(get_connection()) as connection:
        row = connection.execute(
            """
            SELECT
                (
                    SELECT COUNT(*)
                    FROM challenges
                    WHERE active = 1
                ) AS total,
                (
                    SELECT COUNT(*)
                    FROM challenge_completions
                    JOIN challenges
                        ON challenges.id = challenge_completions.challenge_id
                    WHERE challenge_completions.user_id = ?
                        AND challenges.active = 1
                ) AS completed,
                (
                    SELECT COALESCE(SUM(points_awarded), 0)
                    FROM challenge_completions
                    WHERE user_id = ?
                ) AS score
            """,
            (user_id, user_id),
        ).fetchone()
    return {
        "completed": row["completed"],
        "total": row["total"],
        "score": row["score"],
    }


def list_scoreboard() -> list[dict]:
    """Rank student usernames by their total awarded points."""
    with closing(get_connection()) as connection:
        rows = connection.execute(
            """
            SELECT
                users.username,
                COALESCE(SUM(challenge_completions.points_awarded), 0) AS score
            FROM users
            LEFT JOIN challenge_completions
                ON challenge_completions.user_id = users.id
            WHERE users.role = 'student'
            GROUP BY users.id, users.username
            ORDER BY score DESC, users.username COLLATE NOCASE, users.id
            """
        ).fetchall()

    scoreboard = []
    previous_score = None
    current_rank = 0
    for position, row in enumerate(rows, start=1):
        score = int(row["score"])
        if score != previous_score:
            current_rank = position
            previous_score = score
        scoreboard.append(
            {
                "rank": current_rank,
                "username": row["username"],
                "score": score,
            }
        )
    return scoreboard


def get_challenge_progress(user_id: int, challenge_id: int) -> dict:
    """Return one user's non-secret attempt and hint state."""
    with closing(get_connection()) as connection:
        row = connection.execute(
            """
            SELECT attempts, highest_hint, last_attempt_at
            FROM challenge_progress
            WHERE user_id = ? AND challenge_id = ?
            """,
            (user_id, challenge_id),
        ).fetchone()

    if row is None:
        return {"attempts": 0, "highest_hint": 0, "last_attempt_at": None}
    return dict(row)


def reveal_hint(
    user_id: int,
    challenge_id: int,
    hint_number: int,
) -> dict | None:
    """Reveal one sequential hint and persist the highest level used."""
    if hint_number not in range(1, 4):
        return None

    hint_column = HINT_COLUMNS[hint_number - 1]
    with closing(get_connection()) as connection:
        with connection:
            connection.execute("BEGIN IMMEDIATE")
            challenge = connection.execute(
                f"""
                SELECT {hint_column} AS hint
                FROM challenges
                WHERE id = ? AND active = 1
                """,
                (challenge_id,),
            ).fetchone()
            if challenge is None or not challenge["hint"]:
                return None

            progress = connection.execute(
                """
                SELECT highest_hint
                FROM challenge_progress
                WHERE user_id = ? AND challenge_id = ?
                """,
                (user_id, challenge_id),
            ).fetchone()
            current_hint = (
                progress["highest_hint"] if progress is not None else 0
            )

            if hint_number > current_hint + 1:
                return {
                    "hint": None,
                    "hint_number": hint_number,
                    "highest_hint": current_hint,
                    "locked": True,
                    "newly_revealed": False,
                }

            newly_revealed = hint_number > current_hint
            highest_hint = max(current_hint, hint_number)
            connection.execute(
                """
                INSERT INTO challenge_progress (user_id, challenge_id, highest_hint)
                VALUES (?, ?, ?)
                ON CONFLICT (user_id, challenge_id) DO UPDATE
                SET highest_hint = MAX(highest_hint, excluded.highest_hint)
                """,
                (user_id, challenge_id, highest_hint),
            )
    return {
        "hint": challenge["hint"],
        "hint_number": hint_number,
        "highest_hint": highest_hint,
        "locked": False,
        "newly_revealed": newly_revealed,
    }


def calculate_points(base_points: int, highest_hint: int) -> int:
    """Apply the configured hint penalty and round half-points upward."""
    multiplier = HINT_POINT_MULTIPLIERS.get(highest_hint)
    if multiplier is None:
        raise ValueError("highest_hint must be between 0 and 3")
    return int(
        (Decimal(base_points) * multiplier).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )
    )


def _timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")


def _was_rapid_submission(last_attempt_at: str | None, now: datetime) -> bool:
    if last_attempt_at is None:
        return False
    previous = datetime.fromisoformat(last_attempt_at)
    if previous.tzinfo is None:
        previous = previous.replace(tzinfo=timezone.utc)
    elapsed = now - previous.astimezone(timezone.utc)
    return timedelta(0) <= elapsed <= RAPID_SUBMISSION_WINDOW


def submit_flag(user_id: int, challenge_id: int, submitted_flag: str) -> dict | None:
    """Validate and atomically record one submission without returning the flag."""
    now = datetime.now(timezone.utc)

    with closing(get_connection()) as connection:
        with connection:
            connection.execute("BEGIN IMMEDIATE")

            # This is the only engine query that selects flag, exclusively for
            # server-side comparison. The returned result never includes it.
            challenge = connection.execute(
                """
                SELECT id, points, flag
                FROM challenges
                WHERE id = ? AND active = 1
                """,
                (challenge_id,),
            ).fetchone()
            if challenge is None:
                return None

            completion = connection.execute(
                """
                SELECT points_awarded, hints_used, attempts
                FROM challenge_completions
                WHERE user_id = ? AND challenge_id = ?
                """,
                (user_id, challenge_id),
            ).fetchone()

            progress = connection.execute(
                """
                SELECT attempts, highest_hint, last_attempt_at
                FROM challenge_progress
                WHERE user_id = ? AND challenge_id = ?
                """,
                (user_id, challenge_id),
            ).fetchone()
            previous_attempts = progress["attempts"] if progress is not None else 0
            highest_hint = progress["highest_hint"] if progress is not None else 0
            last_attempt_at = (
                progress["last_attempt_at"] if progress is not None else None
            )
            attempts = previous_attempts + 1
            rapid = _was_rapid_submission(last_attempt_at, now)

            connection.execute(
                """
                INSERT INTO challenge_progress (
                    user_id, challenge_id, attempts, highest_hint, last_attempt_at
                )
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT (user_id, challenge_id) DO UPDATE SET
                    attempts = excluded.attempts,
                    highest_hint = MAX(highest_hint, excluded.highest_hint),
                    last_attempt_at = excluded.last_attempt_at
                """,
                (user_id, challenge_id, attempts, highest_hint, _timestamp(now)),
            )

            correct = hmac.compare_digest(
                challenge["flag"].encode("utf-8"),
                submitted_flag.strip().encode("utf-8"),
            )
            if not correct:
                return {
                    "correct": False,
                    "already_completed": False,
                    "attempts": attempts,
                    "rapid": rapid,
                }

            if completion is not None:
                return {
                    "correct": True,
                    "already_completed": True,
                    "points_awarded": completion["points_awarded"],
                    "hints_used": completion["hints_used"],
                    "attempts": attempts,
                    "rapid": rapid,
                }

            points_awarded = calculate_points(challenge["points"], highest_hint)
            connection.execute(
                """
                INSERT INTO challenge_completions (
                    user_id,
                    challenge_id,
                    completed_at,
                    points_awarded,
                    hints_used,
                    attempts
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    challenge_id,
                    _timestamp(now),
                    points_awarded,
                    highest_hint,
                    attempts,
                ),
            )
            return {
                "correct": True,
                "already_completed": False,
                "points_awarded": points_awarded,
                "hints_used": highest_hint,
                "attempts": attempts,
                "rapid": rapid,
            }
