from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
import os
import smtplib
import ssl
from email.message import EmailMessage
from itsdangerous import URLSafeTimedSerializer
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
    if request.method == 'POST':
        correo = request.form.get('correo')
        if not correo:
            flash('Por favor ingresa un correo válido.', 'warning')
            return render_template('reseteo.html')

        usuario = Usuario.query.filter_by(correo=correo).first()
        if not usuario:
            # No revelar si el correo existe por seguridad
            flash('Si el correo existe en nuestro sistema recibirás un enlace para restablecer la contraseña.', 'info')
            return render_template('reseteo.html')

        # Generar token firmado
        secret = current_app.config.get('SECRET_KEY') or os.environ.get('SECRET_KEY')
        serializer = URLSafeTimedSerializer(secret)
        token = serializer.dumps({'user_id': usuario.id}, salt='password-reset-salt')

        # Construir URL de reseteo
        reset_url = url_for('auth.reset_with_token', token=token, _external=True)

        # Enviar correo via SMTP (configurable por vars de entorno)
        try:
            smtp_host = current_app.config.get('SMTP_HOST') or os.environ.get('SMTP_HOST')
            smtp_port = int(current_app.config.get('SMTP_PORT') or os.environ.get('SMTP_PORT') or 587)
            smtp_user = current_app.config.get('SMTP_USER') or os.environ.get('SMTP_USER')
            smtp_pass = current_app.config.get('SMTP_PASS') or os.environ.get('SMTP_PASS')
            smtp_use_tls = (current_app.config.get('SMTP_USE_TLS') or os.environ.get('SMTP_USE_TLS') or 'true').lower() in ['1','true','yes']

            if not smtp_host or not smtp_user or not smtp_pass:
                raise RuntimeError('SMTP no configurado. Por favor configure SMTP_HOST/SMTP_USER/SMTP_PASS en variables de entorno.')

            subject = 'Recuperación de contraseña - LabTrack'
            body = f'Hola {usuario.nombre},\n\nSe ha solicitado restablecer tu contraseña. Haz clic en el siguiente enlace (válido 1 hora):\n\n{reset_url}\n\nSi no solicitaste esto, ignora este mensaje.'

            msg = EmailMessage()
            msg['Subject'] = subject
            msg['From'] = smtp_user
            msg['To'] = usuario.correo
            msg.set_content(body)

            if smtp_use_tls:
                context = ssl.create_default_context()
                with smtplib.SMTP(smtp_host, smtp_port) as server:
                    server.starttls(context=context)
                    server.login(smtp_user, smtp_pass)
                    server.send_message(msg)
            else:
                with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
                    server.login(smtp_user, smtp_pass)
                    server.send_message(msg)

            flash('Si el correo existe en nuestro sistema recibirás un enlace para restablecer la contraseña.', 'info')
            return render_template('reseteo.html')
        except Exception as e:
            current_app.logger.exception('Error enviando correo de reseteo')
            flash('Ocurrió un error al intentar enviar el correo de reseteo. Revisa la configuración SMTP.', 'danger')
            return render_template('reseteo.html')

    return render_template('reseteo.html')


@auth_bp.route('/reseteo/<token>', methods=['GET', 'POST'])
def reset_with_token(token):
    """Validar token y permitir establecer nueva contraseña."""
    secret = current_app.config.get('SECRET_KEY') or os.environ.get('SECRET_KEY')
    serializer = URLSafeTimedSerializer(secret)
    try:
        data = serializer.loads(token, salt='password-reset-salt', max_age=3600)
        user_id = data.get('user_id')
    except Exception:
        flash('Enlace inválido o expirado. Solicita un nuevo reseteo.', 'danger')
        return redirect(url_for('auth.reseteo'))

    usuario = Usuario.query.get(user_id)
    if not usuario:
        flash('Usuario no encontrado.', 'danger')
        return redirect(url_for('auth.reseteo'))

    if request.method == 'POST':
        password = request.form.get('password')
        password2 = request.form.get('password2')
        if not password or not password2 or password != password2:
            flash('Las contraseñas no coinciden o están vacías.', 'warning')
            return render_template('reseteo_confirm.html', token=token)

        usuario.set_password(password)
        db.session.commit()
        flash('Contraseña restablecida correctamente. Ahora puedes iniciar sesión.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('reseteo_confirm.html', token=token)


@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('Has cerrado sesión correctamente.', 'info')
    return redirect(url_for('auth.login'))