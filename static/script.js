document.addEventListener("DOMContentLoaded", () => {
    const analyzeBtn = document.getElementById("analyzeBtn");
    const claimInput = document.getElementById("claimInput");
    const loadingState = document.getElementById("loadingState");
    const resultBox = document.getElementById("resultBox");
    const riskBadge = document.getElementById("riskBadge");
    const reasonText = document.getElementById("reasonText");
    const rewriteText = document.getElementById("rewriteText");
    const errorBox = document.getElementById("errorBox");
    const errorText = document.getElementById("errorText");

    const detailedAnalysisBtn = document.getElementById("detailedAnalysisBtn");
    const premiumModal = document.getElementById("premiumModal");
    const closeModal = document.getElementById("closeModal");

    detailedAnalysisBtn.addEventListener("click", () => {
        premiumModal.classList.remove("hidden");
    });

    closeModal.addEventListener("click", () => {
        premiumModal.classList.add("hidden");
    });

    premiumModal.addEventListener("click", (e) => {
        if (e.target === premiumModal) {
            premiumModal.classList.add("hidden");
        }
    });

    analyzeBtn.addEventListener("click", async () => {
        const claim = claimInput.value.trim();
        if (!claim) return;

        // Hide old results/errors and show loading
        resultBox.classList.add("hidden");
        errorBox.classList.add("hidden");
        loadingState.classList.remove("hidden");
        analyzeBtn.disabled = true;

        try {
            const response = await fetch("/analyze", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ claim })
            });

            const data = await response.json();

            loadingState.classList.add("hidden");

            if (!response.ok) {
                // Show error
                errorText.textContent = data.error || "An error occurred while analyzing the claim.";
                errorBox.classList.remove("hidden");
            } else {
                // Determine risk class
                const riskLevel = data.risk.toUpperCase();
                riskBadge.textContent = riskLevel + " RISK";
                
                // Clear old risk classes
                riskBadge.classList.remove("risk-low", "risk-medium", "risk-high");
                
                if (riskLevel === "LOW") {
                    riskBadge.classList.add("risk-low");
                } else if (riskLevel === "MEDIUM") {
                    riskBadge.classList.add("risk-medium");
                } else if (riskLevel === "HIGH") {
                    riskBadge.classList.add("risk-high");
                } else {
                    riskBadge.classList.add("risk-medium"); // fallback
                }

                reasonText.textContent = data.reason;
                rewriteText.textContent = data.rewrite;

                resultBox.classList.remove("hidden");
            }
        } catch (e) {
            loadingState.classList.add("hidden");
            errorText.textContent = "Failed to communicate with the server. Please check your connection.";
            errorBox.classList.remove("hidden");
            console.error(e);
        } finally {
            analyzeBtn.disabled = false;
        }
    });
});
