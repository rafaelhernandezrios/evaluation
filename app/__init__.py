from flask import Flask
from flask_pymongo import PyMongo

mongo = None  # Definir variable global para MongoDB

def create_app():
    global mongo
    # Configuración de Flask con carpeta personalizada de templates
    app = Flask(__name__, template_folder="../templates",static_folder='../static')
    app.config.from_object("config.Config")
    
    # Inicialización de PyMongo
    mongo = PyMongo(app)

    # Registro del Blueprint
    from .routes import routes
    app.register_blueprint(routes)

    # Agregar `mongo` al contexto de la aplicación
    app.mongo = mongo

    return app
