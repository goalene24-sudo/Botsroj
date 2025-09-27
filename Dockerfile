# Dockerfile
# استخدام صورة بايثون رسمية وخفيفة
FROM python:3.11-slim

# تعيين مجلد العمل داخل الحاوية
WORKDIR /app

# تحديث وتثبيت أداة ffmpeg الأساسية (هذه هي الخطوة الأهم)
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# نسخ ملف متطلبات بايثون
COPY requirements.txt .

# تثبيت مكتبات بايثون
RUN pip install --no-cache-dir -r requirements.txt

# نسخ جميع ملفات المشروع المتبقية
COPY . .

# الأمر الافتراضي لتشغيل البوت عند بدء التشغيل
CMD ["python", "main.py"]
