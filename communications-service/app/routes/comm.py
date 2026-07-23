import os
import requests
from flask import Blueprint, request, jsonify
from app.models.mensaje import db, Mensaje
from app.models.notificacion import Notificacion
from app.extensions import socketio

comm_bp = Blueprint('comm', __name__)

AUTH_SERVICE_URL = os.getenv('AUTH_SERVICE_URL', 'http://auth-service:5001')

def get_usuario_info(usuario_id):
    try:
        res = requests.get(f"{AUTH_SERVICE_URL}/usuarios/{usuario_id}", timeout=2)
        if res.status_code == 200:
            data = res.json()
            if data.get('success'):
                return data.get('usuario')
    except Exception as e:
        print(f"Error calling auth-service: {e}")
    return None

@comm_bp.route('/mensajes/<int:paciente_id>', methods=['GET'])
def obtener_mensajes(paciente_id):
    try:
        user_id = request.headers.get('X-User-Id')
        user_rol = request.headers.get('X-User-Role')
        
        if not user_id:
            return jsonify({'success': False, 'error': 'No autenticado'}), 401
            
        user_id = int(user_id)
        
        # Validar permisos
        if user_rol != 'Tecnico' and user_id != paciente_id:
            return jsonify({'success': False, 'error': 'No autorizado'}), 403
            
        mensajes = Mensaje.query.filter_by(paciente_id=paciente_id).order_by(Mensaje.fecha.asc()).all()
        
        # Cache local simple para nombres de usuarios
        usuarios_cache = {}
        mensajes_list = []
        
        for msg in mensajes:
            rid = msg.remitente_id
            if rid not in usuarios_cache:
                u_info = get_usuario_info(rid)
                usuarios_cache[rid] = u_info if u_info else {'nombre': 'Usuario', 'rol': 'Paciente'}
            
            mensajes_list.append({
                'id': msg.id,
                'remitente_id': msg.remitente_id,
                'remitente_nombre': usuarios_cache[rid]['nombre'],
                'rol': usuarios_cache[rid]['rol'],
                'contenido': msg.contenido,
                'fecha': msg.fecha.strftime('%Y-%m-%d %H:%M:%S') if msg.fecha else ''
            })
            
        return jsonify({
            'success': True,
            'mensajes': mensajes_list
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@comm_bp.route('/notificaciones', methods=['GET'])
def obtener_notificaciones():
    try:
        user_id = request.headers.get('X-User-Id')
        if not user_id:
            return jsonify({'success': False, 'error': 'No autenticado'}), 401
            
        user_id = int(user_id)
        notificaciones = Notificacion.query.filter_by(usuario_id=user_id, leida=False).order_by(Notificacion.fecha_creacion.desc()).all()
        
        notif_list = [{
            'id': n.id,
            'titulo': n.titulo,
            'mensaje': n.mensaje,
            'tipo': n.tipo,
            'fecha': n.fecha_creacion.strftime('%Y-%m-%d %H:%M') if n.fecha_creacion else ''
        } for n in notificaciones]
        
        return jsonify({'success': True, 'notificaciones': notif_list}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@comm_bp.route('/notificaciones/<int:notificacion_id>/leer', methods=['PUT'])
def marcar_notificacion_leida(notificacion_id):
    try:
        user_id = request.headers.get('X-User-Id')
        if not user_id:
            return jsonify({'success': False, 'error': 'No autenticado'}), 401
            
        user_id = int(user_id)
        notificacion = Notificacion.query.get(notificacion_id)
        
        if not notificacion or notificacion.usuario_id != user_id:
            return jsonify({'success': False, 'error': 'Notificación no encontrada o sin acceso'}), 404
            
        notificacion.leida = True
        db.session.commit()
        return jsonify({'success': True}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


# Endpoint interno para crear notificaciones y emitirlas por SocketIO
@comm_bp.route('/notificaciones/crear', methods=['POST'])
def crear_notificacion_interna():
    try:
        data = request.get_json() or {}
        usuario_id = data.get('usuario_id')
        titulo = data.get('titulo')
        mensaje = data.get('mensaje')
        tipo = data.get('tipo', 'info')
        
        if not usuario_id or not titulo or not mensaje:
            return jsonify({'success': False, 'error': 'Campos faltantes'}), 400
            
        nueva_notif = Notificacion(
            usuario_id=usuario_id,
            titulo=titulo,
            mensaje=mensaje,
            tipo=tipo
        )
        db.session.add(nueva_notif)
        db.session.commit()
        
        # Emisiones en tiempo real
        socketio.emit('notificacion', {
            'titulo': nueva_notif.titulo,
            'mensaje': nueva_notif.mensaje,
            'tipo': nueva_notif.tipo
        }, room=f"usuario_{usuario_id}")
        
        socketio.emit('nueva_notificacion_data', {
            'id': nueva_notif.id,
            'titulo': nueva_notif.titulo,
            'mensaje': nueva_notif.mensaje,
            'tipo': nueva_notif.tipo,
            'fecha': nueva_notif.fecha_creacion.strftime('%Y-%m-%d %H:%M') if nueva_notif.fecha_creacion else ''
        }, room=f"usuario_{usuario_id}")
        
        # Adicionalmente, emitir a la sala del paciente si corresponde
        socketio.emit('notificacion', {
            'titulo': nueva_notif.titulo,
            'mensaje': nueva_notif.mensaje,
            'tipo': nueva_notif.tipo
        }, room=f"paciente_{usuario_id}")
        
        socketio.emit('nueva_notificacion_data', {
            'id': nueva_notif.id,
            'titulo': nueva_notif.titulo,
            'mensaje': nueva_notif.mensaje,
            'tipo': nueva_notif.tipo,
            'fecha': nueva_notif.fecha_creacion.strftime('%Y-%m-%d %H:%M') if nueva_notif.fecha_creacion else ''
        }, room=f"paciente_{usuario_id}")
        
        return jsonify({'success': True, 'notificacion': nueva_notif.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
