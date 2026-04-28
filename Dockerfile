FROM python:3.11-slim

# התקנת תלויות מערכת ל-Playwright/Chromium
RUN apt-get update && apt-get install -y \
    wget curl gnupg ca-certificates \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libxkbcommon0 libxcomposite1 \
    libxdamage1 libxfixes3 libxrandr2 libgbm1 \
    libpango-1.0-0 libcairo2 libasound2 \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# התקנת ספריות Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# התקנת Chromium
RUN playwright install chromium

# העתקת קוד הבוט
COPY . .

# יצירת תיקיית נתונים
RUN mkdir -p data

EXPOSE 8080
ENV PYTHONUNBUFFERED=1
CMD ["python", "-u", "app.py"]
