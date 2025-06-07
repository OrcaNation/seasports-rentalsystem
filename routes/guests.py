from flask import Blueprint, render_template, request, redirect, url_for,flash
from datetime import datetime
from pdfrw import PdfReader, PdfWriter, PageMerge, PdfDict
from utils.drive_utils import upload_pdf_to_drive
import csv
import re




guests_bp = Blueprint('guests', __name__, url_prefix='/guests')


def fill_pdf_form(template_path, output_path, data):
    template_pdf = PdfReader(template_path)
    annotations = template_pdf.pages[0]['/Annots']

    for annotation in annotations:
        if annotation['/Subtype'] == '/Widget' and annotation['/T']:
            key = annotation['/T'][1:-1]  # Remove parênteses do nome do campo
            if key in data:
                annotation.update(PdfDict(V='{}'.format(data[key])))

    PdfWriter().write(output_path, template_pdf)



def room_sort_key(room):
    # Match partes numéricas e alfabéticas separadamente
    match = re.match(r"(\d+)\s*([A-Za-z]*)", room)
    if match:
        number = int(match.group(1))
        letter = match.group(2).upper()  # 'a' e 'A' tratadas igual
        return (number, letter)
    else:
        return (float('inf'), room)  # Se não bater regex, manda pro fim

@guests_bp.route("/", methods=["GET"])
def list_guests():
    from app import db


    guests_cursor = db.guests.find({
        "departure_date": {"$gte": datetime.today()}
    }).sort("departure_date", 1)
    guests_list = list(guests_cursor)
    return render_template('guests/guests.html',page_title="Guests",guests=guests_list)

@guests_bp.route('/register', methods=['GET', 'POST'])
def register():
    from app import db, now_in_malaysia

    now = now_in_malaysia().strftime("%Y-%m-%d")
    csv_rooms = "static/docs/rooms.csv"
    with open(csv_rooms, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        rooms_without_construction =  {row["room"] for row in reader if row['available']}

    guests_collection = db.guests  # substitua pelo nome da sua coleção se for diferente
    active_guests = guests_collection.find({
        "departure_date": {"$gt": now_in_malaysia()}
    })

    occupied_rooms = {guest['room_number'] for guest in active_guests}
    available_rooms = rooms_without_construction - occupied_rooms

    sorted_rooms = sorted(available_rooms, key=room_sort_key)


    if request.method == 'POST':
        name = request.form.get('name')
        room_number = request.form.get('room_number')

        if room_number not in available_rooms:
            flash("Room not available", "danger")
            return render_template('guests/register.html', page_title="Register", now=now, rooms=sorted_rooms)

        # Converte string para datetime, cuidado com o formato (ex: 'YYYY-MM-DD')
        departure_date_str = request.form.get('departure_date')
        departure_date = datetime.strptime(departure_date_str, '%Y-%m-%d') if departure_date_str else None

        guest = {
            "name": name,
            "room_number": room_number,
            "departure_date": departure_date,
        }

        result = db.guests.insert_one(guest)
        guest_id = str(result.inserted_id)

        return redirect(url_for('guests.show_waiver',guest_id=guest_id))

    return render_template('guests/register.html',page_title="Register", now=now, rooms=sorted_rooms)

@guests_bp.route('/waiver/<guest_id>', methods=["GET"])
def show_waiver(guest_id):
    template_path = f"static/docs/waiver.pdf"
    return render_template("guests/waiver.html", pdf_filename=template_path, guest_id=guest_id, page_title="Sign Waiver")



@guests_bp.route("/waiver/<guest_id>/confirm", methods=["POST"])
def confirm_waiver(guest_id):
    from app import db, now_in_malaysia
    from bson import ObjectId
    from flask import flash, request, redirect, url_for
    import base64
    import io
    from PIL import Image
    import fitz  # PyMuPDF
    import os


    guest = db.guests.find_one({"_id": ObjectId(guest_id)})
    if not guest:
        return "Guest not found", 404

    name = guest["name"]
    today = now_in_malaysia().strftime("%d/%m/%Y")
    os.makedirs(os.path.join("static", "tmp"), exist_ok=True)

    # Caminhos dos arquivos
    template_path = os.path.join("static", "docs", "waiver.pdf")
    output_path = os.path.join("static", "docs", f"waiver_{guest_id}.pdf")
    signature_path = os.path.join("static", "tmp", f"signature_{guest_id}.png")
    temp_output_path = os.path.join("static", "tmp", f"waiver_signed_{guest_id}.pdf")

    # Dados para preencher no PDF
    data = {
        "name": name,
        "date": today
    }

    # 1. Preenche o PDF com nome e data (gera waiver_partial)
    fill_pdf_form(template_path, output_path, data)

    # 2. Salvar a assinatura (imagem base64)
    signature_data = request.form.get("signature")
    if signature_data:
        image_data = base64.b64decode(signature_data.split(",")[1])
        image = Image.open(io.BytesIO(image_data)).convert("RGBA")
        image.save(signature_path, format="PNG")


    # 3. Abrir o PDF preenchido para inserir a assinatura
    doc = fitz.open(output_path)
    page = doc[0]

    # Ajuste a posição e tamanho da assinatura (mude conforme seu layout)
    rect = fitz.Rect(100, 500, 300, 600)

    if os.path.exists(signature_path):
        page.insert_image(rect, filename=signature_path)

    # 4. Salvar em arquivo temporário e depois substituir o original
    doc.save(temp_output_path)
    doc.close()

    os.replace(temp_output_path, output_path)

    # 5. Upload para o Google Drive (supondo que essa função já existe)

    drive_link = upload_pdf_to_drive(output_path, f"waiver_signed_{guest_id}.pdf")

    # 6. Atualiza o banco
    db.guests.update_one(
        {"_id": ObjectId(guest_id)},
        {
            "$set": {
                "liability_waiver_signed": True,
                "liability_waiver_drive_link": drive_link
            }
        }
    )

    # 7. Limpar arquivos temporários
    for path in [signature_path]:
        if os.path.exists(path):
            os.remove(path)

    flash("Waiver signed and uploaded successfully!", "success")
    return redirect(url_for("rentals.create_rental", guest_id=guest_id))


@guests_bp.route('/delete/<guest_id>', methods=['POST'])
def delete_guest(guest_id):
    from app import db
    from bson import ObjectId
    from flask import flash

    result = db.guests.delete_one({"_id": ObjectId(guest_id)})

    if result.deleted_count:
        flash("Guest deleted successfully.", "info")
    else:
        flash("Guest not found.", "danger")

    return redirect(url_for('guests.list_guests'))


@guests_bp.route('/edit/<guest_id>', methods=['GET', 'POST'])
def edit(guest_id):
    from app import db
    from bson import ObjectId

    guest = db.guests.find_one({"_id": ObjectId(guest_id)})

    if not guest:
        flash("Guest not found.", "danger")
        return redirect(url_for('guests.list_guests'))

    if request.method == 'POST':
        name = request.form.get('name')
        room_number = request.form.get('room_number')
        departure_date_str = request.form.get('departure_date')

        departure_date = datetime.strptime(departure_date_str, '%Y-%m-%d') if departure_date_str else None

        db.guests.update_one(
            {"_id": ObjectId(guest_id)},
            {"$set": {
                "name": name,
                "room_number": room_number,
                "departure_date": departure_date
            }}
        )

        flash("Guest updated successfully.", "success")
        return redirect(url_for('guests.list_guests'))

    return render_template('guests/register.html',
                           page_title="Edit Guest",
                           editing=True,
                           guest=guest,
                           guest_id=guest_id)
