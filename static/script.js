let radarChartInst = null;

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
    const exportCardBtn = document.getElementById("exportCardBtn");
    const premiumModal = document.getElementById("premiumModal");
    const closeModal = document.getElementById("closeModal");

    if (exportCardBtn) {
        exportCardBtn.addEventListener("click", () => {
            const originalText = exportCardBtn.innerHTML;
            exportCardBtn.innerHTML = '<span class="icon">⏳</span> Generating...';
            
            const truthCard = document.getElementById("truthCard");
            html2canvas(truthCard, {
                backgroundColor: "#0f172a",
                scale: 2 // High res export
            }).then(canvas => {
                const link = document.createElement('a');
                link.download = 'declaim-truth-card.png';
                link.href = canvas.toDataURL("image/png");
                link.click();
                exportCardBtn.innerHTML = '<span class="icon">✅</span> Exported!';
                setTimeout(() => { exportCardBtn.innerHTML = originalText; }, 3000);
            }).catch(e => {
                console.error(e);
                exportCardBtn.innerHTML = '<span class="icon">⚠️</span> Failed';
                setTimeout(() => { exportCardBtn.innerHTML = originalText; }, 3000);
            });
        });
    }

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
                // Determine risk class from percentage
                const fakePct = data.fake_percentage;
                riskBadge.textContent = fakePct + "% FAKE";
                
                // Clear old risk classes
                riskBadge.classList.remove("risk-low", "risk-medium", "risk-high");
                
                if (fakePct <= 35) {
                    riskBadge.classList.add("risk-low");
                } else if (fakePct > 35 && fakePct <= 70) {
                    riskBadge.classList.add("risk-medium");
                } else {
                    riskBadge.classList.add("risk-high");
                }

                reasonText.textContent = data.reason;
                rewriteText.textContent = data.rewrite;

                // Populate offscreen truth card
                const tcRisk = document.getElementById('tcRisk');
                if(tcRisk) tcRisk.textContent = fakePct + "% FAKE";
                const tcClaim = document.getElementById('tcClaim');
                if(tcClaim) tcClaim.textContent = `"${claim}"`;
                const tcTruth = document.getElementById('tcTruth');
                if(tcTruth) tcTruth.textContent = data.rewrite;

                if (data.metrics) {
                    const radarContainer = document.getElementById("radarContainer");
                    radarContainer.classList.remove("hidden");
                    const ctx = document.getElementById('radarChart').getContext('2d');
                    if (radarChartInst) {
                        radarChartInst.destroy();
                    }
                    radarChartInst = new Chart(ctx, {
                        type: 'radar',
                        data: {
                            labels: ['Political Bias', 'Emotional Sensationalism', 'Clickbait Severity', 'Logical Fallacy'],
                            datasets: [{
                                label: 'Severity Index',
                                data: [
                                    data.metrics.political_bias, 
                                    data.metrics.emotional_sensationalism, 
                                    data.metrics.clickbait_severity, 
                                    data.metrics.logical_fallacy
                                ],
                                backgroundColor: 'rgba(185, 28, 28, 0.2)', // red accent
                                borderColor: 'rgba(185, 28, 28, 1)',
                                pointBackgroundColor: 'rgba(185, 28, 28, 1)',
                                pointBorderColor: '#fff',
                                pointHoverBackgroundColor: '#fff',
                                pointHoverBorderColor: 'rgba(185, 28, 28, 1)'
                            }]
                        },
                        options: {
                            scales: {
                                r: {
                                    angleLines: { color: 'rgba(148, 163, 184, 0.2)' },
                                    grid: { color: 'rgba(148, 163, 184, 0.2)' },
                                    pointLabels: { color: '#475569', font: { size: 13, family: "'Inter', sans-serif", weight: 'bold' } },
                                    ticks: { display: false, min: 0, max: 100 }
                                }
                            },
                            plugins: {
                                legend: { display: false }
                            }
                        }
                    });
                } else {
                    document.getElementById("radarContainer").classList.add("hidden");
                }

                if (data.new_score !== undefined) {
                    const badgeEl = document.getElementById("userBadge");
                    const scoreEl = document.getElementById("userScore");
                    const progressEl = document.getElementById("scoreProgress");
                    
                    if (badgeEl) badgeEl.textContent = data.new_badge;
                    if (scoreEl) scoreEl.textContent = data.new_score;
                    if (progressEl) progressEl.style.width = (data.new_score % 100) + "%";
                }

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
