


def make_all_equipments_available():
    from app import db

    result = db.equipments.update_many({}, {"$set": {"available": True}})
    print(f"{result.modified_count} equipment(s) marked as available.")

make_all_equipments_available()
