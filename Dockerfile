FROM python:3.11-slim

# Tizimga kerakli kutubxonalarni o'rnatamiz (OpenSSL, ICU va h.k.)
RUN apt-get update && apt-get install -y \
    libgdiplus \
    libicu-dev \
    libssl-dev \
    libgl1-desktop \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

RUN pip install --no-cache-dir -r requirements.txt

# .env o'rniga Railway variables ishlatiladi
ENV DOTNET_SYSTEM_GLOBALIZATION_INVARIANT=1

CMD ["python", "Pdf.py"]
