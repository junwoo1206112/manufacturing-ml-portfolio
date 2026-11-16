FROM python:3.12-slim

WORKDIR /app

COPY requirements-tested.txt .
RUN pip install --no-cache-dir -r requirements-tested.txt

COPY . .

EXPOSE 5000

CMD ["python", "main.py"]
