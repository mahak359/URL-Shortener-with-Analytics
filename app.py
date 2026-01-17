import string
import random
import re
from flask import Flask, render_template, request, redirect, flash, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///urls.db'
app.config['SECRET_KEY'] = 'your_secret_key_here'
db = SQLAlchemy(app)

# Updated Database Model
class URLMap(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    original_url = db.Column(db.String(500), nullable=False)
    short_code = db.Column(db.String(10), unique=True, nullable=False)
    clicks = db.Column(db.Integer, default=0)  # NEW: Click tracker
    created_at = db.Column(db.DateTime, default=datetime.utcnow) # NEW: Timestamp

def generate_short_code():
    characters = string.ascii_letters + string.digits
    while True:
        code = ''.join(random.choices(characters, k=5))
        if not URLMap.query.filter_by(short_code=code).first():
            return code

def is_valid_url(url):
    regex = re.compile(
        r'^https?://'
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
        r'localhost|'
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
        r'(?::\d+)?'
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return re.match(regex, url) is not None

@app.route('/', methods=['GET', 'POST'])
def home():
    short_url = None
    if request.method == 'POST':
        original = request.form.get('url')
        # Use an empty string as a default if 'custom_code' is missing
        custom_code = request.form.get('custom_code', '').strip()# NEW: Custom Alias input
        
        if not is_valid_url(original):
            flash("Please enter a valid URL (include http:// or https://)", "danger")
        else:
            # Handle Custom Alias or Generate Random
            if custom_code:
                existing_code = URLMap.query.filter_by(short_code=custom_code).first()
                if existing_code:
                    flash("That custom alias is already taken. Try another!", "warning")
                    return render_template('home.html')
                code = custom_code
            else:
                code = generate_short_code()

            # Save to DB
            new_url = URLMap(original_url=original, short_code=code)
            db.session.add(new_url)
            db.session.commit()
            short_url = request.host_url + code
            
    return render_template('home.html', short_url=short_url)

@app.route('/history')
def history():
    urls = URLMap.query.order_by(URLMap.created_at.desc()).all()
    return render_template('history.html', urls=urls, host=request.host_url)

@app.route('/<code>')
def redirect_to_url(code):
    url_entry = URLMap.query.filter_by(short_code=code).first_or_404()
    
    # NEW: Increment Click Counter
    url_entry.clicks += 1
    db.session.commit()
    
    return redirect(url_entry.original_url)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)