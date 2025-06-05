from flask import Blueprint, render_template, request, redirect, url_for
from bson import ObjectId
from datetime import datetime


equipments_bp = Blueprint('equipments', __name__)


@equipments_bp.route("/equipments")
def list_equipments():
    from app import db

    selected_type = request.args.get('category')
    available_only = request.args.get('available_only') == 'on'

    query = {}
    default = False

    if selected_type:
        query['label'] = selected_type
        default = True
    if available_only:
        query['available'] = True

    equipments = list(
        db.equipments.find(query).sort([
            ('sort',1),
            ('identifier', 1),
        ])
    )

    types = db.equipments.distinct('label')


    return render_template(
        "equipments/equipments.html",
        equipments=equipments,
        types=types,
        selected_type=selected_type,
        available_only=available_only,
        query=default,
        page_title="Equipment List"
    )

@equipments_bp.route("/equipments/<equipment_id>/view_problems", methods=["GET"])
def view_problems(equipment_id):
    from app import db
    equipment = db.equipments.find_one({"_id": ObjectId(equipment_id)})
    current_date = datetime.today().strftime('%Y-%m-%d')
    condition = equipment.get('condition', '')

    if not equipment:
        return "Equipment not found", 404
    return render_template("equipments/view_problems.html", equipment=equipment,page_title="Log of activities")

@equipments_bp.route("/equipments/<equipment_id>/report_problem", methods=["GET", "POST"])
def report_problem(equipment_id):
    from app import db
    equipment = db.equipments.find_one({"_id": ObjectId(equipment_id)})
    if not equipment:
        return "Equipment not found", 404

    if request.method == "POST":
        problem = request.form.get("problem")
        staff = request.form.get("staff")
        date_str = request.form.get("date")
        condition = request.form.get("condition")
        print("Received:", staff, date_str, condition, problem)

        if problem and staff and date_str and condition:
            try:
                reported_at = datetime.strptime(date_str, "%Y-%m-%d")  # ou "%d/%m/%Y" dependendo do formato no form
            except ValueError:
                reported_at = datetime.utcnow()

            db.equipments.update_one(
                {"_id": ObjectId(equipment_id)},
                {
                    "$push": {
                        "problems": {
                            "description": problem,
                            "reported_by": staff,
                            "reported_at": reported_at,
                            "condition": condition,
                            "date": date_str
                        }
                    },
                    "$set": {
                        "condition": condition  # atualiza a condição atual do equipamento
                    }
                }
            )
        return redirect(url_for("equipments.view_problems", equipment_id=equipment_id))

    else:
        current_date = datetime.today().strftime("%Y-%m-%d")  # precisa ser compatível com o input no form
        condition = equipment.get("condition", "")
        return render_template("equipments/report_problem.html",
                               equipment=equipment,
                               current_date=current_date,
                               condition=condition,
                               page_title="Report a Problem")

@equipments_bp.route('/equipments/price_list')
def price_list():
    from app import db
    collection = db['equipments']

    categories = collection.distinct('category')
    equipments = []

    for category in categories:
        equipment = collection.find_one({'category': category})
        if equipment:
            equipments.append(equipment)

    equipments.sort(key=lambda eq: eq.get('sort', ''))
    return render_template('equipments/price_list.html', equipments=equipments, page_title="Price List")