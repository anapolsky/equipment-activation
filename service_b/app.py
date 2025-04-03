import json
import re
import threading
import time
import uuid

import pika
from flask import Flask, request, jsonify

app = Flask(__name__)

EQUIPMENT_ID_REGEX = re.compile(r"^[a-zA-Z0-9]{6,}$")

# {task_id: {"equipmentID": ..., "parameters": ..., "status": "running"/"completed"/"failed", "result": {...}}}
task_store = {}

RABBITMQ_HOST = "rabbitmq"
TASK_QUEUE = "equipment_tasks"
RESULT_QUEUE = "equipment_results"


def publish_task(task):
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host=RABBITMQ_HOST, connection_attempts=10, retry_delay=5)
    )
    channel = connection.channel()
    channel.queue_declare(queue=TASK_QUEUE, durable=True)
    message = json.dumps(task)
    channel.basic_publish(
        exchange="", routing_key=TASK_QUEUE, body=message, properties=pika.BasicProperties(delivery_mode=2)
    )
    connection.close()


def result_consumer():
    def callback(c, method, properties, body):
        try:
            result = json.loads(body)
            task_id = result.get("taskID")
            if task_id in task_store:
                task_store[task_id]["status"] = result.get("status", "completed")
                task_store[task_id]["result"] = result
        except Exception as e:
            print("Error processing result: {}".format(e))
        c.basic_ack(delivery_tag=method.delivery_tag)

    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host=RABBITMQ_HOST, connection_attempts=10, retry_delay=5)
    )
    channel = connection.channel()
    channel.queue_declare(queue=RESULT_QUEUE, durable=True)
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=RESULT_QUEUE, on_message_callback=callback)
    channel.start_consuming()


t = threading.Thread(target=result_consumer)
t.daemon = True
t.start()


@app.route("/api/v1/equipment/cpe/<string:equipment_id>", methods=["POST"])
def create_configuration_task(equipment_id):
    if not EQUIPMENT_ID_REGEX.match(equipment_id):
        return jsonify({"code": 404, "message": "The requested equipment is not found"}), 404

    data = request.get_json()
    if not data or "timeoutInSeconds" not in data or "parameters" not in data:
        return jsonify({"code": 400, "message": "Bad Request"}), 400

    task_id = str(uuid.uuid4())
    task = {
        "taskID": task_id,
        "equipmentID": equipment_id,
        "parameters": data,
        "timestamp": time.time(),
        "status": "running",
    }
    task_store[task_id] = task

    publish_task(task)

    return jsonify({"code": 200, "taskID": task_id}), 200


@app.route("/api/v1/equipment/cpe/<string:equipment_id>/task/<string:task_id>", methods=["GET"])
def check_task_status(equipment_id, task_id):
    if not EQUIPMENT_ID_REGEX.match(equipment_id):
        return jsonify({"code": 404, "message": "The requested equipment is not found"}), 404

    task = task_store.get(task_id)
    if not task or task.get("equipmentID") != equipment_id:
        return jsonify({"code": 404, "message": "The requested task is not found"}), 404

    if task["status"] == "running":
        return jsonify({"code": 204, "message": "Task is still running"}), 204
    else:
        return jsonify({"code": 200, "message": "Completed", "result": task.get("result", {})}), 200


if __name__ == "__main__":
    app.run(ssl_context="adhoc", host="0.0.0.0", port=5002)
