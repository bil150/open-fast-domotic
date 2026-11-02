# The API: the Python server alone (the client is the other image).
# Context: this folder (server/), in the repository as well as in build/.
FROM python:3.12-slim
WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Configuration (paths, dongle...) comes from the environment: see docker-compose.yml and .env.example.
VOLUME /data
EXPOSE 8000
CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
