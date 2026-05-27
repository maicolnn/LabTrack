from app.models.usuario import db

class Examen(db.Model):
    __tablename__ = 'examenes'
    
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text, nullable=False)
    precio = db.Column(db.Float, nullable=False)
    tiempo_entrega = db.Column(db.String(50), nullable=False)