import os
import json
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from google import genai

# Load environment variables
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

app = Flask(__name__)

# Configure Gemini API
if api_key:
    client = genai.Client(api_key=api_key)
else:
    client = None

@app.route("/")
def home():
    return render_template("index.html")

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
            model='gemini-2.5-flash',
            contents=prompt,
        )
        # Parse the JSON response
        response_text = response.text.replace('```json', '').replace('```', '').strip()
        result_json = json.loads(response_text)
        
        # Ensure correct keys
        risk = result_json.get("risk", "Medium")
        reason = result_json.get("reason", "Analysis failed.")
        rewrite = result_json.get("rewrite", "No rewrite available.")

        return jsonify({
            "risk": risk,
            "reason": reason,
            "rewrite": rewrite
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error calling Gemini AI: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)