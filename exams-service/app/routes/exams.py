import os
import requests
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
from app.models.examen import db, Examen

exams_bp = Blueprint('exams', __name__)

AUTH_SERVICE_URL = os.getenv('AUTH_SERVICE_URL', 'http://auth-service:5001')
COMM_SERVICE_URL = os.getenv('COMM_SERVICE_URL', 'http://communications-service:5003')

def get_usuario_info(usuario_id):
    """Obtiene información del usuario desde el auth-service."""
    try:
        res = requests.get(f"{AUTH_SERVICE_URL}/usuarios/{usuario_id}", timeout=2)
        if res.status_code == 200:
            data = res.json()
            if data.get('success'):
                return data.get('usuario')
    except Exception as e:
        print(f"Error calling auth-service: {e}")
    return None

def enviar_notificacion(usuario_id, titulo, mensaje, tipo='info'):
    """Envía una notificación al communications-service."""
    try:
        payload = {
            'usuario_id': usuario_id,
            'titulo': titulo,
            'mensaje': mensaje,
            'tipo': tipo
        }
        res = requests.post(f"{COMM_SERVICE_URL}/notificaciones/crear", json=payload, timeout=2)
        return res.status_code == 201
    except Exception as e:
        print(f"Error calling communications-service: {e}")
        return False

