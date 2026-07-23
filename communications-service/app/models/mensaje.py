from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Mensaje(db.Model):
    __tablename__ = 'mensajes'
    
    id = db.Column(db.Integer, primary_key=True)
    remitente_id = db.Column(db.Integer, nullable=False)
    paciente_id = db.Column(db.Integer, nullable=False)
    contenido = db.Column(db.Text, nullable=False)
    fecha = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'remitente_id': self.remitente_id,
            'paciente_id': self.paciente_id,
            'contenido': self.contenido,
            'fecha': self.fecha.strftime('%Y-%m-%d %H:%M:%S') if self.fecha else ''
        }
