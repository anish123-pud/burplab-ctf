"use strict";

const responseReader = document.getElementById("response-reader");
const responseOutput = document.getElementById("response-reader-output");

if (responseReader && responseOutput) {
    responseReader.addEventListener("click", async () => {
        responseReader.disabled = true;
        responseOutput.textContent = "Loading response…";

        try {
            const response = await fetch(responseReader.dataset.endpoint, {
                credentials: "same-origin",
                headers: {Accept: "application/json"},
            });
            if (!response.ok) {
                throw new Error("Response request failed");
            }

            const payload = await response.json();
            // The exercise is to inspect the complete HTTP response. The page
            // intentionally displays only its public message.
            responseOutput.textContent = payload.message;
        } catch {
            responseOutput.textContent = "Unable to load the response.";
        } finally {
            responseReader.disabled = false;
        }
    });
}
