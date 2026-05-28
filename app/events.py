from flask import session
from flask_socketio import emit, join_room, leave_room
from app.extensions import socketio
from app.models.usuario import db, Usuario
from app.models.mensaje import Mensaje

@socketio.on('join')
def on_join(data):
    """
    Un usuario se une a una sala de chat.
    La sala de chat será el ID del paciente, ej. `paciente_1`.
    """
    # Prefer an explicit room name if provided (allows exam-specific rooms)
    sala = data.get('sala')
    paciente_id = data.get('paciente_id')
    if sala:
        room = sala
        join_room(room)
    elif paciente_id:
        room = f"paciente_{paciente_id}"
        join_room(room)
        # emit('status', {'msg': f'Usuario unido a la sala {room}'}, room=room)

@socketio.on('leave')
def on_leave(data):
    sala = data.get('sala')
    paciente_id = data.get('paciente_id')
    if sala:
        leave_room(sala)
    elif paciente_id:
        leave_room(f"paciente_{paciente_id}")

@socketio.on('send_message')
def on_send_message(data):
    """
    data debe contener:
    - paciente_id: a qué canal/sala pertenece
    - contenido: texto del mensaje
    """
    paciente_id = data.get('paciente_id')
    contenido = data.get('contenido')
    sala = data.get('sala')
    user_id = session.get('user_id')
    user_name = session.get('user_name')
    rol = session.get('rol')
    
    if not user_id or not paciente_id or not contenido:
        return
        
    # Guardar en BD
    nuevo_mensaje = Mensaje(
        remitente_id=user_id,
        paciente_id=paciente_id,
        sala=sala,
        contenido=contenido
    )
    db.session.add(nuevo_mensaje)
    db.session.commit()
    
    # Emitir a la sala
    # Emit to explicit sala if provided, otherwise use paciente-based room
    room = sala if sala else f"paciente_{paciente_id}"
    mensaje_data = {
        'id': nuevo_mensaje.id,
        'remitente_id': user_id,
        'remitente_nombre': user_name,
        'rol': rol,
        'contenido': contenido,
        'fecha': nuevo_mensaje.fecha.strftime('%Y-%m-%d %H:%M:%S')
    }
    emit('receive_message', mensaje_data, room=room)
