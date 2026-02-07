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

# ใช้ชื่อรุ่นที่ระบุรหัสชัดเจน (เสถียรที่สุด)
model_name = 'gemini-1.5-flash'
model = genai.GenerativeModel(model_name)

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
        if "," in image_data:
            image_data = image_data.split(",")[1]
        image_data = image_data.replace(' ', '+')
        missing_padding = len(image_data) % 4
        if missing_padding:
            image_data += '=' * (4 - missing_padding)
        # =======================================

        # 2. แปลงรูปภาพ
        try:
            image_bytes = base64.b64decode(image_data)
            image = Image.open(io.BytesIO(image_bytes))
        except Exception as img_err:
            return "Error|0|Image Corrupted"

        # 3. สั่ง Gemini
        prompt = f"""
        You are a sourdough expert. Analyze this image of a starter.
        Current Environment: Temperature {temp}°C, Humidity {hum}%.
        
        Strictly return the response in this format ONLY (use pipe '|' separator):
        Status|TimeRemaining(mins)|ShortAdvice

        Status options: 'Feeding Needed', 'Rising', 'Peak/Ready', 'Over-fermented', 'Moldy/Bad'.
        TimeRemaining: Estimate minutes until ready (put 0 if ready or bad).
        ShortAdvice: One short sentence advice.
        """
        
        try:
            response = model.generate_content([prompt, image])
            text_response = response.text.strip()
            text_response = text_response.replace('```', '').replace('python', '').strip()
            print(f"AI Says: {text_response}")
            return text_response
            
        except Exception as api_err:
            # 🚨 ถ้ายัง Error เรื่องชื่อรุ่น ให้ลองค้นหาชื่อรุ่นที่มีอยู่จริง
            error_str = str(api_err)
            if "404" in error_str or "not found" in error_str:
                print("Model not found, listing available models...")
                available = []
                for m in genai.list_models():
                    if 'generateContent' in m.supported_generation_methods:
                        available.append(m.name)
                # ส่งรายชื่อรุ่นกลับไปโชว์ที่หน้าจอ ESP32 เลย จะได้รู้ว่าควรใช้อันไหน
                suggested_models = ", ".join(available[:2]) # เอามาแค่ 2 อันแรก
                return f"Model Error|0|Try using: {suggested_models}"
            else:
                raise api_err

    except Exception as e:
        print(f"System Error: {str(e)}")
        return f"System Error|0|{str(e)}"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)