# Auxiliar para técnicos: obtener pacientes
@exams_bp.route('/pacientes', methods=['GET'])
def obtener_pacientes():
    user_rol = request.headers.get('X-User-Role')
    if user_rol != 'Tecnico':
        return jsonify({'success': False, 'error': 'No autorizado'}), 403
    
    try:
        res = requests.get(f"{AUTH_SERVICE_URL}/usuarios?rol=Paciente", timeout=2)
        if res.status_code == 200:
            data = res.json()
            return jsonify({
                'success': True,
                'pacientes': data.get('usuarios', []),
                'total': len(data.get('usuarios', []))
            }), 200
        return jsonify({'success': False, 'error': 'No se pudo obtener la lista de pacientes'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# READ - Obtener exámenes
@exams_bp.route('/examenes', methods=['GET'])
def obtener_examenes():
    try:
        user_id = request.headers.get('X-User-Id')
        user_rol = request.headers.get('X-User-Role')
        
        if not user_id:
            return jsonify({'success': False, 'error': 'No autenticado'}), 401
        
        user_id = int(user_id)
        
        if user_rol == 'Tecnico':
            examenes = Examen.query.all()
        else:
            examenes = Examen.query.filter_by(usuario_id=user_id).all()
        
        examenes_list = []
        # Cache local simple para no repetir llamadas de red para el mismo paciente
        usuarios_cache = {}

        for examen in examenes:
            uid = examen.usuario_id
            if uid not in usuarios_cache:
                u_info = get_usuario_info(uid)
                usuarios_cache[uid] = u_info.get('nombre') if u_info else 'Sin asignar'
            
            examenes_list.append({
                'id': examen.id,
                'nombre': examen.nombre,
                'descripcion': examen.descripcion,
                'precio': examen.precio,
                'tiempo_entrega': examen.tiempo_entrega,
                'usuario_id': examen.usuario_id,
                'usuario_nombre': usuarios_cache[uid],
                'fecha_creacion': examen.fecha_creacion.strftime('%Y-%m-%d %H:%M') if examen.fecha_creacion else '',
                'estado': examen.estado,
                'archivo_resultado': f"/static/uploads/resultados/{examen.archivo_resultado}" if examen.archivo_resultado else None
            })
            
        return jsonify({
            'success': True,
            'examenes': examenes_list,
            'total': len(examenes_list)
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# READ - Obtener un examen específico
@exams_bp.route('/examenes/<int:examen_id>', methods=['GET'])
def obtener_examen(examen_id):
    try:
        user_id = request.headers.get('X-User-Id')
        user_rol = request.headers.get('X-User-Role')
        
        if not user_id:
            return jsonify({'success': False, 'error': 'No autenticado'}), 401
        
        user_id = int(user_id)
        
        examen = Examen.query.get(examen_id)
        if not examen:
            return jsonify({'success': False, 'error': 'Examen no encontrado'}), 404
        
        if user_rol != 'Tecnico' and examen.usuario_id != user_id:
            return jsonify({'success': False, 'error': 'No tienes acceso a este examen'}), 403
        
        u_info = get_usuario_info(examen.usuario_id)
        usuario_nombre = u_info.get('nombre') if u_info else 'Sin asignar'
        
        return jsonify({
            'success': True,
            'examen': {
                'id': examen.id,
                'nombre': examen.nombre,
                'descripcion': examen.descripcion,
                'precio': examen.precio,
                'tiempo_entrega': examen.tiempo_entrega,
                'usuario_id': examen.usuario_id,
                'usuario_nombre': usuario_nombre,
                'fecha_creacion': examen.fecha_creacion.strftime('%Y-%m-%d %H:%M') if examen.fecha_creacion else '',
                'estado': examen.estado,
                'archivo_resultado': f"/static/uploads/resultados/{examen.archivo_resultado}" if examen.archivo_resultado else None
            }
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# CREATE - Crear examen
@exams_bp.route('/examenes', methods=['POST'])
def crear_examen():
    user_rol = request.headers.get('X-User-Role')
    if user_rol != 'Tecnico':
        return jsonify({'success': False, 'error': 'No autorizado'}), 403
        
    try:
        data = request.get_json() or {}
        campos_requeridos = ['nombre', 'descripcion', 'precio', 'tiempo_entrega', 'usuario_id']
        for campo in campos_requeridos:
            if campo not in data or data[campo] is None or str(data[campo]).strip() == '':
                return jsonify({'success': False, 'error': f'El campo "{campo}" es requerido'}), 400
        
        try:
            precio = float(data['precio'])
            if precio < 0:
                return jsonify({'success': False, 'error': 'El precio no puede ser negativo'}), 400
        except (ValueError, TypeError):
            return jsonify({'success': False, 'error': 'El precio debe ser un número válido'}), 400
            
        try:
            usuario_id = int(data['usuario_id'])
            u_info = get_usuario_info(usuario_id)
            if not u_info:
                return jsonify({'success': False, 'error': 'El paciente no existe'}), 400
            if u_info.get('rol') != 'Paciente':
                return jsonify({'success': False, 'error': 'Solo puedes asignar exámenes a pacientes'}), 400
        except (ValueError, TypeError):
            return jsonify({'success': False, 'error': 'ID de usuario inválido'}), 400
            
        nuevo_examen = Examen(
            nombre=data['nombre'].strip(),
            descripcion=data['descripcion'].strip(),
            precio=precio,
            tiempo_entrega=data['tiempo_entrega'].strip(),
            usuario_id=usuario_id
        )
        
        db.session.add(nuevo_examen)
        db.session.commit()
        
        # Enviar notificación en tiempo real a través del servicio de comunicaciones
        enviar_notificacion(
            usuario_id=usuario_id,
            titulo='Nuevo Examen',
            mensaje=f'Te han asignado un nuevo examen: {nuevo_examen.nombre}',
            tipo='success'
        )
        
        return jsonify({
            'success': True,
            'mensaje': 'Examen creado exitosamente',
            'examen': nuevo_examen.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


# UPDATE - Actualizar examen
@exams_bp.route('/examenes/<int:examen_id>', methods=['PUT', 'POST'])
def actualizar_examen(examen_id):
    user_rol = request.headers.get('X-User-Role')
    if user_rol != 'Tecnico':
        return jsonify({'success': False, 'error': 'No autorizado'}), 403
        
    try:
        examen = Examen.query.get(examen_id)
        if not examen:
            return jsonify({'success': False, 'error': 'Examen no encontrado'}), 404
            
        data = request.get_json() or {}
        
        if 'nombre' in data:
            if not data['nombre'] or str(data['nombre']).strip() == '':
                return jsonify({'success': False, 'error': 'El nombre no puede estar vacío'}), 400
            examen.nombre = data['nombre'].strip()
            
        if 'descripcion' in data:
            if not data['descripcion'] or str(data['descripcion']).strip() == '':
                return jsonify({'success': False, 'error': 'La descripción no puede estar vacía'}), 400
            examen.descripcion = data['descripcion'].strip()
            
        if 'precio' in data:
            try:
                precio = float(data['precio'])
                if precio < 0:
                    return jsonify({'success': False, 'error': 'El precio no puede ser negativo'}), 400
                examen.precio = precio
            except (ValueError, TypeError):
                return jsonify({'success': False, 'error': 'El precio debe ser un número válido'}), 400
                
        if 'tiempo_entrega' in data:
            if not data['tiempo_entrega'] or str(data['tiempo_entrega']).strip() == '':
                return jsonify({'success': False, 'error': 'El tiempo de entrega no puede estar vacío'}), 400
            examen.tiempo_entrega = data['tiempo_entrega'].strip()
            
        if 'usuario_id' in data:
            try:
                usuario_id = int(data['usuario_id'])
                u_info = get_usuario_info(usuario_id)
                if not u_info:
                    return jsonify({'success': False, 'error': 'El paciente no existe'}), 400
                if u_info.get('rol') != 'Paciente':
                    return jsonify({'success': False, 'error': 'Solo puedes asignar exámenes a pacientes'}), 400
                examen.usuario_id = usuario_id
            except (ValueError, TypeError):
                return jsonify({'success': False, 'error': 'ID de usuario inválido'}), 400
                
        db.session.commit()
        
        enviar_notificacion(
            usuario_id=examen.usuario_id,
            titulo='Examen Actualizado',
            mensaje=f'El examen "{examen.nombre}" ha sido actualizado.',
            tipo='info'
        )
        
        return jsonify({
            'success': True,
            'mensaje': 'Examen actualizado exitosamente',
            'examen': examen.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


# DELETE - Eliminar examen
@exams_bp.route('/examenes/<int:examen_id>', methods=['DELETE'])
def eliminar_examen(examen_id):
    user_rol = request.headers.get('X-User-Role')
    if user_rol != 'Tecnico':
        return jsonify({'success': False, 'error': 'No autorizado'}), 403
        
    try:
        examen = Examen.query.get(examen_id)
        if not examen:
            return jsonify({'success': False, 'error': 'Examen no encontrado'}), 404
            
        nombre_examen = examen.nombre
        usuario_id = examen.usuario_id
        
        db.session.delete(examen)
        db.session.commit()
        
        enviar_notificacion(
            usuario_id=usuario_id,
            titulo='Examen Eliminado',
            mensaje=f'El examen "{nombre_examen}" ha sido eliminado.',
            tipo='warning'
        )
        
        return jsonify({
            'success': True,
            'mensaje': f'Examen "{nombre_examen}" eliminado exitosamente'
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


# Upload result file
@exams_bp.route('/examenes/<int:examen_id>/resultado', methods=['POST'])
def subir_resultado(examen_id):
    user_rol = request.headers.get('X-User-Role')
    if user_rol != 'Tecnico':
        return jsonify({'success': False, 'error': 'No autorizado'}), 403
        
    try:
        examen = Examen.query.get(examen_id)
        if not examen:
            return jsonify({'success': False, 'error': 'Examen no encontrado'}), 404
            
        if 'archivo' not in request.files:
            return jsonify({'success': False, 'error': 'No se proporcionó ningún archivo'}), 400
            
        archivo = request.files['archivo']
        if archivo.filename == '':
            return jsonify({'success': False, 'error': 'Nombre de archivo vacío'}), 400
            
        # Directorio de subida
        upload_folder = current_app.config['UPLOAD_FOLDER']
        os.makedirs(upload_folder, exist_ok=True)
        
        filename = secure_filename(f"{examen_id}_{archivo.filename}")
        file_path = os.path.join(upload_folder, filename)
        archivo.save(file_path)
        
        examen.archivo_resultado = filename
        examen.estado = 'Listo'
        db.session.commit()
        
        enviar_notificacion(
            usuario_id=examen.usuario_id,
            titulo='Resultado de Examen Listo',
            mensaje=f'El resultado para tu examen "{examen.nombre}" ya está listo para descargar.',
            tipo='success'
        )
        
        return jsonify({'success': True, 'mensaje': 'Resultado subido correctamente'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
