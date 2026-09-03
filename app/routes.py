import hashlib
import hmac
import secrets
import sqlite3
from contextlib import closing
from functools import wraps

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from app.auth import (
    EMAIL_PATTERN,
    RegistrationError,
    USERNAME_PATTERN,
    authenticate_user,
    create_session,
    destroy_session,
    get_user_for_session,
    register_user,
)
from app.database import get_connection
from app.challenges import (
    get_challenge,
    get_challenge_progress,
    get_user_challenge_summary,
    list_challenges,
    list_scoreboard,
    list_user_completions,
    reveal_hint,
    submit_flag,
)


main = Blueprint("main", __name__)


def _csrf_token() -> str:
    token = session.get("csrf_token")
    if not isinstance(token, str):
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    return token


def _require_valid_csrf() -> None:
    expected = session.pop("csrf_token", None)
    if request.is_json:
        body = request.get_json(silent=True)
        submitted = request.headers.get("X-CSRF-Token", "")
        if not submitted and isinstance(body, dict):
            submitted = body.get("csrf_token", "")
    else:
        submitted = request.form.get("csrf_token", "")
    if (
        not isinstance(expected, str)
        or not isinstance(submitted, str)
        or not submitted
        or not hmac.compare_digest(expected, submitted)
    ):
        abort(400, description="Invalid or missing CSRF token.")


def _authenticated_user():
    token = session.get("auth_token")
    if not isinstance(token, str):
        return None
    return get_user_for_session(token)


def _lab_flag(challenge_id: int) -> str:
    """Load a flag only for an intentional challenge response."""
    with closing(get_connection()) as connection:
        row = connection.execute(
            "SELECT flag FROM challenges WHERE id = ? AND active = 1",
            (challenge_id,),
        ).fetchone()
    if row is None:
        abort(404)
    return row["flag"]


def _optional_lab_flag(challenge_id: int) -> str | None:
    """Load optional lab metadata without disrupting a normal application flow."""
    with closing(get_connection()) as connection:
        row = connection.execute(
            "SELECT flag FROM challenges WHERE id = ? AND active = 1",
            (challenge_id,),
        ).fetchone()
    return row["flag"] if row is not None else None


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        user = _authenticated_user()
        if user is None:
            session.clear()
            flash("Please log in to continue.", "error")
            return redirect(url_for("main.login"))

        g.current_user = user
        return view(*args, **kwargs)

    return wrapped_view


@main.route("/")
def index():
    return render_template("index.html", csrf_token=_csrf_token())


@main.route("/register", methods=["GET", "POST"])
def register():
    if _authenticated_user() is not None:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        _require_valid_csrf()
        try:
            register_user(
                username=request.form.get("username", ""),
                password=request.form.get("password", ""),
                email=request.form.get("email", ""),
            )
        except RegistrationError as exc:
            flash(str(exc), "error")
            return (
                render_template(
                    "register.html",
                    csrf_token=_csrf_token(),
                    username=request.form.get("username", ""),
                    email=request.form.get("email", ""),
                ),
                400,
            )

        flash("Registration complete. You can now log in.", "success")
        return redirect(url_for("main.login"))

    return render_template("register.html", csrf_token=_csrf_token())


@main.route("/login", methods=["GET", "POST"])
def login():
    if _authenticated_user() is not None:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        _require_valid_csrf()
        user = authenticate_user(
            username=request.form.get("username", ""),
            password=request.form.get("password", ""),
        )
        if user is None:
            flash("Invalid username or password.", "error")
            return (
                render_template(
                    "login.html",
                    csrf_token=_csrf_token(),
                    username=request.form.get("username", ""),
                ),
                401,
            )

        old_token = session.get("auth_token")
        if isinstance(old_token, str):
            destroy_session(old_token)

        token = create_session(user["id"])
        session.clear()
        session.permanent = True
        session["auth_token"] = token
        session["csrf_token"] = secrets.token_urlsafe(32)
        response = redirect(url_for("main.dashboard"))
        investigation_flag = _optional_lab_flag(7)
        if investigation_flag is not None:
            response.headers["X-Lab-Login-Note"] = investigation_flag
        return response

    return render_template("login.html", csrf_token=_csrf_token())


