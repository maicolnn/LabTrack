from flask import Blueprint, render_template, request, jsonify, session
from app.utils.decorators import login_required, tecnico_required
from app.models.usuario import db
from app.models.examen import Examen

main_bp = Blueprint('main', __name__)


# rutas de visualizacion

@main_bp.route('/dashboard')
@login_required
def dashboard():
    """Renderiza el dashboard con la lista de exámenes"""
    examenes = Examen.query.all()
    return render_template('dashboard.html', examenes=examenes)


# rutas crud examen

# read-obtener los examenes
@main_bp.route('/examenes', methods=['GET'])
@login_required
def obtener_examenes():
    
    try:
        examenes = Examen.query.all()
        examenes_list = [
            {
                'id': examen.id,
                'nombre': examen.nombre,
                'descripcion': examen.descripcion,
                'precio': examen.precio,
                'tiempo_entrega': examen.tiempo_entrega
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


# read obtener examen por id
@main_bp.route('/examenes/<int:examen_id>', methods=['GET'])
@login_required
def obtener_examen(examen_id):
    
    try:
        examen = Examen.query.get(examen_id)
        if not examen:
            return jsonify({
                'success': False,
                'error': 'Examen no encontrado'
            }), 404
        
        return jsonify({
            'success': True,
            'examen': {
                'id': examen.id,
                'nombre': examen.nombre,
                'descripcion': examen.descripcion,
                'precio': examen.precio,
                'tiempo_entrega': examen.tiempo_entrega
            }
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# create, crear nuevo examen, solo para rol técnico
@main_bp.route('/examenes', methods=['POST'])
@tecnico_required
def crear_examen():
   
    
    try:
        data = request.get_json()
        
        
        campos_requeridos = ['nombre', 'descripcion', 'precio', 'tiempo_entrega']
        for campo in campos_requeridos:
            if campo not in data or data[campo] is None or str(data[campo]).strip() == '':
                return jsonify({
                    'success': False,
                    'error': f'El campo "{campo}" es requerido'
                }), 400
        
        
        try:
            precio = float(data['precio'])
            if precio < 0:
                raise ValueError('El precio no puede ser negativo')
        except (ValueError, TypeError):
            return jsonify({
                'success': False,
                'error': 'El precio debe ser un número válido'
            }), 400
        
        
        nuevo_examen = Examen(
            nombre=data['nombre'].strip(),
            descripcion=data['descripcion'].strip(),
            precio=precio,
            tiempo_entrega=data['tiempo_entrega'].strip()
        )
        
        db.session.add(nuevo_examen)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'mensaje': 'Examen creado exitosamente',
            'examen': {
                'id': nuevo_examen.id,
                'nombre': nuevo_examen.nombre,
                'descripcion': nuevo_examen.descripcion,
                'precio': nuevo_examen.precio,
                'tiempo_entrega': nuevo_examen.tiempo_entrega
            }
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# update, actualizar examen, solo para rol tecnico
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
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'mensaje': 'Examen actualizado exitosamente',
            'examen': {
                'id': examen.id,
                'nombre': examen.nombre,
                'descripcion': examen.descripcion,
                'precio': examen.precio,
                'tiempo_entrega': examen.tiempo_entrega
            }
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# delete, eliminar examen, solo para rol tecnico
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