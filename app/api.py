import sqlite3
from contextlib import closing

from flask import Blueprint, g, jsonify, request, session
from werkzeug.exceptions import HTTPException

from app.auth import EMAIL_PATTERN, USERNAME_PATTERN, get_user_for_session
from app.database import get_connection


api = Blueprint("api", __name__, url_prefix="/api")


def _error(message: str, status: int):
    return jsonify(error=message), status


def _lab_flag(challenge_id: int) -> str | None:
    with closing(get_connection()) as connection:
        row = connection.execute(
            "SELECT flag FROM challenges WHERE id = ? AND active = 1",
            (challenge_id,),
        ).fetchone()
    return row["flag"] if row is not None else None


@api.app_errorhandler(HTTPException)
def json_api_error(error: HTTPException):
    if request.path == "/api" or request.path.startswith("/api/"):
        return _error(error.description or error.name, error.code or 500)
    return error


def _profile_payload(user) -> dict:
    return {
        "id": user["id"],
        "username": user["username"],
        "display_name": user["display_name"],
        "email": user["email"],
        "role": user["role"],
        "created_at": user["created_at"],
    }


@api.before_request
def require_api_login():
    token = session.get("auth_token")
    if not isinstance(token, str):
        return _error("Authentication required.", 401)

    user = get_user_for_session(token)
    if user is None:
        session.clear()
        return _error("Authentication required.", 401)

    g.current_user = user
    return None


@api.get("/products")
def products():
    with closing(get_connection()) as connection:
        rows = connection.execute(
            """
            SELECT id, name, description, price, stock
            FROM products
            ORDER BY id
            """
        ).fetchall()

    return jsonify(
        products=[
            {
                "id": row["id"],
                "name": row["name"],
                "description": row["description"],
                "price": row["price"],
                "stock": row["stock"],
            }
            for row in rows
        ]
    )


@api.get("/products/<int:product_id>")
def product(product_id: int):
    with closing(get_connection()) as connection:
        row = connection.execute(
            """
            SELECT id, name, description, price, stock, created_at
            FROM products
            WHERE id = ?
            """,
            (product_id,),
        ).fetchone()

    if row is None:
        return _error("Product not found.", 404)

    return jsonify(
        product={
            "id": row["id"],
            "name": row["name"],
            "description": row["description"],
            "price": row["price"],
            "stock": row["stock"],
            "created_at": row["created_at"],
        }
    )


@api.get("/profile")
def profile():
    return jsonify(profile=_profile_payload(g.current_user))


@api.post("/profile")
def update_profile():
    if not request.is_json:
        return _error("Request body must be JSON.", 415)

    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return _error("Request body must be a JSON object.", 400)

    allowed_fields = {"username", "display_name", "email"}
    unexpected_fields = set(body) - allowed_fields
    if unexpected_fields:
        return _error("Request contains unsupported profile fields.", 400)

    submitted_username = body.get("username", g.current_user["username"])
    submitted_email = body.get("email", g.current_user["email"])
    submitted_display_name = body.get(
        "display_name", g.current_user["display_name"]
    )

    if not isinstance(submitted_username, str) or not isinstance(submitted_email, str):
        return _error("Profile fields must be strings.", 400)
    if not isinstance(submitted_display_name, str):
        return _error("Profile fields must be strings.", 400)

    username = submitted_username.strip().lower()
    email = submitted_email.strip().lower()
    display_name = submitted_display_name.strip()
    if not USERNAME_PATTERN.fullmatch(username):
        return _error(
            "Username must be 3–32 characters using lowercase letters, numbers, or underscores.",
            400,
        )
    if len(email) > 254 or not EMAIL_PATTERN.fullmatch(email):
        return _error("Enter a valid email address.", 400)
    if not 1 <= len(display_name) <= 80:
        return _error("Display name must be between 1 and 80 characters.", 400)

    try:
        with closing(get_connection()) as connection:
            with connection:
                connection.execute(
                    """
                    UPDATE users
                    SET username = ?, email = ?, display_name = ?
                    WHERE id = ?
                    """,
                    (username, email, display_name, g.current_user["id"]),
                )
                updated_user = connection.execute(
                    """
                    SELECT id, username, email, display_name, role, created_at
                    FROM users
                    WHERE id = ?
                    """,
                    (g.current_user["id"],),
                ).fetchone()
    except sqlite3.IntegrityError:
        return _error("That username or email is already registered.", 409)

    return jsonify(profile=_profile_payload(updated_user))


