from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Notificacion(db.Model):
    __tablename__ = 'notificaciones'
    
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, nullable=False)
    titulo = db.Column(db.String(100), nullable=False)
    mensaje = db.Column(db.Text, nullable=False)
    tipo = db.Column(db.String(20), default='info') # 'info', 'success', 'warning', 'danger'
    leida = db.Column(db.Boolean, default=False)
    fecha_creacion = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'usuario_id': self.usuario_id,
            'titulo': self.titulo,
            'mensaje': self.mensaje,
            'tipo': self.tipo,
            'leida': self.leida,
            'fecha_creacion': self.fecha_creacion.strftime('%Y-%m-%d %H:%M') if self.fecha_creacion else ''
        }
