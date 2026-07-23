import os
from app import create_app
from app.extensions import socketio

app = create_app()

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5003))
    # Para habilitar WebSockets en Flask-SocketIO en Docker, se corre mediante socketio.run
    socketio.run(app, host='0.0.0.0', port=port, debug=False, allow_unsafe_werkzeug=True)
