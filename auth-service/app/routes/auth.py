import jwt
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, current_app
from app.models.usuario import db, Usuario

auth_bp = Blueprint('auth', __name__)

def generate_token(usuario):
    payload = {
        'user_id': usuario.id,
        'rol': usuario.rol,
        'nombre': usuario.nombre,
        'correo': usuario.correo,
        'exp': datetime.utcnow() + timedelta(hours=24)
    }
    return jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm='HS256')

@auth_bp.route('/registro', methods=['POST'])
def registro():
    data = request.get_json() or {}
    cedula = data.get('cedula')
    nombre = data.get('nombre')
    correo = data.get('correo')
    password = data.get('password')
    rol = data.get('rol', 'Paciente')

    if not (cedula and nombre and correo and password):
        return jsonify({'success': False, 'error': 'Todos los campos son obligatorios.'}), 400

    # Verificar si el correo ya está registrado
    if Usuario.query.filter_by(correo=correo).first():
        return jsonify({'success': False, 'error': 'El correo electrónico ya está registrado.'}), 400

    # Verificar si la cédula ya está registrada
    if Usuario.query.filter_by(cedula=cedula).first():
        return jsonify({'success': False, 'error': 'La cédula ya está registrada.'}), 400

    try:
        nuevo_usuario = Usuario(
            cedula=cedula,
            nombre=nombre,
            correo=correo,
            rol=rol
        )
        nuevo_usuario.set_password(password)
        
        db.session.add(nuevo_usuario)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'mensaje': 'Registro exitoso.',
            'usuario': nuevo_usuario.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': 'Ocurrió un error al registrar al usuario.'}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    correo = data.get('correo')
    password = data.get('password')

    if not correo or not password:
        return jsonify({'success': False, 'error': 'Por favor ingresa correo y contraseña.'}), 400

    usuario = Usuario.query.filter_by(correo=correo).first()

    if usuario and usuario.check_password(password):
        token = generate_token(usuario)
        return jsonify({
            'success': True,
            'token': token,
            'usuario': usuario.to_dict()
        }), 200
    else:
        return jsonify({'success': False, 'error': 'Credenciales incorrectas.'}), 401

@auth_bp.route('/validate', methods=['POST'])
def validate_token():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'success': False, 'error': 'Falta el token o formato inválido'}), 401
    
    token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
        return jsonify({'success': True, 'user': payload}), 200
    except jwt.ExpiredSignatureError:
        return jsonify({'success': False, 'error': 'El token ha expirado'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'success': False, 'error': 'Token inválido'}), 401

@auth_bp.route('/usuarios', methods=['GET'])
def obtener_usuarios():
    # Permitir filtrar por rol (ej: ?rol=Paciente)
    rol_filtro = request.args.get('rol')
    query = Usuario.query
    if rol_filtro:
        query = query.filter_by(rol=rol_filtro)
    usuarios = query.all()
    return jsonify({
        'success': True,
        'usuarios': [u.to_dict() for u in usuarios]
    }), 200

@auth_bp.route('/usuarios/<int:user_id>', methods=['GET'])
def obtener_usuario(user_id):
    usuario = Usuario.query.get(user_id)
    if not usuario:
        return jsonify({'success': False, 'error': 'Usuario no encontrado'}), 404
    return jsonify({
        'success': True,
        'usuario': usuario.to_dict()
    }), 200
