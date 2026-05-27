from flask import Blueprint, render_template, request, redirect, url_for

# Creamos el Blueprint para agrupar las rutas de autenticación
auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Aquí el encargado de Autenticación pondrá su lógica de verificar hash
        return redirect(url_for('main.dashboard'))
    return render_template('login.html')


@auth_bp.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        # Aquí se pondrá la lógica de guardar usuario encriptado
        return redirect(url_for('auth.login'))
    return render_template('registro.html')


@auth_bp.route('/reseteo', methods=['GET', 'POST'])
def reseteo():
    return render_template('reseteo.html')