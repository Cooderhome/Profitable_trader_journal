from app import create_app
from app.extensions import db
from app.models import User, BacktestEntry, KPISummary

app = create_app()

# Create DB and tables if they don't exist (dev convenience)
with app.app_context():
    db.create_all()

if __name__ == "__main__":
    # Debug on by default for development
    app.run(debug=True, host="127.0.0.1", port=5000)
