from flask import Blueprint, render_template, flash, redirect, url_for, request
import pandas as pd

finances_bp = Blueprint('finances', __name__, url_prefix='/finances')


@finances_bp.route('/')
def show_finances():
    from app import db, now_in_malaysia
    today = now_in_malaysia()

    # Encontra todos os rentals com departure no futuro e nao pagos
    rentals = list(db.rentals.find({
        "confirmed": True,
        "departure_date": {"$gt": today},
        "paid": False
    }))

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

    return render_template("finances/finances.html", guests=guests_list, page_title="Finances")


@finances_bp.route('/detail/<room_number>')
def finances_detail(room_number):
    from app import db, now_in_malaysia

    today = now_in_malaysia()

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
                           page_title=f"Details for {room_number}")


from datetime import datetime


@finances_bp.route('/mark_as_paid/<room_number>/<departure_date>', methods=['POST'])
def mark_as_paid(room_number, departure_date):
    from app import db, now_in_malaysia

    # Converte string da URL para datetime.date
    try:
        departure_dt = datetime.strptime(departure_date, "%Y-%m-%d")
    except ValueError:
        flash("Invalid departure date format.", "danger")
        return redirect(url_for('finances.finances_detail', room_number=room_number))

    now = now_in_malaysia()
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


@finances_bp.route('/reports')
def dashboard():
    from app import db
    # 1. Pega os filtros da URL
    start_str = request.args.get('start')
    end_str = request.args.get('end')
    category_filter = request.args.get('category', 'all')

    start_date = datetime.strptime(start_str, '%Y-%m-%d') if start_str else None
    end_date = datetime.strptime(end_str, '%Y-%m-%d') if end_str else None

    # Busca categorias únicas na coleção equipments
    categories = db.equipments.distinct('label')
    categories.sort()

    # Monta a lista incluindo 'all' no começo
    categories = ['All'] + categories

    # Passa para o template os filtros e categorias
    filters = {
        'start': start_str,
        'end': end_str,
        'category': category_filter,
        # aqui você pode adicionar outros filtros como start/end
    }

    # 2. Constrói a query
    query = {}
    if start_date and end_date:
        # Considera o final do dia para o filtro 'end'
        end_date = end_date.replace(hour=23, minute=59, second=59)
        query['date'] = {'$gte': start_date, '$lte': end_date}
    elif start_date:
        query['date'] = {'$gte': start_date}
    elif end_date:
        end_date = end_date.replace(hour=23, minute=59, second=59)
        query['date'] = {'$lte': end_date}

    if category_filter.lower() != 'all':
        pipeline = [
            {'$match': query},
            {'$project': {
                'guest_id': 1,
                'guest_name': 1,
                'room_number': 1,
                'date': 1,
                'departure_date': 1,
                'confirmed': 1,
                'paid': 1,
                'paid_at': 1,
                # filtra os items para só a categoria escolhida
                'items': {
                    '$filter': {
                        'input': '$items',
                        'as': 'item',
                        'cond': {'$eq': ['$$item.label', category_filter]}
                    }
                }
            }},
            {'$match': {'items.0': {'$exists': True}}}
        ]
    else:
        # Se for 'all', só faz o match normal, pega tudo
        pipeline = [
            {'$match': query}
        ]
    rentals_collection = db.rentals
    filtered_rentals = list(rentals_collection.aggregate(pipeline))
    for rental in filtered_rentals:
        total = sum(item['final_price'] for item in rental['items'])
        rental['total_price'] = total

    if filtered_rentals:
        df = pd.DataFrame(filtered_rentals)
        df['date'] = pd.to_datetime(df['date'])
        daily_totals = df.groupby(df['date'].dt.date)['total_price'].sum().reset_index()
        line_chart = {
            'labels_line': daily_totals['date'].astype(str).tolist(),
            'values_line': daily_totals['total_price'].tolist(),
        }
        df['weekday'] = df['date'].dt.dayofweek
        weekday_map = {
            0: 'Mon', 1: 'Tue', 2: 'Wed',
            3: 'Thu', 4: 'Fri', 5: 'Sat', 6: 'Sun'
        }
        df['weekday_name'] = df['weekday'].map(weekday_map)
        df['num_items'] = df['items'].apply(lambda x: len(x))

        # Calcular a média por dia da semana
        weekly_avg_items = df.groupby('weekday_name')['num_items'].mean()

        # Garantir que todos os dias apareçam, mesmo que com 0
        ordered_days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        weekly_avg = weekly_avg_items.reindex(ordered_days, fill_value=0)

        # Preparar o gráfico
        bar_chart = {
            'labels_bar': weekly_avg.index.tolist(),
            'values_bar': weekly_avg.tolist()
        }

        exploded_items = df.explode('items')
        items_df = pd.json_normalize(exploded_items['items'])
        category_totals = items_df.groupby('label')['price'].sum().reset_index()
        category_totals = category_totals[category_totals['price'] > 0]
        pie_chart = {
            'labels_pie': category_totals['label'].tolist(),
            'values_pie': category_totals['price'].tolist()
        }

        total_revenue = df['total_price'].sum()
        total_rentals = len(df)
        total_guests = df['guest_name'].nunique()
        total_items = exploded_items['items'].count()

    else:
        # Gráfico com valor zero, só pra não quebrar visual
        line_chart = {
            'labels_line': ['No data'],
            'values_line': [0],
        }
        bar_chart = {
            'labels_bar': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
            'values_bar': [0, 0, 0, 0, 0, 0, 0]
        }
        pie_chart = {
            'labels_pie': [],
            'values_pie': []
        }

        total_revenue = 0
        total_rentals = 0
        total_guests = 0
        total_items = 0

    return render_template("finances/reports.html", categories=categories, filters=filters, rentals=filtered_rentals,
                           line=line_chart, bar=bar_chart, pie=pie_chart, total_revenue=total_revenue, total_rentals=total_rentals, total_guests=total_guests, total_items=total_items)
