import os
import json
import sqlite3
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize OpenAI Client (Routed to Groq)
client = OpenAI(
    api_key=os.environ.get("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

app = Flask(__name__)
app.secret_key = "super_secret_premium_key"

# ---------------- DATABASE ----------------
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

# ---------------- ROUTES ----------------
@app.context_processor
def inject_user_stats():
    if "user" in session:
        try:
            conn = sqlite3.connect('history.db')
            c = conn.cursor()
            c.execute('SELECT count(*) FROM history WHERE username = ?', (session['user'],))
            count = c.fetchone()[0]
            conn.close()
        except:
            count = 0
            
        score = count * 25
        if score < 50:
            badge = "🔍 Novice Sleuth"
        elif score < 150:
            badge = "🛡️ Truth Seeker"
        else:
            badge = "👑 Master Debunker"
            
        return dict(skeptic_score=score, user_badge=badge)
    return dict(skeptic_score=0, user_badge="")
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

@app.route("/premium")
def premium():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("premium.html", user=session["user"])

@app.route("/sources")
def sources():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("sources.html", user=session["user"])

@app.route("/profile")
def profile():
    if "user" not in session:
        return redirect(url_for("login"))
        
    conn = sqlite3.connect('history.db')
    c = conn.cursor()
    c.execute('SELECT count(*) FROM history WHERE username = ?', (session['user'],))
    total_claims = c.fetchone()[0]
    conn.close()
    
    return render_template("profile.html", user=session["user"], total_claims=total_claims)

@app.route("/settings")
def settings():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("settings.html", user=session["user"])

# ---------------- ANALYZE ----------------
@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json()
    if not data or 'claim' not in data:
        return jsonify({"error": "No claim provided."}), 400

    claim = data['claim']

    # Intelligent Reasoning + Rewrite logic using OpenAI
    try:
        prompt = f"""
        You are a world-class investigative journalist and expert fact-checker. Your job is to thoroughly analyze the following claim for its factual accuracy.
        
        Claim: "{claim}"
        
        Your analysis must include:
        1. A 'fake_percentage' from 0 (completely verifiable truth) to 100 (complete fabrication or wildly misleading).
        2. A 'reason': A rigorous, highly-detailed paragraph explaining exactly what makes this claim true, false, or misleading. Reference general historical facts, logical fallacies, or missing context. Do not be vague; be specific and authoritative.
        3. A 'rewrite': A concise, factual, and neutral correction or contextualization of the claim that represents the objective truth.
        4. A 'metrics' object with scores from 0 to 100 for 'political_bias', 'emotional_sensationalism', 'clickbait_severity', and 'logical_fallacy'.
        """
        
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            response_format={ "type": "json_object" },
            messages=[
                {"role": "system", "content": "You are a helpful assistant designed to output strictly in JSON. You must return EXACTLY the following JSON structure: { \"fake_percentage\": <integer>, \"reason\": \"<detailed string>\", \"rewrite\": \"<concise factual string>\", \"metrics\": {\"political_bias\": <integer>, \"emotional_sensationalism\": <integer>, \"clickbait_severity\": <integer>, \"logical_fallacy\": <integer>} }"},
                {"role": "user", "content": prompt}
            ]
        )
        
        response_text = response.choices[0].message.content
        analysis = json.loads(response_text)
        
        fake_percentage = int(analysis.get("fake_percentage", 50))
        reason = analysis.get("reason", "Analysis generated reasoning.")
        rewrite = analysis.get("rewrite", "Analysis factual truth.")
        metrics = analysis.get("metrics", {
            "political_bias": 50,
            "emotional_sensationalism": 50,
            "clickbait_severity": 50,
            "logical_fallacy": 50
        })
    except Exception as e:
        print("OpenAI API Error:", e, flush=True)
        # Fallback if OpenAI fails or rate limits
        fake_percentage = 50
        reason = f"This claim could not be analyzed due to an error: {str(e)}"
        rewrite = "Please try again later or check manually."
        metrics = {
            "political_bias": 0,
            "emotional_sensationalism": 0,
            "clickbait_severity": 0,
            "logical_fallacy": 0
        }

    # Save to DB
    new_score = 0
    new_badge = ""
    try:
        conn = sqlite3.connect('history.db')
        c = conn.cursor()
        # Save string risk just for DB compatibility for now, or update it
        risk_str = f"{fake_percentage}% FAKE"
        c.execute('INSERT INTO history (username, claim, risk, reason, rewrite) VALUES (?, ?, ?, ?, ?)',
                  (session.get('user', 'Anonymous'), claim, risk_str, reason, rewrite))
        conn.commit()
        
        c.execute('SELECT count(*) FROM history WHERE username = ?', (session.get('user', 'Anonymous'),))
        count = c.fetchone()[0]
        conn.close()
        
        new_score = count * 25
        if new_score < 50:
            new_badge = "🔍 Novice Sleuth"
        elif new_score < 150:
            new_badge = "🛡️ Truth Seeker"
        else:
            new_badge = "👑 Master Debunker"
    except Exception as db_err:
        print("DB Error:", db_err)

    return jsonify({
        "fake_percentage": fake_percentage,
        "reason": reason,
        "rewrite": rewrite,
        "metrics": metrics,
        "new_score": new_score,
        "new_badge": new_badge
    })

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)