@main.route("/dashboard")
@login_required
def dashboard():
    summary = get_user_challenge_summary(g.current_user["id"])
    return render_template(
        "dashboard.html",
        username=g.current_user["username"],
        completed=summary["completed"],
        total=summary["total"],
        score=summary["score"],
        csrf_token=_csrf_token(),
    )


@main.route("/scoreboard")
@login_required
def scoreboard():
    return render_template(
        "scoreboard.html",
        standings=list_scoreboard(),
        csrf_token=_csrf_token(),
    )


@main.route("/challenges")
@login_required
def challenges():
    challenge_rows = list_challenges()
    completions = list_user_completions(g.current_user["id"])
    completed_ids = {completion["challenge_id"] for completion in completions}
    for challenge_row in challenge_rows:
        challenge_row["completed"] = challenge_row["id"] in completed_ids

    return render_template(
        "challenges.html",
        challenges=challenge_rows,
        csrf_token=_csrf_token(),
    )


@main.get("/challenge/<int:challenge_id>")
@login_required
def challenge(challenge_id: int):
    public_challenge = get_challenge(challenge_id)
    if public_challenge is None:
        abort(404)

    challenge_with_hints = get_challenge(challenge_id, include_hints=True)
    hints_available = any(
        challenge_with_hints.get(f"hint_{number}")
        for number in range(1, 4)
    )

    progress = get_challenge_progress(g.current_user["id"], challenge_id)
    hint_count = progress["highest_hint"]
    challenge_row = get_challenge(
        challenge_id,
        include_hints=hint_count > 0,
    )

    revealed_hints = []
    if hint_count:
        revealed_hints = [
            challenge_row.get(f"hint_{number}")
            for number in range(1, hint_count + 1)
        ]
        revealed_hints = [hint for hint in revealed_hints if hint]

    completed_ids = {
        completion["challenge_id"]
        for completion in list_user_completions(g.current_user["id"])
    }

    return render_template(
        "challenge.html",
        challenge=public_challenge,
        completed=challenge_id in completed_ids,
        revealed_hints=revealed_hints,
        hint_count=hint_count,
        hints_available=hints_available,
        csrf_token=_csrf_token(),
    )


@main.post("/challenge/<int:challenge_id>/hint/<int:hint_number>")
@login_required
def reveal_challenge_hint(challenge_id: int, hint_number: int):
    wants_json = request.is_json
    _require_valid_csrf()

    result = reveal_hint(g.current_user["id"], challenge_id, hint_number)
    if result is None:
        if wants_json:
            return jsonify(error="Hint not found."), 404
        abort(404)

    if result["locked"]:
        message = f"Reveal hint {hint_number - 1} first."
        if wants_json:
            return jsonify(
                error=message,
                highest_hint=result["highest_hint"],
                csrf_token=_csrf_token(),
            ), 409
        flash(message, "error")
        return redirect(url_for("main.challenge", challenge_id=challenge_id))

    if wants_json:
        return jsonify(
            status="revealed",
            hint_number=result["hint_number"],
            hint=result["hint"],
            highest_hint=result["highest_hint"],
            newly_revealed=result["newly_revealed"],
            csrf_token=_csrf_token(),
        )

    if result["newly_revealed"]:
        flash(f"Hint {hint_number} revealed.", "success")
    return redirect(url_for("main.challenge", challenge_id=challenge_id))


