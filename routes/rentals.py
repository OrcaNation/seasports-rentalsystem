from flask import Blueprint, render_template, request, redirect, url_for, session
from datetime import datetime, time, timedelta
import pytz

rentals_bp = Blueprint('rentals', __name__, url_prefix='/rentals')


def create_item(equipment_category, equipment_id):
    from app import db
    equipments_collection_c = db.equipments
    try:
        equipment_id = int(equipment_id)  # <-- Conversão necessária!
    except (ValueError, TypeError):
        return None  # Retorna nada se não for conversível
    equipment = equipments_collection_c.find_one({
        'category': equipment_category,
        'identifier': equipment_id,
    })
    price = equipment.get('rental_price', 0) if equipment else 0
    equipment_label = equipment.get('label', 0) if equipment else 0
    late_fee = equipment.get('late_fee', 0) if equipment else 0
    replacement_fee = equipment.get('replacement_fee', 0) if equipment else 0
    equipments_collection_c.update_one(
        {'_id': equipment.get('_id')},
        {'$set': {'available': False}}
    )

    return {
        'label': equipment_label,
        'category': equipment_category,
        'identifier': equipment_id,
        'rented_at': datetime.now(),
        'returned': False,
        'price': price,
        'late_fee': late_fee,
        'replacement_fee': replacement_fee,
        'final_price': replacement_fee,
        "charge_type": "replacement"

    }


def determine_final_price(item, returned_at):
    # Converte rented_at e returned_at em datetime
    if isinstance(item["rented_at"], str):
        rented_at = datetime.fromisoformat(item["rented_at"])
    else:
        rented_at = item["rented_at"]

    if isinstance(returned_at, str):
        returned_at = datetime.fromisoformat(returned_at)

    # Define os limites
    normal_deadline = datetime.combine(rented_at.date(), time(17, 30))
    late_deadline = datetime.combine(rented_at.date() + timedelta(days=1), time(9, 0))

    # Define tipo de cobrança
    if returned_at <= normal_deadline:
        return "normal", item.get("price", 0)
    elif returned_at <= late_deadline:
        return "late", item.get("late_fee", 0)
    else:
        return "replacement", item.get("replacement_fee", 0)


def return_equipment_item(rental, category, identifier):
    from app import db
    updated_items = []
    item_returned = False

    returned_at = datetime.utcnow()
    for item in rental["items"]:
        if str(item["identifier"]) == identifier and item["category"] == category and not item.get("returned", False):
            item["returned"] = True
            item["returned_at"] = returned_at.isoformat()

            # 🧠 Cálculo do tipo de cobrança e valor final

            charge_type, final_price = determine_final_price(item, returned_at)
            item["charge_type"] = charge_type
            item["final_price"] = final_price

            item_returned = True
        updated_items.append(item)

    if item_returned:
        db.rentals.update_one(
            {"_id": rental["_id"]},
            {"$set": {"items": updated_items}}
        )

        db.equipments.update_one(
            {"category": category, "identifier": int(identifier)},
            {"$set": {"available": True}}
        )

    return item_returned

#Routes_--------------------

@rentals_bp.route('/')
def show_rentals():
    from app import db
    guests_collection = db.guests
    today = datetime.now(pytz.UTC)  # para garantir compatibilidade com MongoDB timestamps
    guests = list(guests_collection.find({
        "liability_waiver_signed": True,
        "departure_date": {"$gte": today}
    }))
    return render_template('rentals/rentals.html', guests=guests, page_title="Rentals")


@rentals_bp.route("/rent/<guest_id>", methods=["POST"])
def select_guest(guest_id):
    from app import db
    from bson import ObjectId

    guest = db.guests.find_one({"_id": ObjectId(guest_id)})
    if not guest:
        return "Guest not found", 404

    return render_template('select_equipment.html', guest=guest, page_title="Rental Form")