@api.post("/lab/profile")
def update_lab_profile():
    """Intentionally permissive assignment over transient fictional data only."""
    if not request.is_json:
        return _error("Request body must be JSON.", 415)

    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return _error("Request body must be a JSON object.", 400)

    display_name = body.get("display_name", "Fictional Learner")
    theme = body.get("theme", "light")
    if not isinstance(display_name, str) or not 1 <= len(display_name.strip()) <= 80:
        return _error("Fictional display name must be 1–80 characters.", 400)
    if not isinstance(theme, str) or theme not in {"light", "dark"}:
        return _error("Fictional theme must be light or dark.", 400)

    # Challenge 10's mass-assignment behavior is confined to this temporary
    # dictionary. It never reads from or writes to the real users table.
    lab_profile = {
        "display_name": display_name.strip(),
        "theme": theme,
        "lab_access": False,
    }
    lab_profile.update(body)

    response_payload = {
        "status": "updated",
        "profile": {
            "display_name": lab_profile["display_name"],
            "theme": lab_profile["theme"],
        },
    }
    if lab_profile.get("lab_access") is True:
        flag = _lab_flag(10)
        if flag is None:
            return _error("Lab profile reward is unavailable.", 404)
        response_payload["lab_reward"] = flag

    return jsonify(response_payload)


@api.get("/lab/capstone/audit")
def capstone_audit():
    """Deliberately flawed authorization over Challenge 13 records only."""
    record_id = request.args.get("record", type=int)
    if record_id is None or not 1300 <= record_id <= 1310:
        return _error("Choose a fictional audit record from 1300 through 1310.", 400)

    include_archived = request.args.get("include_archived") == "true"
    with closing(get_connection()) as connection:
        if include_archived:
            # Intentional capstone flaw: archived mode omits the fictional
            # alice-owner condition. This table has no real account records.
            row = connection.execute(
                """
                SELECT id, fictional_owner, archived, public_note, private_note
                FROM lab_final_records
                WHERE id = ? AND archived = 1
                """,
                (record_id,),
            ).fetchone()
        else:
            row = connection.execute(
                """
                SELECT id, fictional_owner, archived, public_note, private_note
                FROM lab_final_records
                WHERE id = ? AND fictional_owner = 'alice' AND archived = 0
                """,
                (record_id,),
            ).fetchone()

    if row is None:
        return _error("Fictional audit record not found.", 404)

    record = {
        "id": row["id"],
        "owner": row["fictional_owner"],
        "archived": bool(row["archived"]),
        "note": row["public_note"],
    }
    if include_archived:
        record["private_note"] = row["private_note"]

    response = jsonify(assumed_account="alice", record=record)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Lab-Optional-Query"] = "include_archived=true"
    return response


@api.get("/orders")
def orders():
    with closing(get_connection()) as connection:
        rows = connection.execute(
            """
            SELECT
                orders.id AS order_id,
                orders.status,
                orders.total_amount,
                orders.created_at,
                order_items.quantity,
                order_items.unit_price,
                products.id AS product_id,
                products.name AS product_name
            FROM orders
            LEFT JOIN order_items ON order_items.order_id = orders.id
            LEFT JOIN products ON products.id = order_items.product_id
            WHERE orders.user_id = ?
            ORDER BY orders.created_at DESC, orders.id DESC, order_items.id
            """,
            (g.current_user["id"],),
        ).fetchall()

    user_orders = []
    orders_by_id = {}
    for row in rows:
        order = orders_by_id.get(row["order_id"])
        if order is None:
            order = {
                "id": row["order_id"],
                "status": row["status"],
                "total_amount": row["total_amount"],
                "created_at": row["created_at"],
                "items": [],
            }
            orders_by_id[row["order_id"]] = order
            user_orders.append(order)

        if row["product_id"] is not None:
            order["items"].append(
                {
                    "product_id": row["product_id"],
                    "product_name": row["product_name"],
                    "quantity": row["quantity"],
                    "unit_price": row["unit_price"],
                }
            )

    return jsonify(orders=user_orders)


@api.get("/internal/debug")
def internal_debug():
    with closing(get_connection()) as connection:
        row = connection.execute(
            "SELECT flag FROM challenges WHERE id = 9 AND active = 1"
        ).fetchone()
    if row is None:
        return _error("Debug metadata is unavailable.", 404)

    response = jsonify(
        service="dashboard-activity",
        status="ok",
        debug_token=row["flag"],
    )
    response.headers["Cache-Control"] = "no-store"
    return response