@main.route("/challenge/<int:challenge_id>/submit", methods=["POST"])
@login_required
def submit_challenge(challenge_id: int):
    wants_json = request.is_json
    _require_valid_csrf()

    if wants_json:
        body = request.get_json(silent=True)
        submitted_flag = body.get("flag") if isinstance(body, dict) else None
    else:
        submitted_flag = request.form.get("flag")

    if not isinstance(submitted_flag, str):
        if wants_json:
            return jsonify(error="A flag string is required."), 400
        flash("A flag string is required.", "error")
        return redirect(url_for("main.challenge", challenge_id=challenge_id))

    result = submit_flag(g.current_user["id"], challenge_id, submitted_flag)
    if result is None:
        if wants_json:
            return jsonify(error="Challenge not found."), 404
        abort(404)

    if result["rapid"]:
        current_app.logger.warning(
            "Rapid challenge submission: user_id=%s challenge_id=%s attempt=%s",
            g.current_user["id"],
            challenge_id,
            result["attempts"],
        )

    if result["already_completed"]:
        message = "Challenge already completed; no additional points awarded."
        if wants_json:
            return jsonify(
                status="correct",
                message=message,
                already_completed=True,
                points_awarded=result["points_awarded"],
                csrf_token=_csrf_token(),
            )
        flash(message, "success")
        return redirect(url_for("main.challenge", challenge_id=challenge_id))

    if not result["correct"]:
        message = "Incorrect flag."
        current_app.logger.info(
            "Incorrect challenge submission: user_id=%s challenge_id=%s attempt=%s",
            g.current_user["id"],
            challenge_id,
            result["attempts"],
        )
        if wants_json:
            return jsonify(
                status="incorrect",
                error=message,
                attempts=result["attempts"],
                csrf_token=_csrf_token(),
            ), 400
        flash(message, "error")
        return redirect(url_for("main.challenge", challenge_id=challenge_id))

    message = f"Correct flag. {result['points_awarded']} points awarded."
    if wants_json:
        return jsonify(
            status="correct",
            message=message,
            already_completed=False,
            points_awarded=result["points_awarded"],
            hints_used=result["hints_used"],
            csrf_token=_csrf_token(),
        )
    flash(message, "success")
    return redirect(url_for("main.challenge", challenge_id=challenge_id))


@main.route("/lab/first-request")
@login_required
def first_request_lab():
    response = jsonify(
        status="ok",
        message="The fictional training request completed successfully.",
    )
    response.headers["X-Lab-Flag"] = _lab_flag(1)
    return response


@main.route("/lab/read-response/data")
@login_required
def read_response_lab_data():
    return jsonify(
        message="The fictional response reader finished loading.",
        internal_note=_lab_flag(2),
    )


@main.route("/product")
@login_required
def repeater_lab():
    product_id = request.args.get("id", type=int)
    if product_id is None or not 1 <= product_id <= 50:
        return jsonify(error="Choose a fictional product id from 1 through 50."), 400

    with closing(get_connection()) as connection:
        product_row = connection.execute(
            """
            SELECT id, name, price, stock
            FROM lab_products
            WHERE id = ?
            """,
            (product_id,),
        ).fetchone()
    if product_row is None:
        return jsonify(error="Product not found."), 404

    response = jsonify(
        product={
            "id": product_row["id"],
            "name": product_row["name"],
            "price": product_row["price"],
            "stock": product_row["stock"],
        }
    )
    if product_id == 3:
        response.headers["X-Lab-Flag"] = _lab_flag(3)
    elif product_id == 42:
        response.headers["X-Lab-Flag"] = _lab_flag(4)
    return response


@main.route("/lab/cookies/start")
@login_required
def cookies_lab_start():
    cookie_value = secrets.token_urlsafe(24)
    token_digest = hashlib.sha256(cookie_value.encode("utf-8")).hexdigest()
    with closing(get_connection()) as connection:
        with connection:
            connection.execute(
                """
                INSERT INTO lab_cookie_tokens (user_id, token_digest, created_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT (user_id) DO UPDATE SET
                    token_digest = excluded.token_digest,
                    created_at = excluded.created_at
                """,
                (g.current_user["id"], token_digest),
            )

    response = jsonify(
        status="issued",
        message="Inspect the challenge-scoped session cookie, then use its value with the related check request.",
        cookie_name="blctf_lab_session",
        check_path="/lab/cookies/check?session_value=VALUE",
    )
    response.set_cookie(
        "blctf_lab_session",
        cookie_value,
        max_age=600,
        httponly=True,
        secure=current_app.config.get("SESSION_COOKIE_SECURE", False),
        samesite="Lax",
        path="/lab/cookies",
    )
    return response


