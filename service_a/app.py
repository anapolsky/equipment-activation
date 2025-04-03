import re
import time

from flask import Flask, request, jsonify

app = Flask(__name__)

EQUIPMENT_ID_REGEX = re.compile(r"^[a-zA-Z0-9]{6,}$")


@app.route("/api/v1/equipment/cpe/<string:equipment_id>", methods=["POST"])
def configure_equipment(equipment_id):
    if not EQUIPMENT_ID_REGEX.match(equipment_id):
        return jsonify({"code": 404, "message": "The requested equipment is not found"}), 404

    data = request.get_json()
    if not data or "timeoutInSeconds" not in data or "parameters" not in data:
        return jsonify({"code": 400, "message": "Bad Request"}), 400

    time.sleep(60)

    return jsonify({"code": 200, "message": "Success"}), 200


if __name__ == "__main__":
    app.run(ssl_context="adhoc", host="0.0.0.0", port=5001)
