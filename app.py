import os
import requests
import base64
import traceback
from flask import Flask, request

app = Flask(__name__)

# ================= CONFIG =================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
LINE_CHANNEL_TOKEN = os.environ.get("LINE_CHANNEL_TOKEN")
LINE_USER_ID = os.environ.get("LINE_USER_ID")

# ใช้เฉพาะโมเดลฟรีที่ชัวร์
GEMINI_MODEL = "gemini-2.5-flash"

# เก็บสถานะล่าสุด กันแจ้งซ้ำ
last_status = None
# =========================================


# ================= LINE ===================
def send_line(msg: str):
    if not LINE_CHANNEL_TOKEN or not LINE_USER_ID:
        print("LINE config missing")
        return

    try:
        requests.post(
            "https://api.line.me/v2/bot/message/push",
            headers={
                "Authorization": f"Bearer {LINE_CHANNEL_TOKEN}",
                "Content-Type": "application/json"
            },
            json={
                "to": LINE_USER_ID,
                "messages": [{"type": "text", "text": msg}]
            },
            timeout=5
        )
    except Exception as e:
        print("LINE error:", e)
# =========================================


@app.route("/")
def home():
    return "🍞 Sourdough Brain Running"


# ====== ใช้ทดสอบ LINE โดยไม่ต้อง ESP32 ======
@app.route("/test-line")
def test_line():
    send_line("✅ LINE notification works!")
    return "ok"


# ================= ANALYZE =================
@app.route("/analyze", methods=["POST"])
def analyze():
    global last_status

    print("\n--- New Analyze Request ---")

    if not GEMINI_API_KEY:
        return "Error|0|NoGeminiKey"

    if "imageFile" not in request.files:
        return "Error|0|NoImage"

    try:
        # --- เตรียมรูป ---
        img = request.files["imageFile"]
        img_b64 = base64.b64encode(img.read()).decode()

        url = (
            f"https://generativelanguage.googleapis.com/v1beta/"
            f"models/{GEMINI_MODEL}:generateContent"
            f"?key={GEMINI_API_KEY}"
        )

        payload = {
            "contents": [{
                "role": "user",
                "parts": [
                    {
                        "text": (
                            "Analyze sourdough starter image.\n"
                            "Return STRICTLY ONE LINE ONLY:\n"
                            "Status|Time(mins)|Advice\n"
                            "Status must be one of: Ready, Peak, Hungry, Moldy\n"
                            "Example: Ready|0|Bake now\n"
                            "Do not add any extra text."
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

        resp = requests.post(url, json=payload, timeout=30)

        # --- Quota หมด ---
        if resp.status_code == 429:
            print("Gemini quota exceeded")
            return "Error|0|GeminiQuota"

        data = resp.json()

        if "error" in data:
            print("Gemini error:", data["error"])
            return "Error|0|GeminiError"

        result = (
            data["candidates"][0]["content"]["parts"][0]["text"]
            .strip()
            .replace("\n", "")
            .replace("*", "")
        )

        print("Gemini result:", result)

        # --- แยกสถานะ ---
        status = result.split("|")[0] if "|" in result else "Unknown"

        # --- แจ้ง LINE เฉพาะตอนสถานะเปลี่ยน และเป็นสถานะสำคัญ ---
        if status in ["Ready", "Peak", "Moldy", "Hungry"] and status != last_status:
            send_line(f"{result}\n")
            last_status = status

        return result

    except Exception:
        print(traceback.format_exc())
        return "Error|0|ServerError"
# =========================================


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