@main.route("/lab/cookies/check")
@login_required
def cookies_lab_check():
    submitted_value = request.args.get("session_value", "")
    cookie_value = request.cookies.get("blctf_lab_session", "")
    submitted_digest = hashlib.sha256(submitted_value.encode("utf-8")).hexdigest()

    with closing(get_connection()) as connection:
        row = connection.execute(
            "SELECT token_digest FROM lab_cookie_tokens WHERE user_id = ?",
            (g.current_user["id"],),
        ).fetchone()

    valid = (
        row is not None
        and bool(submitted_value)
        and bool(cookie_value)
        and hmac.compare_digest(
            cookie_value.encode("utf-8"), submitted_value.encode("utf-8")
        )
        and hmac.compare_digest(row["token_digest"], submitted_digest)
    )
    if not valid:
        return jsonify(error="The challenge session value is missing or invalid."), 400

    response = jsonify(
        status="verified",
        message="The challenge-scoped session value was validated.",
    )
    response.headers["X-Lab-Flag"] = _lab_flag(5)
    return response


@main.route("/lab/headers")
@login_required
def headers_lab():
    debug_enabled = request.headers.get("X-Lab-Debug") == "enabled"
    response = jsonify(
        mode="debug" if debug_enabled else "standard",
        message="Fictional lab diagnostics are enabled."
        if debug_enabled
        else "Fictional lab request completed in standard mode.",
    )
    if debug_enabled:
        response.headers["X-Lab-Flag"] = _lab_flag(6)
    return response


@main.route("/challenge-orders/<int:order_id>")
@login_required
def challenge_order(order_id: int):
    with closing(get_connection()) as connection:
        # Intentional IDOR for Challenge 8 only: this isolated fictional route
        # omits the alice-owner filter. The real /orders route remains scoped by
        # g.current_user["id"] and never reads these lab tables.
        order = connection.execute(
            """
            SELECT
                lab_orders.id,
                lab_order_accounts.username AS owner,
                lab_orders.item_name,
                lab_orders.total_amount,
                lab_orders.private_note
            FROM lab_orders
            JOIN lab_order_accounts
                ON lab_order_accounts.id = lab_orders.account_id
            WHERE lab_orders.id = ?
            """,
            (order_id,),
        ).fetchone()
    if order is None:
        return jsonify(error="Fictional challenge order not found."), 404

    return jsonify(
        assumed_account="alice",
        order={
            "id": order["id"],
            "owner": order["owner"],
            "item_name": order["item_name"],
            "total_amount": order["total_amount"],
            "private_note": order["private_note"],
        },
    )


@main.get("/lab/archive/retired-status")
@login_required
def retired_lab_status():
    """Challenge 11 endpoint referenced only by a static investigation asset."""
    return jsonify(
        service="fictional-retired-status",
        status="archived",
        archive_key=_lab_flag(11),
    )


@main.get("/lab/chain/start")
@login_required
def chain_lab_start():
    record_id = request.args.get("record", type=int)
    if record_id is None or not 1 <= record_id <= 20:
        return jsonify(error="Choose a fictional record from 1 through 20."), 400

    if record_id != 12:
        return jsonify(
            record={"id": record_id, "status": "ordinary"},
            message="This fictional record has no follow-up action.",
        )

    cookie_value = secrets.token_urlsafe(24)
    token_digest = hashlib.sha256(cookie_value.encode("utf-8")).hexdigest()
    with closing(get_connection()) as connection:
        with connection:
            connection.execute(
                """
                INSERT INTO lab_chain_tokens (user_id, token_digest, created_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT (user_id) DO UPDATE SET
                    token_digest = excluded.token_digest,
                    created_at = excluded.created_at
                """,
                (g.current_user["id"], token_digest),
            )

    response = jsonify(
        record={"id": record_id, "status": "handoff-ready"},
        message="Use the issued challenge token with the second endpoint.",
        next_path="/lab/chain/finish",
    )
    response.set_cookie(
        "blctf_chain_token",
        cookie_value,
        max_age=600,
        httponly=True,
        secure=current_app.config.get("SESSION_COOKIE_SECURE", False),
        samesite="Lax",
        path="/lab/chain",
    )
    response.headers["Cache-Control"] = "no-store"
    return response


