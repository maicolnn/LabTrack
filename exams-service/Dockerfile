FROM python:3.10-alpine
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PORT=5002
EXPOSE 5002
CMD ["python", "app.py"]
