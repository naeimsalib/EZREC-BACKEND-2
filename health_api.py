from flask import Flask, jsonify, abort
import os
import json

app = Flask(__name__)

HEALTH_PATH = "/opt/ezrec-backend/health_report.json"

@app.route("/health")
def health():
    if not os.path.exists(HEALTH_PATH):
        abort(503, description="Health report not available")
    try:
        with open(HEALTH_PATH) as f:
            data = json.load(f)
        return jsonify(data)
    except Exception:
        abort(503, description="Health report invalid")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080) 