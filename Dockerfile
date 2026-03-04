FROM python:3.11-bookworm
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends build-essential libgomp1 && rm -rf /var/lib/apt/lists/*
COPY req.txt /app/req.txt
RUN pip install --no-cache-dir -r /app/req.txt
COPY . /app
RUN mkdir -p /app/uploads /app/instance
ENV FLASK_ENV=production
ENV PYTHONPATH=/app
EXPOSE 5000
CMD ["python", "app.py"]
