from app.models.usuario import db
from datetime import datetime

class Examen(db.Model):
    __tablename__ = 'examenes'
    
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text, nullable=False)
    precio = db.Column(db.Float, nullable=False)
    tiempo_entrega = db.Column(db.String(50), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    fecha_creacion = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    estado = db.Column(db.String(20), nullable=False, default='Pendiente') # 'Pendiente', 'Listo'
    archivo_resultado = db.Column(db.String(255), nullable=True) # Ruta del archivo
    
    # Relación con Usuario
    usuario = db.relationship('Usuario', backref=db.backref('examenes', lazy=True))