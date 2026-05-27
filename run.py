from flask import Flask, redirect, url_for
from app.models.usuario import db
from flask_socketio import SocketIO
from app.routes.auth import auth_bp
from app.routes.main import main_bp

app = Flask(__name__)

# Configuración de la base de datos relacional local (SQLite para desarrollo)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///laboratorio.db'
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

@app.route('/')
def index():
    return redirect(url_for('auth.login'))

if __name__ == '__main__':
    socketio.run(app, debug=True)