from functools import wraps
from flask import session, redirect, url_for, flash, abort

def _normalize_role(role: str | None) -> str | None:
    if role is None:
        return None
    
    role = role.strip()
    if role.lower() in ('técnico', 'tecnico'):
        return 'Tecnico'
    if role.lower() == 'paciente':
        return 'Paciente'
    return role

def login_required(f):
    """
    Decorador para asegurar que el usuario haya iniciado sesión antes de acceder a la ruta.
    Redirige al login si no se encuentra 'user_id' en la sesión.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Por favor, inicia sesión para acceder a esta página.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(role):
    """
    Decorador para restringir el acceso a usuarios que tengan un rol específico (e.g., 'Tecnico', 'Paciente').
    Lanza un error HTTP 403 Forbidden si el rol no coincide.
    """
    allowed_roles = role if isinstance(role, (list, tuple, set)) else (role,)
    allowed_roles = {_normalize_role(r) for r in allowed_roles}

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Asegurar primero que esté autenticado
            if 'user_id' not in session:
                flash('Por favor, inicia sesión para acceder a esta página.', 'warning')
                return redirect(url_for('auth.login'))
            
            # Verificar el rol almacenado en la sesión
            current_role = _normalize_role(session.get('rol'))
            if current_role not in allowed_roles:
                flash('No tienes permisos para acceder a esta sección.', 'danger')
                return abort(403)
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def tecnico_required(f):
    """
    Decorador de conveniencia para rutas exclusivas de Técnicos.
    Equivale a @role_required('Tecnico').
    """
    return role_required({'Tecnico', 'Técnico'})(f)
