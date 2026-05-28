from flask import Blueprint, render_template, request, jsonify, session, current_app, url_for
import os
from werkzeug.utils import secure_filename
from app.utils.decorators import login_required, tecnico_required
from app.models.usuario import db, Usuario
from app.models.examen import Examen
from app.models.mensaje import Mensaje
from app.models.notificacion import Notificacion
from app.extensions import socketio

main_bp = Blueprint('main', __name__)


# ======================== RUTAS DE VISUALIZACIÓN ========================

@main_bp.route('/dashboard')
@login_required
def dashboard():
    """Renderiza el dashboard con la lista de exámenes"""
    return render_template('dashboard.html')


# ======================== RUTAS AUXILIARES ========================

# GET - Obtener lista de pacientes (para que técnicos asignen exámenes)
@main_bp.route('/pacientes', methods=['GET'])
@tecnico_required
def obtener_pacientes():
    """
    Retorna lista de pacientes (usuarios con rol 'Paciente')
    Solo accesible para técnicos
    """
    try:
        pacientes = Usuario.query.filter_by(rol='Paciente').all()
        pacientes_list = [
            {
                'id': paciente.id,
                'nombre': paciente.nombre,
                'cedula': paciente.cedula,
                'correo': paciente.correo
            }
            for paciente in pacientes
        ]
        return jsonify({
            'success': True,
            'pacientes': pacientes_list,
            'total': len(pacientes_list)
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ======================== RUTAS CRUD DE EXÁMENES ========================

# READ - Obtener exámenes del usuario actual
@main_bp.route('/examenes', methods=['GET'])
@login_required
def obtener_examenes():
    """
    Retorna una lista de exámenes:
    - Técnicos: todos los exámenes que han asignado
    - Pacientes: solo sus exámenes asignados
    """
    try:
        user_id = session.get('user_id')
        user_rol = session.get('rol')
        
        if user_rol == 'Tecnico':
            # Los técnicos ven todos los exámenes que han asignado
            examenes = Examen.query.all()
        else:
            # Los pacientes ven solo sus exámenes
            examenes = Examen.query.filter_by(usuario_id=user_id).all()
        
        examenes_list = [
            {
                'id': examen.id,
                'nombre': examen.nombre,
                'descripcion': examen.descripcion,
                'precio': examen.precio,
                'tiempo_entrega': examen.tiempo_entrega,
                'usuario_id': examen.usuario_id,
                'usuario_nombre': examen.usuario.nombre if examen.usuario else 'Sin asignar',
                'fecha_creacion': examen.fecha_creacion.strftime('%Y-%m-%d %H:%M') if examen.fecha_creacion else '',
                'estado': examen.estado,
                'archivo_resultado': url_for('static', filename=f'uploads/resultados/{examen.archivo_resultado}') if examen.archivo_resultado else None
            }
            for examen in examenes
        ]
        return jsonify({
            'success': True,
            'examenes': examenes_list,
            'total': len(examenes_list)
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# READ - Obtener un examen específico por ID
@main_bp.route('/examenes/<int:examen_id>', methods=['GET'])
@login_required
def obtener_examen(examen_id):
    """
    Retorna los detalles de un examen específico.
    Solo si el usuario es técnico o es el propietario del examen.
    """
    try:
        examen = Examen.query.get(examen_id)
        if not examen:
            return jsonify({
                'success': False,
                'error': 'Examen no encontrado'
            }), 404
        
        # Verificar acceso
        user_id = session.get('user_id')
        user_rol = session.get('rol')
        if user_rol != 'Tecnico' and examen.usuario_id != user_id:
            return jsonify({
                'success': False,
                'error': 'No tienes acceso a este examen'
            }), 403
        
        return jsonify({
            'success': True,
            'examen': {
                'id': examen.id,
                'nombre': examen.nombre,
                'descripcion': examen.descripcion,
                'precio': examen.precio,
                'tiempo_entrega': examen.tiempo_entrega,
                'usuario_id': examen.usuario_id,
                'usuario_nombre': examen.usuario.nombre if examen.usuario else 'Sin asignar',
                'fecha_creacion': examen.fecha_creacion.strftime('%Y-%m-%d %H:%M') if examen.fecha_creacion else '',
                'estado': examen.estado,
                'archivo_resultado': url_for('static', filename=f'uploads/resultados/{examen.archivo_resultado}') if examen.archivo_resultado else None
            }
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# CREATE - Crear un nuevo examen 
@main_bp.route('/examenes', methods=['POST'])
@tecnico_required
def crear_examen():
    
    try:
        data = request.get_json()
        
        # Validación de campos requeridos
        campos_requeridos = ['nombre', 'descripcion', 'precio', 'tiempo_entrega', 'usuario_id']
        for campo in campos_requeridos:
            if campo not in data or data[campo] is None or (isinstance(data[campo], str) and str(data[campo]).strip() == ''):
                return jsonify({
                    'success': False,
                    'error': f'El campo "{campo}" es requerido'
                }), 400
        
        # Validación de precio
        try:
            precio = float(data['precio'])
            if precio < 0:
                raise ValueError('El precio no puede ser negativo')
        except (ValueError, TypeError):
            return jsonify({
                'success': False,
                'error': 'El precio debe ser un número válido'
            }), 400
        
        # Validación de usuario_id
        try:
            usuario_id = int(data['usuario_id'])
            usuario = Usuario.query.get(usuario_id)
            if not usuario:
                return jsonify({
                    'success': False,
                    'error': 'El paciente no existe'
                }), 400
            if usuario.rol != 'Paciente':
                return jsonify({
                    'success': False,
                    'error': 'Solo puedes asignar exámenes a pacientes'
                }), 400
        except (ValueError, TypeError):
            return jsonify({
                'success': False,
                'error': 'ID de usuario inválido'
            }), 400
        
        # Crear nuevo examen
        nuevo_examen = Examen(
            nombre=data['nombre'].strip(),
            descripcion=data['descripcion'].strip(),
            precio=precio,
            tiempo_entrega=data['tiempo_entrega'].strip(),
            usuario_id=usuario_id
        )
        
        db.session.add(nuevo_examen)
        db.session.commit()
        
        socketio.emit('notificacion', {
            'titulo': 'Nuevo Examen',
            'mensaje': f'Te han asignado un nuevo examen: {nuevo_examen.nombre}',
            'tipo': 'success'
        }, room=f"paciente_{usuario_id}")
        
        return jsonify({
            'success': True,
            'mensaje': 'Examen creado exitosamente',
            'examen': {
                'id': nuevo_examen.id,
                'nombre': nuevo_examen.nombre,
                'descripcion': nuevo_examen.descripcion,
                'precio': nuevo_examen.precio,
                'tiempo_entrega': nuevo_examen.tiempo_entrega,
                'usuario_id': nuevo_examen.usuario_id,
                'usuario_nombre': nuevo_examen.usuario.nombre if nuevo_examen.usuario else 'Sin asignar',
                'fecha_creacion': nuevo_examen.fecha_creacion.strftime('%Y-%m-%d %H:%M') if nuevo_examen.fecha_creacion else '',
                'estado': nuevo_examen.estado,
                'archivo_resultado': None
            }
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# UPDATE - Actualizar un examen existente (solo Técnicos)
@main_bp.route('/examenes/<int:examen_id>', methods=['PUT', 'POST'])
@tecnico_required
def actualizar_examen(examen_id):
    
    try:
        examen = Examen.query.get(examen_id)
        if not examen:
            return jsonify({
                'success': False,
                'error': 'Examen no encontrado'
            }), 404
        
        data = request.get_json()
        
        # Validación y actualización de campos
        if 'nombre' in data:
            if data['nombre'] is None or str(data['nombre']).strip() == '':
                return jsonify({
                    'success': False,
                    'error': 'El nombre no puede estar vacío'
                }), 400
            examen.nombre = data['nombre'].strip()
        
        if 'descripcion' in data:
            if data['descripcion'] is None or str(data['descripcion']).strip() == '':
                return jsonify({
                    'success': False,
                    'error': 'La descripción no puede estar vacía'
                }), 400
            examen.descripcion = data['descripcion'].strip()
        
        if 'precio' in data:
            try:
                precio = float(data['precio'])
                if precio < 0:
                    raise ValueError('El precio no puede ser negativo')
                examen.precio = precio
            except (ValueError, TypeError):
                return jsonify({
                    'success': False,
                    'error': 'El precio debe ser un número válido'
                }), 400
        
        if 'tiempo_entrega' in data:
            if data['tiempo_entrega'] is None or str(data['tiempo_entrega']).strip() == '':
                return jsonify({
                    'success': False,
                    'error': 'El tiempo de entrega no puede estar vacío'
                }), 400
            examen.tiempo_entrega = data['tiempo_entrega'].strip()
        
        if 'usuario_id' in data:
            try:
                usuario_id = int(data['usuario_id'])
                usuario = Usuario.query.get(usuario_id)
                if not usuario:
                    return jsonify({
                        'success': False,
                        'error': 'El paciente no existe'
                    }), 400
                if usuario.rol != 'Paciente':
                    return jsonify({
                        'success': False,
                        'error': 'Solo puedes asignar exámenes a pacientes'
                    }), 400
                examen.usuario_id = usuario_id
            except (ValueError, TypeError):
                return jsonify({
                    'success': False,
                    'error': 'ID de usuario inválido'
                }), 400
        
        db.session.commit()
        
        socketio.emit('notificacion', {
            'titulo': 'Examen Actualizado',
            'mensaje': f'El examen "{examen.nombre}" ha sido actualizado.',
            'tipo': 'info'
        }, room=f"paciente_{examen.usuario_id}")
        
        return jsonify({
            'success': True,
            'mensaje': 'Examen actualizado exitosamente',
            'examen': {
                'id': examen.id,
                'nombre': examen.nombre,
                'descripcion': examen.descripcion,
                'precio': examen.precio,
                'tiempo_entrega': examen.tiempo_entrega,
                'usuario_id': examen.usuario_id,
                'usuario_nombre': examen.usuario.nombre if examen.usuario else 'Sin asignar',
                'fecha_creacion': examen.fecha_creacion.strftime('%Y-%m-%d %H:%M') if examen.fecha_creacion else '',
                'estado': examen.estado,
                'archivo_resultado': url_for('static', filename=f'uploads/resultados/{examen.archivo_resultado}') if examen.archivo_resultado else None
            }
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# DELETE - Eliminar un examen 
@main_bp.route('/examenes/<int:examen_id>', methods=['DELETE'])
@tecnico_required
def eliminar_examen(examen_id):
   
    try:
        examen = Examen.query.get(examen_id)
        if not examen:
            return jsonify({
                'success': False,
                'error': 'Examen no encontrado'
            }), 404
        
        nombre_examen = examen.nombre
        db.session.delete(examen)
        db.session.commit()
        
        socketio.emit('notificacion', {
            'titulo': 'Examen Eliminado',
            'mensaje': f'El examen "{nombre_examen}" ha sido eliminado.',
            'tipo': 'warning'
        }, room=f"paciente_{examen.usuario_id}")
        
        return jsonify({
            'success': True,
            'mensaje': f'Examen "{nombre_examen}" eliminado exitosamente'
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ======================== RUTAS DEL CHAT ========================

@main_bp.route('/mensajes/<int:paciente_id>', methods=['GET'])
@login_required
def obtener_mensajes(paciente_id):
    """Obtener el historial de mensajes de un paciente específico"""
    try:
        user_id = session.get('user_id')
        user_rol = session.get('rol')
        
        # Validación de seguridad: el paciente solo puede ver sus propios mensajes
        if user_rol != 'Tecnico' and user_id != paciente_id:
            return jsonify({'success': False, 'error': 'No autorizado'}), 403
            
        mensajes = Mensaje.query.filter_by(paciente_id=paciente_id).order_by(Mensaje.fecha.asc()).all()
        
        mensajes_list = [{
            'id': msg.id,
            'remitente_id': msg.remitente_id,
            'remitente_nombre': msg.remitente.nombre,
            'rol': 'Tecnico' if msg.remitente.rol in ['Tecnico', 'Técnico'] else 'Paciente',
            'contenido': msg.contenido,
            'fecha': msg.fecha.strftime('%Y-%m-%d %H:%M:%S')
        } for msg in mensajes]
        
        return jsonify({
            'success': True,
            'mensajes': mensajes_list
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ======================== RUTAS DE ARCHIVOS Y NOTIFICACIONES ========================

@main_bp.route('/examenes/<int:examen_id>/resultado', methods=['POST'])
@tecnico_required
def subir_resultado(examen_id):
    """Subir archivo de resultado para un examen"""
    try:
        examen = Examen.query.get(examen_id)
        if not examen:
            return jsonify({'success': False, 'error': 'Examen no encontrado'}), 404

        if 'archivo' not in request.files:
            return jsonify({'success': False, 'error': 'No se proporcionó ningún archivo'}), 400

        archivo = request.files['archivo']
        if archivo.filename == '':
            return jsonify({'success': False, 'error': 'Nombre de archivo vacío'}), 400

        # Crear directorio si no existe
        upload_folder = os.path.join(current_app.static_folder, 'uploads', 'resultados')
        os.makedirs(upload_folder, exist_ok=True)

        filename = secure_filename(f"{examen_id}_{archivo.filename}")
        file_path = os.path.join(upload_folder, filename)
        archivo.save(file_path)

        examen.archivo_resultado = filename
        examen.estado = 'Listo'
        
        # Crear notificación
        mensaje_notif = f'El resultado para tu examen "{examen.nombre}" ya está listo para descargar.'
        nueva_notif = Notificacion(
            usuario_id=examen.usuario_id,
            titulo='Resultado de Examen Listo',
            mensaje=mensaje_notif,
            tipo='success'
        )
        db.session.add(nueva_notif)
        db.session.commit()

        # Emitir por socket
        socketio.emit('notificacion', {
            'titulo': 'Resultado de Examen Listo',
            'mensaje': mensaje_notif,
            'tipo': 'success'
        }, room=f"paciente_{examen.usuario_id}")
        
        # Emitir evento para actualizar campanita
        socketio.emit('nueva_notificacion_data', {
            'id': nueva_notif.id,
            'titulo': nueva_notif.titulo,
            'mensaje': nueva_notif.mensaje,
            'tipo': nueva_notif.tipo,
            'fecha': nueva_notif.fecha_creacion.strftime('%Y-%m-%d %H:%M')
        }, room=f"paciente_{examen.usuario_id}")

        return jsonify({'success': True, 'mensaje': 'Resultado subido correctamente'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@main_bp.route('/notificaciones', methods=['GET'])
@login_required
def obtener_notificaciones():
    """Obtener notificaciones del usuario actual"""
    try:
        user_id = session.get('user_id')
        # Obtener notificaciones no leídas
        notificaciones = Notificacion.query.filter_by(usuario_id=user_id, leida=False).order_by(Notificacion.fecha_creacion.desc()).all()
        
        notif_list = [{
            'id': n.id,
            'titulo': n.titulo,
            'mensaje': n.mensaje,
            'tipo': n.tipo,
            'fecha': n.fecha_creacion.strftime('%Y-%m-%d %H:%M')
        } for n in notificaciones]
        
        return jsonify({'success': True, 'notificaciones': notif_list}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@main_bp.route('/notificaciones/<int:notificacion_id>/leer', methods=['PUT'])
@login_required
def marcar_notificacion_leida(notificacion_id):
    """Marcar una notificación como leída"""
    try:
        user_id = session.get('user_id')
        notificacion = Notificacion.query.get(notificacion_id)
        
        if not notificacion or notificacion.usuario_id != user_id:
            return jsonify({'success': False, 'error': 'Notificación no encontrada o sin acceso'}), 404
            
        notificacion.leida = True
        db.session.commit()
        return jsonify({'success': True}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500