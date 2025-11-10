"""
El módulo mail no tiene rutas (no es accesible vía web).
Es solo un servicio interno usado por otros módulos.
"""
from flask import Blueprint

mail_bp = Blueprint('mail', __name__)
