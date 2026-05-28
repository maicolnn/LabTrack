from flask import session
from flask_socketio import emit, join_room, leave_room
from app.extensions import socketio
from app.models.usuario import db, Usuario
from app.models.mensaje import Mensaje
from app.models.notificacion import Notificacion


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

@socketio.on('join')
def on_join(data):
    """
    Un usuario se une a una sala de chat.
    La sala de chat será el ID del paciente, ej. `paciente_1`.
    """
    paciente_id = data.get('paciente_id')
    usuario_id = data.get('usuario_id')
    if paciente_id:
        room = f"paciente_{paciente_id}"
        join_room(room)
        # emit('status', {'msg': f'Usuario unido a la sala {room}'}, room=room)
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
    """
    data debe contener:
    - paciente_id: a qué canal/sala pertenece
    - contenido: texto del mensaje
    """
    paciente_id = data.get('paciente_id')
    contenido = data.get('contenido')
    user_id = session.get('user_id')
    user_name = session.get('user_name')
    rol = session.get('rol')
    
    if not user_id or not paciente_id or not contenido:
        return

    remitente = Usuario.query.get(user_id)
    if not remitente:
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
        'fecha': nuevo_mensaje.fecha.strftime('%Y-%m-%d %H:%M:%S')
    }
    emit('receive_message', mensaje_data, room=room)

    if rol in ['Tecnico', 'Técnico']:
        destinatarios = [paciente_id]
        titulo_notif = 'Nuevo mensaje del laboratorio'
    else:
        destinatarios = [u.id for u in Usuario.query.filter(Usuario.rol.in_(['Tecnico', 'Técnico'])).all()]
        titulo_notif = f'Nuevo mensaje de {user_name}'

    for destinatario_id in destinatarios:
        if destinatario_id == user_id:
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
            'fecha': nueva_notif.fecha_creacion.strftime('%Y-%m-%d %H:%M')
        }, room=f"usuario_{destinatario_id}")
