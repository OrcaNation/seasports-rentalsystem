import os

from dotenv import load_dotenv
from flask import Flask, render_template, request, flash, redirect, url_for, session
from pymongo import MongoClient
from datetime import datetime
import pandas as pd

from routes.equipments import equipments_bp
from routes.guests import guests_bp
from routes.rentals import rentals_bp
from routes.finances import finances_bp

load_dotenv()

app = Flask(__name__)


@app.before_request
def require_login():
    allowed_routes = ['login', 'static']  # rotas liberadas sem login
    if request.endpoint not in allowed_routes and not session.get('logged_in'):
        return redirect(url_for('login'))


app.secret_key = os.getenv('SECRET_KEY')
app.config['UPLOAD_FOLDER'] = 'uploads'  # você pode mudar isso
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # limite de 2MB
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# MongoDB connection
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["rental_system"]

app.register_blueprint(guests_bp)
app.register_blueprint(equipments_bp)
app.register_blueprint(rentals_bp)
app.register_blueprint(finances_bp)


@app.route('/')
def home():
    today = datetime.today()

    returns_pending = db.rentals.count_documents({
        "confirmed": True,
        "paid": False,
        "items": {"$elemMatch": {"returned": False}}
    })

    payments_pending = db.rentals.count_documents({
        "confirmed": True,
        "departure_date": {"$gt": today},
        "paid": False
    })

    return render_template('index.html',
                           page="index",
                           returns_pending=returns_pending,
                           payments_pending=payments_pending)


@app.route('/upload_csv', methods=['GET'])
def upload_equipment_csv_form():
    return render_template('upload_csv.html')


@app.route('/upload_equipment_csv', methods=['POST'])
def upload_equipment_csv():
    file_eq = request.files.get('csv_eq_file')
    if not file_eq:
        flash('No equipment file selected', 'danger')
        return redirect(url_for('home'))

    try:
        df = pd.read_csv(file_eq)
        df.columns = df.columns.str.lower()
        df['available'] = df['available'].astype(bool)

        collection = db['equipments']
        inserted_count = 0
        skipped_count = 0

        for _, row in df.iterrows():
            try:
                category = str(row['category']).strip()
                identifier = int(row['identifier'])  # assume que vem como número

                exists = collection.find_one({
                    'category': category,
                    'identifier': identifier
                })

                if exists:
                    skipped_count += 1
                    continue

                equipment = row.to_dict()
                collection.insert_one(equipment)
                inserted_count += 1

            except KeyError as ke:
                flash(f'Missing expected column: {str(ke)}', 'danger')
                return redirect(url_for('home'))

        flash(f'{inserted_count} equipment(s) added. {skipped_count} skipped (already existed).', 'success')

    except Exception as e:
        flash(f'Error uploading equipment CSV: {str(e)}', 'danger')

    return redirect(url_for('home'))


@app.route('/upload_pricelist_csv', methods=['POST'])
def upload_pricelist_csv():
    file_price = request.files.get('csv_price_file')
    if not file_price:
        flash('No price list file selected', 'danger')
        return redirect(url_for('home'))

    try:
        df = pd.read_csv(file_price)
        df.columns = df.columns.str.lower()

        collection = db['equipments']

        for _, row in df.iterrows():
            category = row['category'].strip().lower()
            update_fields = {
                'rental_price': row['rental_price'],
                'late_fee': row['late_fee'],
                'replacement_fee': row['replacement_fee']
            }

            result = collection.update_many(
                {'category': category},
                {'$set': update_fields}
            )

            print(f"Updated {result.modified_count} documents for category '{category}'.")

        flash('Pricelist updated successfully!', 'success')

    except Exception as e:
        flash(f'Error uploading pricelist CSV: {str(e)}', 'danger')

    return redirect(url_for('home'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == os.getenv('APP_PASSWORD'):
            session['logged_in'] = True
            flash('Login successful!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Incorrect password', 'danger')
    return render_template('login.html', page_title="Insert the password")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)