@rentals_bp.route('/create_rental/<guest_id>', methods=['GET', 'POST'])
def create_rental(guest_id):
    from app import db
    from bson import ObjectId
    from flask import session, flash

    guests_collection = db.guests
    equipments_collection_c = db.equipments
    rentals_collection = db.rentals

    guest = guests_collection.find_one({"_id": ObjectId(guest_id)})
    if not guest:
        return "Guest not found", 404

    rental_id = session.get('rental_id')
    rental = None

    if rental_id:
        rental = rentals_collection.find_one({'_id': ObjectId(rental_id), 'confirmed': False})
        if not rental:
            session.pop('rental_id', None)
            rental_id = None

    if not rental_id:
        rental_doc = {
            'guest_id': ObjectId(guest_id),
            'guest_name': guest.get('name'),
            'room_number': guest.get('room_number'),
            'date':datetime.utcnow(),
            'departure_date': guest.get('departure_date'),
            'items': [],
            'confirmed': False,
            "paid": False,
        }
        rental_id = rentals_collection.insert_one(rental_doc).inserted_id
        session['rental_id'] = str(rental_id)
        rental = rentals_collection.find_one({'_id': rental_id})

    if request.method == 'POST':
        equipment_category = request.form.get('equipment_category')
        equipment_id = request.form.get('equipment_id')
        paddle_1_id = request.form.get('paddle_id')
        paddle_2_id = request.form.get('paddle_1_id')
        items_to_add = []

        def safe_create_and_add(category, identifier):
            try:
                identifier = int(identifier)
            except (TypeError, ValueError):
                flash(f"Invalid identifier for {category}.", "warning")
                return

            equipment = equipments_collection_c.find_one({
                'category': category,
                'identifier': identifier
            })

            if not equipment:
                flash(f"{category.title()} {identifier} not found.", "danger")
                return

            if not equipment.get('available', True):
                flash(f"{equipment.get('label', category.title())} {identifier} is not available.", "warning")
                return

            item = create_item(category, identifier)
            if item:
                items_to_add.append(item)

        if equipment_id:
            safe_create_and_add(equipment_category, equipment_id)

        if paddle_1_id:
            safe_create_and_add('paddle', paddle_1_id)

        if paddle_2_id:
            safe_create_and_add('paddle', paddle_2_id)

        for item in items_to_add:
            rentals_collection.update_one(
                {'_id': ObjectId(rental_id)},
                {'$push': {'items': item}}
            )

        return redirect(url_for('rentals.create_rental', guest_id=guest_id))

    cursor = equipments_collection_c.find({"category": {"$ne": "paddle"}})
    categories_dict = {}

    for eq in cursor:
        cat = eq["category"]
        label = eq["label"]
        sort = eq.get("sort", 999)

        if cat not in categories_dict:
            categories_dict[cat] = {"label": label, "sort": sort}

    equipment_data = [
        {"category": k, "label": v["label"], "sort": v["sort"]}
        for k, v in categories_dict.items()
    ]

    equipment_data.sort(key=lambda item: item["sort"])
    rented_items = rental.get('items', [])

    return render_template(
        'rentals/create_rental.html',
        guest=guest,
        equipments=equipment_data,
        rental=rental,
        rented_items=rented_items,
        page_title="Choose the Equipment"
    )


@rentals_bp.route('/delete_rental_item/<rental_id>/<category>/<item_identifier>', methods=['POST'])
def delete_rental_item(rental_id, category, item_identifier):
    from app import db
    from bson import ObjectId

    # Remove o item com aquele category + identifier do rental
    db.rentals.update_one(
        {"_id": ObjectId(rental_id)},
        {"$pull": {"items": {"category": category, "identifier": int(item_identifier)}}}
    )
    print(ObjectId(rental_id), category, item_identifier)
    # Marca o equipamento correspondente como disponível novamente
    db.equipments.update_one(
        {"category": category, "identifier": int(item_identifier)},
        {"$set": {"available": True}}
    )

    return redirect(request.referrer or url_for('home'))


