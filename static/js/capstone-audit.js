"use strict";

// Routine fictional audit activity. The result is deliberately not rendered.
fetch("/api/lab/capstone/audit?record=1301", {
    cache: "no-store",
    credentials: "same-origin",
    headers: {Accept: "application/json"},
})
    .then((response) => {
        if (!response.ok) {
            throw new Error("Audit request failed");
        }
        return response.json();
    })
    .catch(() => {
        // Audit activity must not disrupt the challenge page.
    });
