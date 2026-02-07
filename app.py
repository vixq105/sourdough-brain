import os
from flask import Flask, request
import google.generativeai as genai
from PIL import Image
import io
import base64

# =================ตั้งค่า API KEY ตรงนี้=================
GENAI_API_KEY = "AIzaSyCGk8FcySmCgnrteDdMdSHSWFPIErBvauM" 
# ====================================================

genai.configure(api_key=GENAI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash-latest')

app = Flask(__name__)

@app.route('/', methods=['GET'])
def home():
    return "Sourdough AI Brain is Running!"

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        # 1. รับข้อมูล
        image_data = request.form.get('image')
        temp = request.form.get('temp', '25')
        hum = request.form.get('hum', '60')

        if not image_data:
            return "Error|0|No Image Sent"

        # === 🛠️ ส่วนซ่อมแซมข้อมูล (Auto-Repair) ===
        # ลบหัวกระดาษทิ้งถ้ามี (data:image/jpeg;base64,)
        if "," in image_data:
            image_data = image_data.split(",")[1]
            
        # แก้ไข Space ที่อาจเพี้ยนมาจากการส่ง
        image_data = image_data.replace(' ', '+')

        # เติมเครื่องหมาย = ที่หายไปตอนท้าย (Padding Fix)
        missing_padding = len(image_data) % 4
        if missing_padding:
            image_data += '=' * (4 - missing_padding)
        # =======================================

        # 2. แปลงรหัสกลับเป็นรูปภาพ
        try:
            image_bytes = base64.b64decode(image_data)
            image = Image.open(io.BytesIO(image_bytes))
        except Exception as img_err:
            print(f"Image Decode Error: {img_err}")
            return "Error|0|Image Corrupted"

        # 3. ส่งให้ Gemini ดู
        prompt = f"""
        You are a sourdough expert. Analyze this image of a starter.
        Current Environment: Temperature {temp}°C, Humidity {hum}%.
        
        Strictly return the response in this format ONLY (use pipe '|' separator):
        Status|TimeRemaining(mins)|ShortAdvice

        Status options: 'Feeding Needed', 'Rising', 'Peak/Ready', 'Over-fermented', 'Moldy/Bad'.
        TimeRemaining: Estimate minutes until ready (put 0 if ready or bad).
        ShortAdvice: One short sentence advice.
        """
        
        response = model.generate_content([prompt, image])
        text_response = response.text.strip()
        
        # ล้าง Format ที่ไม่จำเป็น
        text_response = text_response.replace('```', '').replace('python', '').strip()
        
        print(f"AI Says: {text_response}")
        return text_response

    except Exception as e:
        print(f"Server Error: {str(e)}")
        return f"System Error|0|{str(e)}"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)