@rentals_bp.route('/clear_rental_items/<rental_id>', methods=['POST'])
def clear_rental_items(rental_id):
    from app import db
    from bson import ObjectId

    rental = db.rentals.find_one({"_id": ObjectId(rental_id)})
    if rental:
        items = rental.get("items", [])

        for item in items:
            category = item.get("category")
            identifier = item.get("identifier")
            if category and identifier:
                db.equipments.update_one(
                    {"category": category, "identifier": identifier},
                    {"$set": {"available": True}}
                )

        db.rentals.update_one(
            {"_id": ObjectId(rental_id)},
            {"$set": {"items": []}}
        )

    return redirect(request.referrer or url_for('rentals.create_rental', guest_id=session.get('guest_id')))


@rentals_bp.route('/confirm_rental/<rental_id>', methods=['POST'])
def confirm_rental(rental_id):
    from app import db
    from bson import ObjectId
    from flask import session

    rentals_collection = db.rentals

    # Atualiza o rental
    rentals_collection.update_one(
        {'_id': ObjectId(rental_id)},
        {'$set': {'confirmed': True}}
    )

    # Remove da sessão
    session.pop('rental_id', None)

    return redirect(url_for('home'))


@rentals_bp.route('/returns')
def show_returns():
    from app import db

    categories_dict = {}

    cursor = db.equipments.find({"category": {"$ne": "paddle"}}).sort("sort", 1)

    for eq in cursor:
        cat = eq["category"]
        if cat not in categories_dict:
            categories_dict[cat] = eq["sort"]  # ou o próprio equipamento se quiser mais info

    sorted_categories = list(categories_dict.keys())

    # Buscar todos os rentals confirmados com pelo menos um item não devolvido
    rentals = list(db.rentals.find({
        "confirmed": True,
        "paid": False,
        "items": {
            "$elemMatch": {
                "returned": False
            }
        }
    }))
    for rental in rentals:
        rental['rented_items'] = rental.pop('items')
        rental["_id"] = str(rental["_id"])

        if isinstance(rental["date"], str):
            rental["date_obj"] = datetime.strptime(rental["date"], "%Y-%m-%d")
        else:
            rental["date_obj"] = rental["date"]  # já é datetime

    return render_template(
        "returns/returns.html",
        rentals=rentals,
        equipment_categories=sorted_categories,
        page_title="Return Equipment"
    )


@rentals_bp.route('/returns/<rental_id>')
def show_return_details(rental_id):
    from bson import ObjectId
    from app import db

    rental = db.rentals.find_one({"_id": ObjectId(rental_id)})
    if not rental:
        return "Rental not found", 404

    equipment_categories = db.equipments.distinct("category")
    equipment_categories = [cat for cat in equipment_categories if cat != "paddle"]

    rental['rented_items'] = rental.pop('items')
    rental["_id"] = str(rental["_id"])

    if isinstance(rental["date"], str):
        rental["date_obj"] = datetime.strptime(rental["date"], "%Y-%m-%d")
    else:
        rental["date_obj"] = rental["date"]  # já é datetime

    return render_template("returns/return_rental.html",
                           rental=rental,
                           categories=equipment_categories)


@rentals_bp.route('/return_item/<rental_id>/<category>/<identifier>', methods=['POST'])
def return_item(rental_id, category, identifier):
    from app import db
    from bson import ObjectId

    rental = db.rentals.find_one({"_id": ObjectId(rental_id)})
    if not rental:
        return "Rental not found", 404

    return_equipment_item(rental, category, identifier)

    # Verifica se ainda há itens não devolvidos
    still_renting = any(not item.get("returned", False) for item in rental["items"])

    if still_renting:
        return redirect(url_for("rentals.show_return_details", rental_id=rental_id))
    else:
        return redirect(url_for("home"))


@rentals_bp.route('/return_all/<rental_id>', methods=['POST'])
def return_all(rental_id):
    from app import db
    from bson import ObjectId

    rental = db.rentals.find_one({"_id": ObjectId(rental_id)})
    if not rental:
        return "Rental not found", 404

    for item in rental["items"]:
        return_equipment_item(rental, item["category"], str(item["identifier"]))

    return redirect(url_for("home"))