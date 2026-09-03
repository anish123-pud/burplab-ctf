#!/bin/sh
set -eu

if [ ! -f /app/database/burplab.db ]; then
    echo "No BurpLab database found; initializing fictional seed data."
    python /app/scripts/init_db.py
fi

# Docker port publishing cannot reach a process bound to the container's
# loopback interface. In default local-only mode, Flask still binds to
# 127.0.0.1 through Config.HOST while this relay listens only on the container's
# assigned interface and forwards traffic to Flask. Explicit LAN mode makes
# Flask bind directly to 0.0.0.0 and therefore does not use the relay.
if [ "${LAB_ALLOW_LAN:-0}" != "1" ] \
    && [ "${1:-}" = "python" ] \
    && [ "${2:-}" = "run.py" ]; then
    container_address="$(python -c 'import socket; print(socket.gethostbyname(socket.gethostname()))')"
    echo "Local-only mode: Flask binds to 127.0.0.1; Docker relay binds to ${container_address}."
    socat "TCP4-LISTEN:5000,bind=${container_address},reuseaddr,fork" TCP4:127.0.0.1:5000 &
fi

exec "$@"
