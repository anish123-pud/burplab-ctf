# BurpLab CTF Reset Guide

The reset system restores the entire local lab database from `database/schema.sql` and `database/seed.sql`. It is intended for instructors preparing a clean environment between classes, cohorts, demonstrations, or individual assessment sessions.

## What a Reset Does

A reset permanently removes runtime data and restores the original fictional seed state, including:

- registered and modified users;
- active server-side login sessions;
- product and order changes;
- challenge attempts and progressive hint usage;
- challenge completions and awarded scores;
- temporary challenge cookies, tokens, and lab-only records.

The seeded students, administrator, products, orders, challenge definitions, and fictional lab records are recreated. Every browser session becomes invalid, including the administrator that initiated the reset.

## When to Reset

Use a reset before a new class or cohort, between students sharing an installation, after a demonstration, or whenever testing must begin from known seed data. Do not reset while students are working. There is no undo or export workflow in the current UI, so preserve any results needed for grading first.

## Admin Reset Procedure

1. Confirm the Flask application is running locally.
2. Log in with the seeded administrator:
   - Username: `admin01`
   - Password: `admin-lab-only`
3. Open **Admin** from the navigation bar.
4. Select **Review reset confirmation**.
5. Read the warning and confirm that no active work must be preserved.
6. Type `RESET` exactly.
7. Select **Reset lab data** once.
8. Wait for the login-page redirect, which confirms the initiating session was invalidated.
9. Log in again and verify both seeded students show zero progress and zero scores.

Missing or incorrectly cased confirmation text does not alter the database.

## Command-Line Reset

When the web application is stopped, an instructor may run the same recreation logic from the project directory:

```bash
python scripts/init_db.py
```

Prefer stopping the development server first when using the command line. The web reset coordinates the operation inside the running process and is preferred during normal use.

## Access and Safety Controls

- Only a valid session whose database role is exactly `admin` can access `/admin/reset`.
- Anonymous, student, and legacy `instructor` roles receive `404 Not Found`.
- Execution requires `POST`, a current CSRF token, and exact typed confirmation.
- A process lock prevents overlapping resets within the local Flask process.
- Repeated resets recreate the same schema and seed state without accumulating rows.
- The application remains bound to `127.0.0.1` unless LAN access was explicitly enabled.

## Reset Logging

After success, the application logs `event=admin_reset`, the initiating fictional administrator's numeric user ID, and an ISO 8601 UTC timestamp. It does not log usernames, passwords, hashes, session or CSRF tokens, submitted flags, or stored flags. With the development server, the entry appears in the server console and survives database recreation because it is not stored in the reset database.

## Post-reset Verification

Confirm that only seeded accounts remain, both students show `0 / 13` and zero points, submission activity is empty, products and orders match seed data, and normal student access works. For a development verification run:

```bash
python -m unittest discover -s tests -v
```

The reset tests repeat recreation and validate SQLite integrity and foreign-key consistency.

## Recovery Notes

If a web reset is interrupted, stop Flask and run `python scripts/init_db.py` once. If it fails, preserve the console output for diagnosis and do not manually edit `database/burplab.db`; the schema and seed SQL files are the authoritative recovery source.
