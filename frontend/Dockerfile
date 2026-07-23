FROM python:3.10-alpine
WORKDIR /app
COPY frontend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY frontend/app.py .
COPY app/templates ./app/templates
COPY app/static ./app/static
ENV PORT=5004
EXPOSE 5004
CMD ["python", "app.py"]
