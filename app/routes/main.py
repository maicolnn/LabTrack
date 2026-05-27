from flask import Blueprint, render_template

main_bp = Blueprint('main', __name__)


@main_bp.route('/dashboard')
def dashboard():
    # Aquí el encargado del CRUD listará los exámenes y el chat
    return render_template('dashboard.html')