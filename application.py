from flask import Flask, render_template, jsonify
from flask_sqlalchemy import SQLAlchemy
from apscheduler.schedulers.background import BackgroundScheduler
import os
from datetime import datetime
import background_jobs  # We will write this next

application = Flask(__name__)

# --- DATABASE CONFIGURATION ---
# Use AWS RDS if available, otherwise use a local file (sqlite)
# This is the "Hard" part: Persistence
db_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'crypto_hype.db')
application.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
application.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(application)

# --- THE DATABASE MODEL ---
class CryptoMetric(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    coin_name = db.Column(db.String(50))
    price_usd = db.Column(db.Float)
    hype_score = db.Column(db.Integer) # 0 to 100 sentiment score

# Create the database tables if they don't exist
with application.app_context():
    db.create_all()

# --- THE BACKGROUND WORKER ---
# This runs the scraper every 60 seconds automatically
def run_scraper():
    with application.app_context():
        # 1. Get Data (from our logic file)
        data = background_jobs.fetch_crypto_data()
        
        # 2. Save to Database
        new_entry = CryptoMetric(
            coin_name=data['coin'],
            price_usd=data['price'],
            hype_score=data['hype']
        )
        db.session.add(new_entry)
        db.session.commit()
        print(f"✅ Data Saved: {data}")

# Start the scheduler
if not application.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=run_scraper, trigger="interval", seconds=60)
    scheduler.start()

# --- ROUTES ---
@application.route('/')
def dashboard():
    return render_template('dashboard.html')

@application.route('/api/data')
def get_data():
    # Fetch the last 50 data points for the graph
    results = CryptoMetric.query.order_by(CryptoMetric.timestamp.desc()).limit(50).all()
    
    # Format for JSON
    data = [{
        'time': r.timestamp.strftime('%H:%M:%S'),
        'price': r.price_usd,
        'hype': r.hype_score
    } for r in reversed(results)] # Reverse so graph goes Left -> Right
    
    return jsonify(data)

if __name__ == '__main__':
    application.run(port=8080)