from contextlib import closing
from datetime import datetime, timezone
from threading import Lock

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from app.auth import get_user_for_session
from app.database import get_connection, recreate_db
from app.routes import _csrf_token, _require_valid_csrf


admin = Blueprint("admin", __name__, url_prefix="/admin")
RESET_LOCK = Lock()


@admin.before_request
def require_admin_role():
    """Hide and deny the entire admin surface unless role is exactly admin."""
    token = session.get("auth_token")
    if not isinstance(token, str):
        abort(404)

    user = get_user_for_session(token)
    if user is None:
        session.clear()
        abort(404)
    if user["role"] != "admin":
        abort(404)

    g.current_user = user


def _load_dashboard_data() -> tuple[list[dict], list[dict]]:
    with closing(get_connection()) as connection:
        student_rows = connection.execute(
            """
            SELECT
                users.id,
                users.username,
                users.display_name,
                users.created_at,
                (
                    SELECT COUNT(*)
                    FROM challenges
                    WHERE active = 1
                ) AS total_challenges,
                (
                    SELECT COUNT(*)
                    FROM challenge_completions
                    JOIN challenges
                        ON challenges.id = challenge_completions.challenge_id
                    WHERE challenge_completions.user_id = users.id
                      AND challenges.active = 1
                ) AS completed_challenges,
                (
                    SELECT COALESCE(SUM(challenge_progress.attempts), 0)
                    FROM challenge_progress
                    JOIN challenges
                        ON challenges.id = challenge_progress.challenge_id
                    WHERE challenge_progress.user_id = users.id
                      AND challenges.active = 1
                ) AS submissions,
                (
                    SELECT COALESCE(SUM(challenge_progress.highest_hint), 0)
                    FROM challenge_progress
                    JOIN challenges
                        ON challenges.id = challenge_progress.challenge_id
                    WHERE challenge_progress.user_id = users.id
                      AND challenges.active = 1
                ) AS hints_used,
                (
                    SELECT COALESCE(SUM(challenge_completions.points_awarded), 0)
                    FROM challenge_completions
                    JOIN challenges
                        ON challenges.id = challenge_completions.challenge_id
                    WHERE challenge_completions.user_id = users.id
                      AND challenges.active = 1
                ) AS score
            FROM users
            WHERE users.role = 'student'
            ORDER BY users.username COLLATE NOCASE, users.id
            """
        ).fetchall()

        progress_rows = connection.execute(
            """
            SELECT
                users.id AS user_id,
                users.username,
                challenges.id AS challenge_id,
                challenges.title AS challenge_title,
                COALESCE(challenge_progress.attempts, 0) AS attempts,
                COALESCE(challenge_progress.highest_hint, 0) AS hints_used,
                challenge_progress.last_attempt_at,
                challenge_completions.completed_at,
                COALESCE(challenge_completions.points_awarded, 0)
                    AS points_awarded
            FROM users
            CROSS JOIN challenges
            LEFT JOIN challenge_progress
                ON challenge_progress.user_id = users.id
               AND challenge_progress.challenge_id = challenges.id
            LEFT JOIN challenge_completions
                ON challenge_completions.user_id = users.id
               AND challenge_completions.challenge_id = challenges.id
            WHERE users.role = 'student'
              AND challenges.active = 1
            ORDER BY
                users.username COLLATE NOCASE,
                users.id,
                challenges.id
            """
        ).fetchall()

    students = [dict(row) for row in student_rows]
    students_by_id = {student["id"]: student for student in students}
    for student in students:
        student["progress"] = []

    submissions = []
    for row in progress_rows:
        progress = dict(row)
        progress["status"] = (
            "Completed"
            if progress["completed_at"]
            else "Attempted"
            if progress["attempts"]
            else "Not started"
        )
        students_by_id[progress["user_id"]]["progress"].append(progress)
        if progress["attempts"]:
            submissions.append(progress)

    submissions.sort(
        key=lambda row: row["last_attempt_at"] or "",
        reverse=True,
    )
    return students, submissions


@admin.get("")
@admin.get("/")
def dashboard():
    students, submissions = _load_dashboard_data()
    return render_template(
        "admin/dashboard.html",
        students=students,
        submissions=submissions,
        csrf_token=_csrf_token(),
    )


@admin.route("/reset", methods=["GET", "POST"])
def reset():
    if request.method == "GET":
        return render_template(
            "admin/reset.html",
            csrf_token=_csrf_token(),
        )

    _require_valid_csrf()
    if request.form.get("confirmation", "") != "RESET":
        return (
            render_template(
                "admin/reset.html",
                error="Type RESET exactly to confirm the reset.",
                csrf_token=_csrf_token(),
            ),
            400,
        )

    actor_user_id = g.current_user["id"]
    occurred_at = datetime.now(timezone.utc).isoformat()
    with RESET_LOCK:
        recreate_db()

    current_app.logger.info(
        "event=admin_reset actor_user_id=%s occurred_at=%s",
        actor_user_id,
        occurred_at,
    )
    session.clear()
    flash("Lab data was reset to its original fictional seed state.", "success")
    return redirect(url_for("main.login"))
