FROM python:2.7

WORKDIR /app

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY task_executor.py .

CMD ["python", "task_executor.py"]
