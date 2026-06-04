FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py db.py type_calc.py ./
COPY templates/ ./templates/
COPY static/css ./static/css/
COPY static/js ./static/js/
COPY static/logo.png ./static/logo.png

COPY data/ ./data/
COPY static/sprites/ ./static/sprites/

COPY fetch_data.py fetch_sprites.py ./

COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

EXPOSE 5000

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["python", "app.py"]
