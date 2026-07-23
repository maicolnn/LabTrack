import os
import requests
from flask import request
from flask_socketio import emit, join_room, leave_room
from app.extensions import socketio
from app.models.mensaje import db, Mensaje
from app.models.notificacion import Notificacion

AUTH_SERVICE_URL = os.getenv('AUTH_SERVICE_URL', 'http://auth-service:5001')

def crear_notificacion_usuario(usuario_id, titulo, mensaje, tipo='info'):
    nueva_notif = Notificacion(
        usuario_id=usuario_id,
        titulo=titulo,
        mensaje=mensaje,
        tipo=tipo
    )
    db.session.add(nueva_notif)
    db.session.commit()
    return nueva_notif

def obtener_tecnicos_ids():
    try:
        res = requests.get(f"{AUTH_SERVICE_URL}/usuarios?rol=Tecnico", timeout=2)
        if res.status_code == 200:
            data = res.json()
            if data.get('success'):
                return [u.get('id') for u in data.get('usuarios', [])]
    except Exception as e:
        print(f"Error fetching tecnicos from auth-service: {e}")
    return []

@socketio.on('join')
def on_join(data):
    paciente_id = data.get('paciente_id')
    usuario_id = data.get('usuario_id')
    if paciente_id:
        room = f"paciente_{paciente_id}"
        join_room(room)
    if usuario_id:
        join_room(f"usuario_{usuario_id}")

@socketio.on('leave')
def on_leave(data):
    paciente_id = data.get('paciente_id')
    usuario_id = data.get('usuario_id')
    if paciente_id:
        room = f"paciente_{paciente_id}"
        leave_room(room)
    if usuario_id:
        leave_room(f"usuario_{usuario_id}")

@socketio.on('send_message')
def on_send_message(data):
    paciente_id = data.get('paciente_id')
    contenido = data.get('contenido')
    user_id = data.get('remitente_id')
    user_name = data.get('remitente_nombre')
    rol = data.get('rol')
    
    if not user_id or not paciente_id or not contenido:
        return

    # Guardar en BD
    nuevo_mensaje = Mensaje(
        remitente_id=user_id,
        paciente_id=paciente_id,
        contenido=contenido
    )
    db.session.add(nuevo_mensaje)
    db.session.commit()
    
    # Emitir a la sala
    room = f"paciente_{paciente_id}"
    mensaje_data = {
        'id': nuevo_mensaje.id,
        'remitente_id': user_id,
        'remitente_nombre': user_name,
        'rol': rol,
        'paciente_id': paciente_id,
        'contenido': contenido,
        'fecha': nuevo_mensaje.fecha.strftime('%Y-%m-%d %H:%M:%S') if nuevo_mensaje.fecha else ''
    }
    emit('receive_message', mensaje_data, room=room)

    # Lógica de notificaciones persistentes
    if rol in ['Tecnico', 'Técnico']:
        destinatarios = [paciente_id]
        titulo_notif = 'Nuevo mensaje del laboratorio'
    else:
        # Buscar técnicos dinámicamente
        destinatarios = obtener_tecnicos_ids()
        titulo_notif = f'Nuevo mensaje de {user_name}'

    for destinatario_id in destinatarios:
        if int(destinatario_id) == int(user_id):
            continue

        nueva_notif = crear_notificacion_usuario(
            destinatario_id,
            titulo_notif,
            contenido,
            'info'
        )

        socketio.emit('notificacion', {
            'titulo': nueva_notif.titulo,
            'mensaje': nueva_notif.mensaje,
            'tipo': nueva_notif.tipo
        }, room=f"usuario_{destinatario_id}")

        socketio.emit('nueva_notificacion_data', {
            'id': nueva_notif.id,
            'titulo': nueva_notif.titulo,
            'mensaje': nueva_notif.mensaje,
            'tipo': nueva_notif.tipo,
            'fecha': nueva_notif.fecha_creacion.strftime('%Y-%m-%d %H:%M') if nueva_notif.fecha_creacion else ''
        }, room=f"usuario_{destinatario_id}")
