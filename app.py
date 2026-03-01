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

# เก็บสถานะล่าสุด
last_status = None
last_temp = "N/A"  # 📌 [เพิ่มใหม่] ตัวแปรเก็บค่าอุณหภูมิ
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


# ================= DASHBOARD =================
@app.route("/")
def home():
    global last_status, last_temp
    
    # 📌 [เพิ่มใหม่] โค้ดหน้าเว็บ HTML / CSS สวยๆ
    html = f"""
    <!DOCTYPE html>
    <html lang="th">
    <head>
        <meta charset="UTF-8">
        <title>Sourdough Smart Incubator</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <meta http-equiv="refresh" content="60">
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; text-align: center; background-color: #fdf6e3; padding: 40px 20px; color: #333; margin: 0; }}
            .card {{ background: white; padding: 30px; border-radius: 20px; box-shadow: 0 10px 20px rgba(0,0,0,0.08); display: inline-block; max-width: 350px; width: 100%; }}
            h1 {{ color: #d35400; font-size: 26px; margin-bottom: 5px; margin-top: 0; }}
            p.subtitle {{ color: #7f8c8d; margin-top: 0; margin-bottom: 25px; font-size: 14px; }}
            .temp-box {{ background-color: #fff3e0; border-radius: 15px; padding: 20px; margin-bottom: 20px; }}
            .temp-title {{ color: #e67e22; font-size: 14px; font-weight: bold; text-transform: uppercase; letter-spacing: 1px; }}
            .temp {{ font-size: 52px; font-weight: bold; color: #d35400; margin: 5px 0 0 0; }}
            .status-box {{ background-color: #e8f8f5; border-radius: 15px; padding: 20px; }}
            .status-title {{ color: #16a085; font-size: 14px; font-weight: bold; text-transform: uppercase; letter-spacing: 1px; }}
            .status {{ font-size: 24px; font-weight: bold; color: #1abc9c; margin: 5px 0 0 0; }}
            .footer {{ margin-top: 25px; font-size: 12px; color: #bdc3c7; }}
        </style>
    </head>
    <body>
        <div class="card">
            <h1>🍞 Sourdough Brain</h1>
            <p class="subtitle">AI Smart Incubator</p>

            <div class="temp-box">
                <div class="temp-title">อุณหภูมิตู้บ่ม (DHT22)</div>
                <div class="temp">🌡️ {last_temp} °C</div>
            </div>

            <div class="status-box">
                <div class="status-title">สถานะน้องยีสต์</div>
                <div class="status">{last_status if last_status else "Waiting for AI..."}</div>
            </div>

            <div class="footer">Auto-refresh every 60 seconds</div>
        </div>
    </body>
    </html>
    """
    return html
# =========================================


# ====== ใช้ทดสอบ LINE โดยไม่ต้อง ESP32 ======
@app.route("/test-line")
def test_line():
    send_line("✅ LINE notification works!")
    return "ok"


# ================= ANALYZE =================
@app.route("/analyze", methods=["POST"])
def analyze():
    global last_status, last_temp

    print("\n--- New Analyze Request ---")

    # 📌 [เพิ่มใหม่] รับค่าอุณหภูมิที่แนบมากับฟอร์ม
    if "temperature" in request.form:
        last_temp = request.form["temperature"]
        print(f"🌡️ Received Temp: {last_temp} °C")
    else:
        print("⚠️ No temperature data received from ESP32")

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
            
            # แปลงสถานะเป็นข้อความสวยๆ
            if status == "Ready":
                line_msg = f"🍞 Starter is ready!\n🌡️ อุณหภูมิ: {last_temp} °C"
            elif status == "Peak":
                line_msg = f"📈 Starter is at its peak!\n🌡️ อุณหภูมิ: {last_temp} °C"
            elif status == "Hungry":
                line_msg = f"🥣 Starter is hungry!\n🌡️ อุณหภูมิ: {last_temp} °C"
            elif status == "Moldy":
                line_msg = f"⚠️ ระวัง! Starter is moldy!\n🌡️ อุณหภูมิ: {last_temp} °C"
            else:
                line_msg = f"Status: {status}\n🌡️ อุณหภูมิ: {last_temp} °C"

            send_line(line_msg)
            last_status = status

        return result

    except Exception:
        print(traceback.format_exc())
        return "Error|0|ServerError"
# =========================================


if __name__ == "__main__":
    # ให้ดึง Port จาก Render มาใช้ ถ้าไม่มีให้ใช้ 10000 แทน
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
