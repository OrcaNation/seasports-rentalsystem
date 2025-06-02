from flask import Blueprint, render_template, flash, redirect, url_for
from datetime import datetime
from bson import ObjectId

finances_bp = Blueprint('finances', __name__,url_prefix='/finances')


@finances_bp.route('/')
def show_finances():
    from app import db
    today = datetime.utcnow()

    # Encontra todos os rentals com departure no futuro e nao pagos
    rentals = list(db.rentals.find({
        "confirmed": True,
        "departure_date": {"$gt": today},
        "paid": False
    }))
    print(rentals)
    # Organiza por room_number (que estamos usando como ID do hospede)
    guests = {}
    for rental in rentals:
        room = rental.get("room_number")
        name = rental.get("guest_name")
        date = rental.get("date")
        rental_total = sum(item.get("final_price", 0) for item in rental.get("items", []))

        if room not in guests:
            guests[room] = {
                "room": room,
                "name": name,
                "start": date,
                "end": date,
                "total": rental_total
            }
        else:
            guests[room]["total"] += rental_total
            if date < guests[room]["start"]:
                guests[room]["start"] = date
            if date > guests[room]["end"]:
                guests[room]["end"] = date

    # Converte dict para lista e ordena por número do quarto
    guests_list = sorted(guests.values(), key=lambda g: g["room"])



    return render_template("finances/finances.html", guests=guests_list, page_title="Outstanding Rentals")


@finances_bp.route('/detail/<room_number>')
def finances_detail(room_number):
    from app import db

    today = datetime.utcnow()

    rentals = list(db.rentals.find({
        "room_number": room_number,
        "paid": False,
        "departure_date": {"$gt": today}
    }))

    if not rentals:
        return f"No unpaid rentals found for room {room_number}"

    # Dados fixos para exibir
    guest_name = rentals[0]["guest_name"]
    departure_date = rentals[0]["departure_date"].strftime("%Y-%m-%d")
    start_date = min(r["date"] for r in rentals)
    end_date = max(r["date"] for r in rentals)

    # Agrupa por data
    daily_totals = {}
    overall_total = 0

    for rental in rentals:
        for item in rental["items"]:

            day = item.get("rented_at").date()
            if day not in daily_totals:
                daily_totals[day] = {
                    "items": [],
                    "subtotal": 0
                }

            daily_totals[day]["items"].append(item)
            daily_totals[day]["subtotal"] += item["final_price"]
            overall_total += item["final_price"]

    # Organiza os dias em ordem crescente
    daily_totals = dict(sorted(daily_totals.items()))


    return render_template("finances/finances_detail.html",
                           guest_name=guest_name,
                           room_number=room_number,
                           start_date=start_date,
                           end_date=end_date,
                           departure_date=departure_date,
                           daily_details=daily_totals,
                           overall_total=overall_total,
                           page_title=f"Details for {room_number} - {guest_name}")

from datetime import datetime


@finances_bp.route('/mark_as_paid/<room_number>/<departure_date>', methods=['POST'])
def mark_as_paid(room_number, departure_date):
    from app import db

    # Converte string da URL para datetime.date
    try:
        departure_dt = datetime.strptime(departure_date, "%Y-%m-%d")
    except ValueError:
        flash("Invalid departure date format.", "danger")
        return redirect(url_for('finances.finances_detail', room_number=room_number))

    now = datetime.utcnow()
    result = db.rentals.update_many(
        {
            "room_number": room_number,
            "departure_date": departure_dt,
            "paid_at": {"$exists": False}
        },
        {
            "$set": {
                "paid": True,
                "paid_at": now
            }
        }
    )

    flash(f"{result.modified_count} rentals marked as paid for room {room_number}.", "success")
    return redirect(url_for('home', room_number=room_number))