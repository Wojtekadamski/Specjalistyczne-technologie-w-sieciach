# Używamy lekkiej wersji Pythona 3.11 (stabilna, ma wszystkie paczki)
FROM python:3.11-slim

# Ustawiamy katalog roboczy w kontenerze
WORKDIR /app

# Instalujemy potrzebne biblioteki systemowe (na wszelki wypadek)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Kopiujemy plik z wymaganiami i instalujemy biblioteki
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kopiujemy resztę plików (skrypt)
COPY . .

# Tworzymy folder na wyniki (wykresy)
RUN mkdir -p results

# Domyślna komenda po uruchomieniu
CMD ["python", "algorytm_global_2.py"]