from app.models.usuario import db
from datetime import datetime

class Mensaje(db.Model):
    __tablename__ = 'mensajes'
    
    id = db.Column(db.Integer, primary_key=True)
    remitente_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    paciente_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    contenido = db.Column(db.Text, nullable=False)
    fecha = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Relaciones
    remitente = db.relationship('Usuario', foreign_keys=[remitente_id], backref=db.backref('mensajes_enviados', lazy=True))
    paciente_room = db.relationship('Usuario', foreign_keys=[paciente_id])
