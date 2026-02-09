from flask import Flask, request, jsonify, render_template_string
from datetime import datetime
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Allow cross-origin requests

# In-memory alert store (for demo)
ALERTS = []
MAX_ALERTS = 100  # Keep last 100 alerts only

# ------------------------
# Health Check
# ------------------------
@app.route("/", methods=["GET"])
def health():
    return {"status": "Fraud Alert Service Running"}, 200

# ------------------------
# Receive Fraud Alert
# ------------------------
@app.route("/fraud-alert", methods=["POST"])
def fraud_alert():
    data = request.json
    if not data or "userId" not in data:
        return jsonify({"status": "error", "message": "Invalid payload"}), 400

    alert = {
        "userId": data["userId"],
        "name": data.get("name", "Unknown"),
        "countries": data.get("countries", []),
        "severity": data.get("severity", "CRITICAL"),
        "time": datetime.utcnow().isoformat() + "Z"
    }

    ALERTS.append(alert)
    if len(ALERTS) > MAX_ALERTS:
        ALERTS.pop(0)  # Remove oldest

    print("🚨 FRAUD ALERT 🚨", alert)
    return jsonify({"status": "received"}), 200

# ------------------------
# Alerts Dashboard (HTML)
# ------------------------
@app.route("/alerts", methods=["GET"])
def alerts_page():
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Fraud Alerts Dashboard</title>
        <meta http-equiv="refresh" content="10">  <!-- Auto-refresh every 10s -->
        <style>
            body { font-family: Arial, sans-serif; background: #0f172a; color: #e5e7eb; padding: 20px; }
            h1 { color: #f87171; }
            table { width: 100%; border-collapse: collapse; margin-top: 20px; }
            th, td { padding: 12px; border-bottom: 1px solid #334155; text-align: left; }
            th { background: #1e293b; }
            tr:hover { background: #1e293b; }
            .severity { color: #ef4444; font-weight: bold; }
            .empty { margin-top: 20px; color: #94a3b8; }
        </style>
    </head>
    <body>
        <h1>🚨 Fraud Alerts</h1>
        {% if alerts %}
        <table>
            <tr>
                <th>Time</th>
                <th>User ID</th>
                <th>Name</th>
                <th>Countries</th>
                <th>Severity</th>
            </tr>
            {% for a in alerts %}
            <tr>
                <td>{{ a.time }}</td>
                <td>{{ a.userId }}</td>
                <td>{{ a.name }}</td>
                <td>{{ a.countries | join(", ") }}</td>
                <td class="severity">{{ a.severity }}</td>
            </tr>
            {% endfor %}
        </table>
        {% else %}
        <div class="empty">No fraud alerts yet.</div>
        {% endif %}
    </body>
    </html>
    """
    return render_template_string(html, alerts=ALERTS)

# ------------------------
# Alerts API (JSON)
# ------------------------
@app.route("/alerts/json", methods=["GET"])
def alerts_json():
    return jsonify({"alerts": ALERTS}), 200


if __name__ == "__main__":
    app.run(port=5000, debug=True)
