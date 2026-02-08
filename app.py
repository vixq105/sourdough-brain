import os
from flask import Flask, request
import google.generativeai as genai
from PIL import Image
import io
import base64
import traceback

# ====================================================
# เปลี่ยนวิธีเรียก Key: ดึงจากตู้เซฟของ Render แทน (ปลอดภัย 100%)
GENAI_API_KEY = os.environ.get("GENAI_API_KEY")
# ====================================================

genai.configure(api_key=GENAI_API_KEY)

# ใช้รุ่นนี้ตามที่ระบบแนะนำ
model_name = 'models/gemini-2.5-flash'

app = Flask(__name__)

@app.route('/', methods=['GET'])
def home():
    return "Sourdough AI Brain is Running!"

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        print("--- Start Request ---")
        
        # เช็คว่ามี Key หรือยัง
        if not GENAI_API_KEY:
            return "Config Error|0|API Key missing in Render Env"

        image_data = request.form.get('image')
        temp = request.form.get('temp', '25')
        hum = request.form.get('hum', '60')

        if not image_data:
            return "Error|0|No Image Sent"

        # แปลงรูปภาพ
        try:
            if "," in image_data:
                image_data = image_data.split(",")[1]
            image_data = image_data.replace(' ', '+')
            missing_padding = len(image_data) % 4
            if missing_padding:
                image_data += '=' * (4 - missing_padding)
            
            image_bytes = base64.b64decode(image_data)
            image = Image.open(io.BytesIO(image_bytes))
        except Exception as e:
            print(f"Image Error: {e}")
            return f"Error|0|Image Corrupted"

        try:
            model = genai.GenerativeModel(model_name)
        except Exception as e:
             return f"Error|0|Model Setup Fail"

        # สั่ง Gemini ให้วิเคราะห์ (เวอร์ชันใหม่ บังคับตอบสั้น)
        prompt = f"""
        You are a sourdough expert. Analyze this image of a starter.
        Current Environment: Temperature {temp}°C, Humidity {hum}%.
        
        Strictly return the response in this format ONLY (use pipe '|' separator):
        Status|TimeRemaining(mins)|ShortAdvice

        Status options: 'Feeding Needed', 'Rising', 'Peak/Ready', 'Over-fermented', 'Moldy/Bad'.
        TimeRemaining: Estimate minutes until ready (put 0 if ready or bad).
        ShortAdvice: ONE SHORT SENTENCE. Max 6 words. No symbols.
        """
        
        print(f"Sending to model: {model_name}")
        response = model.generate_content([prompt, image])
        text_response = response.text.strip()
        
        text_response = text_response.replace('```', '').replace('python', '').replace('text', '').strip()
        
        if "|" not in text_response:
            print(f"AI Format Error: {text_response}")
            # ถ้า AI ตอบผิดฟอร์ม ให้พยายามดึงคำตอบออกมา
            return f"AI Error|0|{text_response[:50]}"

        print(f"AI Says: {text_response}")
        return text_response

    except Exception as e:
        error_msg = str(e)
        print(f"CRITICAL ERROR: {traceback.format_exc()}")
        
        if "403" in error_msg:
            return "Key Error|0|API Key Invalid or Leaked"
        if "404" in error_msg:
            return "Model Error|0|Model not found"
        if "429" in error_msg:
            return "Quota Error|0|Too many requests"
            
        return f"Sys Error|0|Check Logs"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)


