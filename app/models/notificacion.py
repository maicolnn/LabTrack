from app.models.usuario import db
from datetime import datetime

class Notificacion(db.Model):
    __tablename__ = 'notificaciones'
    
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    titulo = db.Column(db.String(100), nullable=False)
    mensaje = db.Column(db.Text, nullable=False)
    tipo = db.Column(db.String(20), default='info') # 'info', 'success', 'warning', 'danger'
    leida = db.Column(db.Boolean, default=False)
    fecha_creacion = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Relación con Usuario
    usuario = db.relationship('Usuario', backref=db.backref('notificaciones', lazy=True))
