import os
import requests
import base64
import traceback
from flask import Flask, request

app = Flask(__name__)

# ========= CONFIG =========
API_KEY = os.environ.get("GEMINI_API_KEY")
LINE_TOKEN = os.environ.get("LINE_CHANNEL_TOKEN")
LINE_USER = os.environ.get("LINE_USER_ID")

MODELS_TO_TRY = [
    "gemini-1.5-flash"
]

# ========= LINE =========
def send_line(msg):
    if not LINE_TOKEN or not LINE_USER:
        return
    try:
        requests.post(
            "https://api.line.me/v2/bot/message/push",
            headers={
                "Authorization": f"Bearer {LINE_TOKEN}",
                "Content-Type": "application/json"
            },
            json={
                "to": LINE_USER,
                "messages": [{"type": "text", "text": msg}]
            },
            timeout=5
        )
    except:
        pass

# ========= ROUTES =========
@app.route("/")
def home():
    return "Gemini Auto Switcher Running ✅"

@app.route("/analyze", methods=["POST"])
def analyze():
    print("\n--- New Request ---")

    if not API_KEY:
        return "Error|0|Missing API Key"

    if "imageFile" not in request.files:
        return "Error|0|No Image"

    try:
        img = request.files["imageFile"]
        img_b64 = base64.b64encode(img.read()).decode()

        last_error = "Unknown"

        for model in MODELS_TO_TRY:
            print(f"Trying model: {model}")

            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={API_KEY}"

            payload = {
                "contents": [{
                    "role": "user",
                    "parts": [
                        {
                            "text": (
                                "Analyze sourdough starter image.\n"
                                "Return STRICTLY one line:\n"
                                "Status|Time(mins)|Advice\n"
                                "Status must be one of: Ready, Peak, Hungry, Moldy\n"
                                "Example: Ready|0|Bake now"
                            )
                        },
                        {
                            "inline_data": {
                                "mime_type": "image/jpeg",
                                "data": img_b64
                            }
                        }
                    ]
                }]
            }

            r = requests.post(url, json=payload, timeout=20)
            data = r.json()

            if r.status_code != 200:
                print("HTTP", r.status_code, data)
                last_error = data.get("error", {}).get("message", "HTTP error")
                continue

            try:
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                text = text.strip().replace("\n", "").replace("*", "")
                print(f"SUCCESS ({model}):", text)

                if any(x in text for x in ["Ready", "Peak", "Moldy"]):
                    send_line(f"🍞 {model}\n{text}")

                return text
            except Exception:
                last_error = "Bad response format"
                continue

        return f"Error|0|{last_error[:25]}"

    except Exception as e:
        print(traceback.format_exc())
        return f"Error|0|{str(e)[:25]}"

# ========= RUN =========
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)

