from flask import Flask, render_template, request

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    claim = request.form["claim"].lower()

    # Default values
    risk = "Low"
    reason = "This claim seems normal and does not use strong or misleading words."
    rewrite = claim

    # Rule-based logic
    if "cure" in claim or "guarantee" in claim or "100%" in claim:
        risk = "High"
        reason = "This claim uses exaggerated or absolute terms which can be misleading."
        rewrite = "This may help, but it is not guaranteed or scientifically proven."

    elif "may" in claim or "can" in claim:
        risk = "Medium"
        reason = "This claim is uncertain and lacks strong supporting evidence."
        rewrite = "This might have some benefits, but more evidence is needed."

    elif "always" in claim or "never" in claim:
        risk = "High"
        reason = "Absolute words like 'always' or 'never' make the claim unreliable."
        rewrite = "This may not apply in all situations and needs proper validation."

    # Result dictionary
    result = {
        "risk": risk,
        "reason": reason,
        "rewrite": rewrite
    }

    return render_template("index.html", result=result)


if __name__ == "__main__":
    app.run(debug=True)