from flask import Flask, jsonify
import os
import sys
import traceback

application = Flask(__name__)

# --- DIAGNOSTIC MODE ---
# We wrap the "Dangerous" imports in a Try/Catch block.
# If they fail, the website will load and tell us WHY, instead of giving a 502.

setup_errors = ""

try:
    # 1. Try importing dependencies
    from flask_sqlalchemy import SQLAlchemy
    from apscheduler.schedulers.background import BackgroundScheduler
    import tempfile
    from datetime import datetime
    
    # 2. Try importing your local file
    import background_jobs

    # 3. Try setting up the Database
    tmp_dir = tempfile.gettempdir()
    db_path = os.path.join(tmp_dir, 'crypto_hype.db')
    application.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    application.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db = SQLAlchemy(application)
    
    class CryptoMetric(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        timestamp = db.Column(db.DateTime, default=datetime.utcnow)
        coin_name = db.Column(db.String(50))
        price_usd = db.Column(db.Float)
        hype_score = db.Column(db.Integer)

    with application.app_context():
        db.create_all()

    # 4. Try setting up the Scheduler
    def run_scraper():
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
            except Exception as e:
                print(f"Scheduler Error: {e}")

    if not application.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        scheduler = BackgroundScheduler()
        scheduler.add_job(func=run_scraper, trigger="interval", seconds=60)
        scheduler.start()

except Exception:
    # CAPTURE THE CRASH
    setup_errors = traceback.format_exc()


# --- ROUTES ---

@application.route('/')
def dashboard():
    # If the app crashed during startup, SHOW THE ERROR
    if setup_errors:
        return f"""
        <h1>⚠️ App Crashed on Startup</h1>
        <pre style="background: #eee; padding: 20px; border: 1px solid red;">{setup_errors}</pre>
        """
    
    # Otherwise, show the normal dashboard
    from flask import render_template
    return render_template('dashboard.html')

@application.route('/api/data')
def get_data():
    if setup_errors:
        return jsonify({"error": "App crashed", "details": setup_errors}), 500
        
    try:
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