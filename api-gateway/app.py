import os
import requests
import jwt
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from prometheus_flask_exporter import PrometheusMetrics

app = Flask(__name__)
# Permitir CORS para desarrollo local y peticiones desde el Frontend
CORS(app, supports_credentials=True)

# Instrumentar métricas
metrics = PrometheusMetrics(app)

SECRET_KEY = os.getenv('SECRET_KEY', 'clave_secreta_laboratorio_2026')

# URL de los microservicios internos
AUTH_SERVICE_URL = os.getenv('AUTH_SERVICE_URL', 'http://auth-service:5001')
EXAMS_SERVICE_URL = os.getenv('EXAMS_SERVICE_URL', 'http://exams-service:5002')
COMM_SERVICE_URL = os.getenv('COMM_SERVICE_URL', 'http://communications-service:5003')

# Rutas públicas que no requieren autenticación JWT
PUBLIC_ROUTES = [
    '/auth/login',
    '/auth/registro'
]

def validar_jwt(token):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return {'error': 'El token ha expirado'}
    except jwt.InvalidTokenError:
        return {'error': 'Token inválido'}

def proxy_request(target_url, headers=None):
    """
    Reenvía la petición entrante al microservicio destino (Circuit Breaker básico).
    """
    if headers is None:
        headers = {}
    
    # Copiar headers del cliente útiles (excluyendo Host y Content-Length si cambia)
    for key, value in request.headers.items():
        if key.lower() not in ['host', 'content-length', 'content-type']:
            headers[key] = value

    # Mantener el Content-Type original si existe
    if request.headers.get('Content-Type'):
        headers['Content-Type'] = request.headers.get('Content-Type')

    method = request.method
    data = request.get_data()

    try:
        # Petición al microservicio con un timeout para evitar bloqueos
        response = requests.request(
            method=method,
            url=target_url,
            headers=headers,
            data=data,
            params=request.args,
            timeout=5  # Límite de tiempo (Circuit Breaker)
        )
        
        # Crear la respuesta de Flask a partir de la respuesta del microservicio
        excluded_headers = ['content-encoding', 'transfer-encoding', 'connection', 'keep-alive']
        resp_headers = [
            (name, value) for name, value in response.raw.headers.items()
            if name.lower() not in excluded_headers
        ]
        
        return Response(response.content, response.status_code, resp_headers)
        
    except requests.exceptions.Timeout:
        # Fallback del Circuit Breaker en caso de Timeout
        return jsonify({
            'success': False,
            'error': 'El servicio destino tardó demasiado en responder. Por favor intente más tarde.'
        }), 504
        
    except requests.exceptions.ConnectionError:
        # Fallback del Circuit Breaker si el servicio está caído
        return jsonify({
            'success': False,
            'error': 'El servicio temporalmente no está disponible. (Circuit Breaker activo)'
        }), 503

@app.before_request
def handle_routing():
    path = request.path
    
    # Evitar interceptar el endpoint de métricas de Prometheus
    if path == '/metrics':
        return None
    
    # 1. Verificar si la ruta es pública
    if path in PUBLIC_ROUTES:
        # Redirigir a auth-service directamente
        if path == '/auth/login':
            target_url = f"{AUTH_SERVICE_URL}/login"
        else:
            target_url = f"{AUTH_SERVICE_URL}/registro"
        return proxy_request(target_url)

    # 2. Validar JWT para rutas protegidas
    token = None
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        token = auth_header.split(" ")[1]
    else:
        # Intentar obtener del cookie 'token'
        token = request.cookies.get('token')
        
    if not token:
        return jsonify({'success': False, 'error': 'Acceso denegado. Token no proporcionado.'}), 401
    
    user_info = validar_jwt(token)
    
    if 'error' in user_info:
        return jsonify({'success': False, 'error': user_info['error']}), 401
    
    # 3. Inyectar cabeceras de identidad de usuario para los microservicios aguas abajo
    headers = {
        'X-User-Id': str(user_info.get('user_id')),
        'X-User-Role': str(user_info.get('rol')),
        'X-User-Name': str(user_info.get('nombre')),
        'X-User-Email': str(user_info.get('correo'))
    }

    # 4. Enrutamiento dinámico según el path
    if path.startswith('/auth'):
        # Quitar el prefijo /auth si el microservicio de auth no lo espera,
        # en nuestro caso, el blueprint de auth tiene prefijo /auth.
        target_url = f"{AUTH_SERVICE_URL}{path.replace('/auth', '', 1)}"
        return proxy_request(target_url, headers)
        
    elif path.startswith('/examenes') or path.startswith('/pacientes'):
        target_url = f"{EXAMS_SERVICE_URL}{path}"
        return proxy_request(target_url, headers)
        
    elif path.startswith('/mensajes') or path.startswith('/notificaciones'):
        target_url = f"{COMM_SERVICE_URL}{path}"
        return proxy_request(target_url, headers)

    # Si no coincide con ninguna regla de negocio
    return jsonify({'success': False, 'error': 'Ruta no encontrada en el Gateway.'}), 404

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
