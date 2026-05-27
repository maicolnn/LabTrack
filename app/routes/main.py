from flask import Blueprint, render_template
from app.utils.decorators import login_required

main_bp = Blueprint('main', __name__)


@main_bp.route('/dashboard')
@login_required
def dashboard():
    # Aquí el encargado del CRUD listará los exámenes y el chat
    return render_template('dashboard.html')