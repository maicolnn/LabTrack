import os

from flask import Flask, redirect, url_for
from app.models.usuario import db, Usuario
from app.models.examen import Examen
from flask_socketio import SocketIO
from sqlalchemy import text
from app.routes.auth import auth_bp
from app.routes.main import main_bp

project_root = os.path.abspath(os.path.dirname(__file__))
instance_dir = os.path.join(project_root, 'instance')
os.makedirs(instance_dir, exist_ok=True)
db_path = os.path.join(instance_dir, 'laboratorio.db')

app = Flask(__name__, template_folder='app/templates', static_folder='app/static', instance_path=instance_dir)

# Configuración de la base de datos relacional local (SQLite para desarrollo)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'clave_secreta_laboratorio_2026'

# Inicializar Base de Datos y WebSockets
db.init_app(app)
socketio = SocketIO(app)

# Registrar los blueprints de rutas
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(main_bp)

# Crear las tablas automáticamente en la base de datos
with app.app_context():
    db.create_all()
    # SQLite no aplica cambios de esquema con create_all(); aseguramos columnas nuevas.
    try:
        cols = [row[1] for row in db.session.execute(text("PRAGMA table_info(examenes)")).all()]
        if 'usuario_id' not in cols:
            db.session.execute(text("ALTER TABLE examenes ADD COLUMN usuario_id INTEGER"))
            cols.append('usuario_id')

        if 'fecha_creacion' not in cols:
            # Guardamos como texto ISO/SQLite datetime; SQLAlchemy lo parsea como DateTime.
            db.session.execute(text("ALTER TABLE examenes ADD COLUMN fecha_creacion DATETIME"))
            # Backfill para filas antiguas (evita None en lecturas y respeta nullable=False del modelo).
            db.session.execute(text("UPDATE examenes SET fecha_creacion = CURRENT_TIMESTAMP WHERE fecha_creacion IS NULL"))

        db.session.commit()
    except Exception:
        db.session.rollback()

@app.route('/')
def index():
    return redirect(url_for('auth.login'))

if __name__ == '__main__':
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)