FROM python:3.11-slim

WORKDIR /app

COPY algorytm1.py .

RUN pip install --no-cache-dir numpy

CMD ["python", "algorytm1.py"]
