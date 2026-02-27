FROM python:3.11-slim

# Kerakli tizim paketlarini o'rnatish
RUN apt-get update && apt-get install -y \
    libgdiplus \
    libicu-dev \
    libssl-dev \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

# Kutubxonalarni o'rnatish
RUN pip install --no-cache-dir -r requirements.txt

# Globalizatsiya xatoligini oldini olish
ENV DOTNET_SYSTEM_GLOBALIZATION_INVARIANT=1

CMD ["python", "Pdf.py"]
