"use strict";

const labProfileButton = document.getElementById("lab-profile-update");
const labProfileOutput = document.getElementById("lab-profile-output");

if (labProfileButton && labProfileOutput) {
    labProfileButton.addEventListener("click", async () => {
        labProfileButton.disabled = true;
        labProfileOutput.textContent = "Sending fictional profile update…";

        try {
            const response = await fetch(labProfileButton.dataset.endpoint, {
                method: "POST",
                credentials: "same-origin",
                headers: {
                    Accept: "application/json",
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    display_name: "Fictional Learner",
                    theme: "light",
                }),
            });
            if (!response.ok) {
                throw new Error("Lab profile update failed");
            }
            const payload = await response.json();
            labProfileOutput.textContent = `Updated ${payload.profile.display_name}.`;
        } catch {
            labProfileOutput.textContent = "Unable to update the fictional profile.";
        } finally {
            labProfileButton.disabled = false;
        }
    });
}
