from flask import Flask
from app.models.usuario import db
from flask_socketio import SocketIO

app = Flask(__name__)

# Configuración de la base de datos relacional local (SQLite para desarrollo)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///laboratorio.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'clave_secreta_laboratorio_2026'

# Inicializar componentes en el monolito
db.init_app(app)
socketio = SocketIO(app)

# Crear las tablas automáticamente en la base de datos
with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return "¡Servidor Monolítico del Laboratorio Clínico Inicializado Correctamente!"

if __name__ == '__main__':
    socketio.run(app, debug=True)