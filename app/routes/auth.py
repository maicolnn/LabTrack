from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.models.usuario import db, Usuario

# Creamos el Blueprint para agrupar las rutas de autenticación
auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        correo = request.form.get('correo')
        password = request.form.get('password')

        # Validar que los campos no estén vacíos
        if not correo or not password:
            flash('Por favor ingresa correo y contraseña.', 'warning')
            return render_template('login.html')

        # Buscar usuario en la base de datos
        usuario = Usuario.query.filter_by(correo=correo).first()

        # Validar credenciales
        if usuario and usuario.check_password(password):
            # Guardar información en la sesión
            session['user_id'] = usuario.id
            session['rol'] = usuario.rol
            session['user_name'] = usuario.nombre
            
            flash(f'¡Bienvenido de nuevo, {usuario.nombre}!', 'success')
            return redirect(url_for('main.dashboard'))
        else:
            flash('Credenciales incorrectas. Por favor verifica tus datos.', 'danger')
            return render_template('login.html')

    return render_template('login.html')


@auth_bp.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        cedula = request.form.get('cedula')
        nombre = request.form.get('nombre')
        correo = request.form.get('correo')
        password = request.form.get('password')
        rol = request.form.get('rol', 'Paciente')  # Default a 'Paciente'

        # Validar campos requeridos
        if not (cedula and nombre and correo and password):
            flash('Todos los campos son obligatorios.', 'warning')
            return render_template('registro.html')

        # Verificar si el correo ya está registrado
        existing_user_email = Usuario.query.filter_by(correo=correo).first()
        if existing_user_email:
            flash('El correo electrónico ya está registrado.', 'danger')
            return render_template('registro.html')

        # Verificar si la cédula ya está registrada
        existing_user_cedula = Usuario.query.filter_by(cedula=cedula).first()
        if existing_user_cedula:
            flash('La cédula ya está registrada.', 'danger')
            return render_template('registro.html')

        # Crear y guardar nuevo usuario
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
            
            flash('Registro exitoso. ¡Ahora puedes iniciar sesión!', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            flash('Ocurrió un error al registrar al usuario. Inténtalo de nuevo.', 'danger')
            return render_template('registro.html')

    return render_template('registro.html')


@auth_bp.route('/reseteo', methods=['GET', 'POST'])
def reseteo():
    return render_template('reseteo.html')