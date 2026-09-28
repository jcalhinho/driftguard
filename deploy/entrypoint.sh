#!/bin/sh
# Start as root only long enough to fix ownership, then run the service unprivileged.
set -e

if [ "$(id -u)" = "0" ]; then
    # Volumes created by older (root) images keep root ownership: hand them over.
    mkdir -p /data
    chown -R driftguard:driftguard /data

    # The key is bind-mounted read-only with host ownership (often 0600): give the
    # service its own readable copy.
    if [ -n "$GITHUB_APP_PRIVATE_KEY_PATH" ] && [ -f "$GITHUB_APP_PRIVATE_KEY_PATH" ]; then
        install -d -o driftguard -g driftguard -m 700 /run/driftguard
        install -o driftguard -g driftguard -m 400 \
            "$GITHUB_APP_PRIVATE_KEY_PATH" /run/driftguard/app-key.pem
        export GITHUB_APP_PRIVATE_KEY_PATH=/run/driftguard/app-key.pem
    fi

    exec setpriv --reuid=driftguard --regid=driftguard --init-groups "$@"
fi

exec "$@"
