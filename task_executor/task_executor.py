import json
import threading

import pika
import requests
import urllib3

RABBITMQ_HOST = "rabbitmq"
TASK_QUEUE = "equipment_tasks"
RESULT_QUEUE = "equipment_results"
SERVICE_A_URL = "https://service_a:5001/api/v1/equipment/cpe/"

# Disable warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def publish_result(result):
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host=RABBITMQ_HOST, connection_attempts=10, retry_delay=5)
    )
    channel = connection.channel()
    channel.queue_declare(queue=RESULT_QUEUE, durable=True)
    message = json.dumps(result)
    channel.basic_publish(
        exchange="", routing_key=RESULT_QUEUE, body=message, properties=pika.BasicProperties(delivery_mode=2)
    )
    connection.close()


def process_task(channel, method, properties, body):
    task = None
    try:
        task = json.loads(body)
        equipment_id = task.get("equipmentID")
        parameters = task.get("parameters")
        task_id = task.get("taskID", "unknown")
        url = SERVICE_A_URL + equipment_id

        response = requests.post(url, json=parameters, verify=False, timeout=parameters.get("timeoutInSeconds", 14))

        if response.status_code == 200:
            result = {"taskID": task_id, "status": "completed", "result": response.json()}
        else:
            result = {"taskID": task_id, "status": "failed", "result": response.json()}
    except Exception as e:
        task_id = task.get("taskID", "unknown") if task is not None else "unknown"
        result = {
            "taskID": task_id,
            "status": "failed",
            "result": {"code": 500, "message": "Internal provisioning exception", "error": str(e)},
        }

    publish_result(result)
    channel.basic_ack(delivery_tag=method.delivery_tag)


def worker():
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host=RABBITMQ_HOST, connection_attempts=10, retry_delay=5)
    )
    channel = connection.channel()
    channel.queue_declare(queue=TASK_QUEUE, durable=True)
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=TASK_QUEUE, on_message_callback=process_task)
    channel.start_consuming()


if __name__ == "__main__":
    num_workers = 2
    threads = []
    for i in range(num_workers):
        t = threading.Thread(target=worker)
        t.start()
        threads.append(t)
    for t in threads:
        t.join()
