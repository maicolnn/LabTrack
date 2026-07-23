import os
import requests
from flask import Flask, Blueprint, render_template, request, redirect, url_for, flash, session, make_response
from flask_cors import CORS
from prometheus_flask_exporter import PrometheusMetrics

app = Flask(__name__, template_folder='app/templates', static_folder='app/static')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'clave_secreta_laboratorio_2026')

# Instrumentar métricas
metrics = PrometheusMetrics(app)

API_GATEWAY_URL = os.getenv('API_GATEWAY_URL', 'http://api-gateway:5000')

# Definir Blueprints
auth_bp = Blueprint('auth', __name__)
main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    if 'token' in request.cookies:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('auth.login'))

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        correo = request.form.get('correo')
        password = request.form.get('password')

        if not correo or not password:
            flash('Por favor ingresa correo y contraseña.', 'warning')
            return render_template('login.html')

        try:
            # Enviar credenciales al API Gateway
            res = requests.post(
                f"{API_GATEWAY_URL}/auth/login",
                json={'correo': correo, 'password': password},
                timeout=4
            )
            
            if res.status_code == 200:
                data = res.json()
                token = data.get('token')
                user_info = data.get('usuario', {})

                # Almacenar info en la sesión de Flask para la renderización de Jinja2
                session['user_id'] = user_info.get('id')
                session['rol'] = user_info.get('rol')
                session['user_name'] = user_info.get('nombre')

                flash(f'¡Bienvenido de nuevo, {user_info.get("nombre")}!', 'success')
                
                # Crear respuesta e inyectar el token en una cookie
                response = make_response(redirect(url_for('main.dashboard')))
                response.set_cookie('token', token, httponly=True, samesite='Lax')
                return response
            else:
                error_msg = res.json().get('error', 'Credenciales incorrectas.')
                flash(error_msg, 'danger')
                return render_template('login.html')
        except Exception as e:
            flash(f'Error al conectar con el servidor: {str(e)}', 'danger')
            return render_template('login.html')

    return render_template('login.html')

@auth_bp.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        cedula = request.form.get('cedula')
        nombre = request.form.get('nombre')
        correo = request.form.get('correo')
        password = request.form.get('password')
        rol = request.form.get('rol', 'Paciente')

        if not (cedula and nombre and correo and password):
            flash('Todos los campos son obligatorios.', 'warning')
            return render_template('registro.html')

        try:
            # Enviar registro al API Gateway
            res = requests.post(
                f"{API_GATEWAY_URL}/auth/registro",
                json={
                    'cedula': cedula,
                    'nombre': nombre,
                    'correo': correo,
                    'password': password,
                    'rol': rol
                },
                timeout=4
            )
            
            if res.status_code == 201:
                flash('Registro exitoso. ¡Ahora puedes iniciar sesión!', 'success')
                return redirect(url_for('auth.login'))
            else:
                error_msg = res.json().get('error', 'Error en el registro.')
                flash(error_msg, 'danger')
                return render_template('registro.html')
        except Exception as e:
            flash(f'Error al conectar con el servidor: {str(e)}', 'danger')
            return render_template('registro.html')

    return render_template('registro.html')

@auth_bp.route('/reseteo', methods=['GET', 'POST'])
def reseteo():
    return render_template('reseteo.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    response = make_response(redirect(url_for('auth.login')))
    response.delete_cookie('token')
    flash('Has cerrado sesión correctamente.', 'info')
    return response

@main_bp.route('/dashboard')
def dashboard():
    # Validar que el token exista en las cookies
    token = request.cookies.get('token')
    if not token:
        flash('Por favor, inicia sesión para acceder a esta página.', 'warning')
        return redirect(url_for('auth.login'))
    
    return render_template('dashboard.html')

@main_bp.route('/chat')
def chat():
    token = request.cookies.get('token')
    if not token:
        flash('Por favor, inicia sesión para acceder a esta página.', 'warning')
        return redirect(url_for('auth.login'))
    return render_template('chat.html')

# Registrar Blueprints
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(main_bp)

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5004))
    app.run(host='0.0.0.0', port=port, debug=False)

