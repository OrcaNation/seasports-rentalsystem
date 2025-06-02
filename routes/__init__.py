from .guests import guests_bp
from .equipments import equipments_bp
from .rentals import rentals_bp
from .finances import finances_bp

def register_routes(app):
    app.register_blueprint(guests_bp)
    app.register_blueprint(equipments_bp)
    app.register_blueprint(rentals_bp)
    app.register_blueprint(finances_bp)