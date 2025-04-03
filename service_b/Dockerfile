FROM python:2.7

WORKDIR /app

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY app.py .

EXPOSE 5002

CMD ["python", "app.py"]
