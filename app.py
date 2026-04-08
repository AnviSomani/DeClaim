import os
import json
import sqlite3
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from dotenv import load_dotenv
from google import genai

# Load environment variables
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

app = Flask(__name__)
app.secret_key = "super_secret_premium_key"

def init_db():
    conn = sqlite3.connect('history.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            claim TEXT,
            risk TEXT,
            reason TEXT,
            rewrite TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Configure Gemini API
if api_key:
    client = genai.Client(api_key=api_key)
else:
    client = None

@app.route("/")
def home():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("index.html", user=session["user"])

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        session["user"] = request.form.get("username", "Premium User")
        return redirect(url_for("home"))
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))

@app.route("/history")
def history_page():
    if "user" not in session:
        return redirect(url_for("login"))
    
    conn = sqlite3.connect('history.db')
    c = conn.cursor()
    c.execute('SELECT claim, risk, reason, rewrite, timestamp FROM history WHERE username = ? ORDER BY timestamp DESC', (session['user'],))
    records = c.fetchall()
    conn.close()
    
    parsed_records = []
    for r in records:
        parsed_records.append({
            "claim": r[0],
            "risk": r[1],
            "reason": r[2],
            "rewrite": r[3],
            "timestamp": r[4]
        })

    return render_template("history.html", history=parsed_records, user=session["user"])

@app.route("/analyze", methods=["POST"])
def analyze():
    if not client:
        return jsonify({"error": "Gemini API key is missing or invalid. Please check your .env file."}), 500

    data = request.get_json()
    if not data or 'claim' not in data:
        return jsonify({"error": "No claim provided."}), 400

    claim = data['claim']

    prompt = f"""
    Analyze the following news claim or statement for factual accuracy and bias.
    Claim: "{claim}"

    Return the analysis as a JSON object with the following exact keys:
    "risk": a string which must be either "Low", "Medium", or "High".
    "reason": a concise string explaining the reasoning behind the risk level.
    "rewrite": a factual, neutral version of the claim, or a corrected truth if the claim is false.

    Do not include markdown tags (like ```json). Return ONLY valid JSON.
    """

    try:
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=prompt,
        )
        # Parse the JSON response
        response_text = response.text.replace('```json', '').replace('```', '').strip()
        result_json = json.loads(response_text)
        
        # Ensure correct keys
        risk = result_json.get("risk", "Medium")
        reason = result_json.get("reason", "Analysis failed.")
        rewrite = result_json.get("rewrite", "No rewrite available.")

        # Save to history DB
        try:
            conn = sqlite3.connect('history.db')
            c = conn.cursor()
            c.execute('INSERT INTO history (username, claim, risk, reason, rewrite) VALUES (?, ?, ?, ?, ?)',
                      (session.get('user', 'Anonymous'), claim, risk, reason, rewrite))
            conn.commit()
            conn.close()
        except Exception as db_e:
            print("DB error:", db_e)

        return jsonify({
            "risk": risk,
            "reason": reason,
            "rewrite": rewrite
        })

    except Exception as e:
        error_message = str(e)
        if '429' in error_message or 'RESOURCE_EXHAUSTED' in error_message:
            # Emergency fallback logic to keep the UI working smoothly!
            mock_risk = "High"
            mock_reason = "[Offline Cache] We intercepted an API Quota limit. Proceeding with simulated fallback analysis instead of crashing."
            mock_rewrite = "Please try again in 30 seconds for live network responses."
            
            try:
                conn = sqlite3.connect('history.db')
                c = conn.cursor()
                c.execute('INSERT INTO history (username, claim, risk, reason, rewrite) VALUES (?, ?, ?, ?, ?)',
                          (session.get('user', 'Anonymous'), claim, mock_risk, mock_reason, mock_rewrite))
                conn.commit()
                conn.close()
            except Exception:
                pass
                
            return jsonify({
                "risk": mock_risk,
                "reason": mock_reason,
                "rewrite": mock_rewrite
            })
            
        import traceback
        traceback.print_exc()
        print(f"Error calling Gemini AI: {e}")
        return jsonify({"error": error_message}), 500


if __name__ == "__main__":
    app.run(debug=True)