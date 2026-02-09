from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from datetime import datetime

app = Flask(__name__)
CORS(app)

# ------------------------
# In-memory alert store
# ------------------------
ALERTS = []
MAX_ALERTS = 100


# ------------------------
# Health Check
# ------------------------
@app.route("/", methods=["GET"])
def health():
    return jsonify({
        "status": "running",
        "service": "Fraud Alert Engine",
        "alerts_loaded": len(ALERTS)
    })

@app.route("/alerts")
def alerts_page():
    alerts = list(reversed(ALERTS))  # IMPORTANT
    return render_template("alerts.html", alerts=alerts)

# ------------------------
# Receive Fraud Alert (API)
# ------------------------
@app.route("/fraud-alert", methods=["POST"])
def fraud_alert():
    data = request.json

    if not data or "userId" not in data:
        return jsonify({"error": "Invalid payload"}), 400

    alert = {
        "userId": data["userId"],
        "name": data.get("name", "Unknown"),
        "countries": data.get("countries", []),
        "severity": data.get("severity", "HIGH"),
        "reason": data.get("reason", "Rule triggered"),
        "time": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    }

    ALERTS.append(alert)

    if len(ALERTS) > MAX_ALERTS:
        ALERTS.pop(0)

    print("🚨 ALERT RECEIVED:", alert)
    return jsonify({"status": "received"}), 200


# ------------------------
# Dashboard UI
# ------------------------
@app.route("/alerts", methods=["GET"])
def alerts_page():
    return render_template("alerts.html", alerts=reversed(ALERTS))


# ------------------------
# Alerts JSON (for JS / APIs)
# ------------------------
@app.route("/alerts/json", methods=["GET"])
def alerts_json():
    return jsonify({"alerts": ALERTS})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
