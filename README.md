# BurpLab CTF

BurpLab CTF is a local Burp Suite training lab intended for controlled security education. It will be intentionally vulnerable and must use fictional data only. Do not use it against real systems or without explicit authorization.

The application includes student registration and login, a fictional storefront,
authenticated HTML and JSON views, thirteen Burp Suite challenges, progressive
hints and scoring, a scoreboard, and an admin-only progress and reset area.

Students should continue with the [student guide](student/student-guide.md).
Instructors can use the [challenge map](instructor/challenge-map.md),
[answer key](instructor/answer-key.md), and
[reset guide](instructor/reset-guide.md).

## Setup

Python 3 is required. From the project root, create a virtual environment and install the dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

On Windows, activate the virtual environment with:

```powershell
.venv\Scripts\activate
```

## Run

Start the local development server from the project root:

```bash
python run.py
```

The landing page will be available at <http://127.0.0.1:5000>.

The server binds only to `127.0.0.1` by default. To make the lab reachable on the local network, explicitly set `LAB_ALLOW_LAN=1` before starting it.

## Docker quickstart

Docker Compose builds the image, initializes the fictional seed database on the
first start, and publishes the lab on the host loopback interface only:

```bash
docker compose up --build
```

Open <http://127.0.0.1:5000>. Stop the containers with:

```bash
docker compose down
```

The database is stored in the named `burplab_database` volume, so
`docker compose down` does not erase student progress. If the database file is
absent, the container entrypoint recreates it from `database/schema.sql` and
`database/seed.sql` before starting Flask.

### Deliberate classroom LAN access

In the default container, Flask itself still binds to `127.0.0.1`, honoring
the same `Config.HOST` default as a bare-metal run. Docker cannot publish a
container-loopback listener directly, so the image starts a small TCP relay
bound only to the container's assigned interface. That relay forwards the
Compose-published port to Flask on container loopback. Compose independently
restricts the host publication to `127.0.0.1:5000:5000`, giving the default
setup both an application binding boundary and a host publication boundary.

An instructor who has secured and isolated the classroom network must
explicitly enable the app's LAN bind and publish the Docker port on all host
interfaces:

```bash
LAB_ALLOW_LAN=1 LAB_BIND_ADDRESS=0.0.0.0 docker compose up --build
```

With `LAB_ALLOW_LAN=1`, the relay is skipped and Flask deliberately binds
directly to `0.0.0.0`. Both variables are required for the documented
classroom mode: `LAB_ALLOW_LAN` controls the application bind, while
`LAB_BIND_ADDRESS` controls Docker's host publication. This exposes an
intentionally vulnerable training application to the local network. Use it
only on a trusted classroom LAN, never on a public or internet-facing host.
Remove both overrides—or run `docker compose down`—when the class ends.

## Changelog

### v1.0 — 2026-09-02

- First complete BurpLab CTF release with authenticated student workflows,
  thirteen isolated challenges, progressive scoring, instructor controls, and
  reset support.
- Completed the application, CTF, teaching, and safety release checklist.
- Verified that fresh unauthenticated requests cannot retrieve challenge flags,
  administrator credentials, or instructor-only material.
- Added a localhost-only Docker Compose workflow with deliberate classroom LAN
  exposure available only through explicit opt-in settings.
