# Rebuild
# 1. نبدأ من صورة بايثون 3.11 الرسمية
FROM python:3.10-slim

# 2. نحدد مجلد العمل داخل البيئة
WORKDIR /app

# 3. نقوم بتحديث الحزم وتثبيت ffmpeg و git (مهم جداً)
RUN apt-get update && apt-get install -y ffmpeg git

# 4. ننسخ ملف المكتبات ونقوم بتثبيتها
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. ننسخ كل ملفات البوت إلى بيئة العمل
COPY . .

# 6. نحدد الأمر الذي سيتم تشغيله عند بدء التشغيل
CMD ["python", "main.py"]