@main.get("/lab/chain/finish")
@login_required
def chain_lab_finish():
    cookie_value = request.cookies.get("blctf_chain_token", "")
    submitted_digest = hashlib.sha256(cookie_value.encode("utf-8")).hexdigest()
    with closing(get_connection()) as connection:
        row = connection.execute(
            """
            SELECT token_digest
            FROM lab_chain_tokens
            WHERE user_id = ?
              AND created_at >= datetime('now', '-10 minutes')
            """,
            (g.current_user["id"],),
        ).fetchone()

    valid = (
        row is not None
        and bool(cookie_value)
        and hmac.compare_digest(row["token_digest"], submitted_digest)
    )
    if not valid:
        return jsonify(error="A valid challenge chain token is required."), 403

    response = jsonify(
        status="chain-complete",
        flag=_lab_flag(12),
    )
    response.headers["Cache-Control"] = "no-store"
    return response


@main.route("/products")
@login_required
def products():
    with closing(get_connection()) as connection:
        product_rows = connection.execute(
            """
            SELECT id, name, description, price, stock
            FROM products
            ORDER BY id
            """
        ).fetchall()

    return render_template(
        "products.html",
        products=product_rows,
        csrf_token=_csrf_token(),
    )


@main.route("/product/<int:product_id>")
@login_required
def product(product_id: int):
    with closing(get_connection()) as connection:
        product_row = connection.execute(
            """
            SELECT id, name, description, price, stock, created_at
            FROM products
            WHERE id = ?
            """,
            (product_id,),
        ).fetchone()

    if product_row is None:
        abort(404)

    return render_template(
        "product.html",
        product=product_row,
        csrf_token=_csrf_token(),
    )


@main.route("/orders")
@login_required
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

    return render_template(
        "orders.html",
        orders=user_orders,
        csrf_token=_csrf_token(),
    )


@main.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        _require_valid_csrf()
        username = request.form.get("username", "").strip().lower()
        email = request.form.get("email", "").strip().lower()

        error = None
        if not USERNAME_PATTERN.fullmatch(username):
            error = (
                "Username must be 3–32 characters using lowercase letters, "
                "numbers, or underscores."
            )
        elif len(email) > 254 or not EMAIL_PATTERN.fullmatch(email):
            error = "Enter a valid email address."

        if error is None:
            try:
                with closing(get_connection()) as connection:
                    with connection:
                        connection.execute(
                            """
                            UPDATE users
                            SET username = ?, email = ?
                            WHERE id = ?
                            """,
                            (username, email, g.current_user["id"]),
                        )
            except sqlite3.IntegrityError:
                error = "That username or email is already registered."

        if error is not None:
            flash(error, "error")
            return (
                render_template(
                    "profile.html",
                    user={
                        "username": username,
                        "email": email,
                        "role": g.current_user["role"],
                    },
                    csrf_token=_csrf_token(),
                ),
                400,
            )

        flash("Profile updated.", "success")
        return redirect(url_for("main.profile"))

    return render_template(
        "profile.html",
        user=g.current_user,
        csrf_token=_csrf_token(),
    )


@main.route("/logout", methods=["POST"])
def logout():
    _require_valid_csrf()
    token = session.get("auth_token")
    if isinstance(token, str):
        destroy_session(token)
    session.clear()
    return redirect(url_for("main.login"))
