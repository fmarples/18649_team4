FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && useradd --uid 10001 --create-home app
COPY . .
USER 10001
CMD ["gunicorn", "--bind=0.0.0.0:8000", "--workers=1", "--threads=4", "app:create_app()"]
