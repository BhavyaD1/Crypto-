from flask import Flask, render_template, jsonify
from flask_sqlalchemy import SQLAlchemy
from apscheduler.schedulers.background import BackgroundScheduler
import os
import tempfile
from datetime import datetime
import background_jobs  # Your simulation/scraper logic

application = Flask(__name__)

# --- 1. DATABASE CONFIGURATION ---
# We use the system temp folder to avoid "Read Only" errors on AWS
tmp_dir = tempfile.gettempdir()
db_path = os.path.join(tmp_dir, 'crypto_hype.db')
application.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
application.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(application)

# --- 2. DATABASE MODEL ---
class CryptoMetric(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    coin_name = db.Column(db.String(50))
    price_usd = db.Column(db.Float)
    hype_score = db.Column(db.Integer)

# Initialize Database
with application.app_context():
    db.create_all()

# --- 3. THE TURBO WORKER ---
def run_scraper():
    """ Runs automatically to fetch data """
    with application.app_context():
        try:
            data = background_jobs.fetch_crypto_data()
            
            new_entry = CryptoMetric(
                coin_name=data['coin'],
                price_usd=data['price'],
                hype_score=data['hype']
            )
            db.session.add(new_entry)
            db.session.commit()
            print(f"⚡ TURBO MODE: Data Saved {data}")
        except Exception as e:
            print(f"Worker Error: {e}")

# Start Scheduler - Runs every 10 SECONDS now (was 60)
if not application.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
    scheduler = BackgroundScheduler()
    # CHANGED: seconds=10 (Much faster updates)
    scheduler.add_job(func=run_scraper, trigger="interval", seconds=10)
    scheduler.start()

# --- 4. ROUTES ---
@application.route('/')
def dashboard():
    return render_template('dashboard.html')

@application.route('/api/data')
def get_data():
    try:
        # Fetch last 50 points
        results = CryptoMetric.query.order_by(CryptoMetric.timestamp.desc()).limit(50).all()
        
        data = [{
            'time': r.timestamp.strftime('%H:%M:%S'),
            'price': r.price_usd,
            'hype': r.hype_score
        } for r in reversed(results)]
        
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    application.run(port=8080)