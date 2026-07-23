from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Examen(db.Model):
    __tablename__ = 'examenes'
    
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text, nullable=False)
    precio = db.Column(db.Float, nullable=False)
    tiempo_entrega = db.Column(db.String(50), nullable=False)
    usuario_id = db.Column(db.Integer, nullable=False)  # ID lógico del paciente
    fecha_creacion = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    estado = db.Column(db.String(20), nullable=False, default='Pendiente') # 'Pendiente', 'Listo'
    archivo_resultado = db.Column(db.String(255), nullable=True) # Nombre del archivo resultado

    def to_dict(self):
        return {
            'id': self.id,
            'nombre': self.nombre,
            'descripcion': self.descripcion,
            'precio': self.precio,
            'tiempo_entrega': self.tiempo_entrega,
            'usuario_id': self.usuario_id,
            'fecha_creacion': self.fecha_creacion.strftime('%Y-%m-%d %H:%M') if self.fecha_creacion else '',
            'estado': self.estado,
            'archivo_resultado': self.archivo_resultado
        }
