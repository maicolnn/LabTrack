import os
from flask import Flask
from flask_cors import CORS
from app.models.mensaje import db
from app.extensions import socketio
from prometheus_flask_exporter import PrometheusMetrics

def create_app():
    app = Flask(__name__)
    CORS(app)

    # Instrumentar métricas
    PrometheusMetrics(app)

    # Configuration
    database_url = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@communications-db:5432/communications_db')
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'clave_secreta_laboratorio_2026')

    db.init_app(app)
    socketio.init_app(app)

    # Register routes
    from app.routes.comm import comm_bp
    app.register_blueprint(comm_bp)

    # Register event handlers
    import app.events as _events

    # Create tables automatically
    with app.app_context():
        db.create_all()

    return app
