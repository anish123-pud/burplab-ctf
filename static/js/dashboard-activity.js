"use strict";

// This background activity is intentionally not rendered. Challenge students
// discover its response by reviewing authenticated Proxy HTTP history.
fetch("/api/internal/debug", {
    cache: "no-store",
    credentials: "same-origin",
    headers: {Accept: "application/json"},
})
    .then((response) => {
        if (!response.ok) {
            throw new Error("Dashboard activity request failed");
        }
        return response.json();
    })
    .catch(() => {
        // Background diagnostics must not disrupt the normal dashboard.
    });
