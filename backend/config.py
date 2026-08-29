from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_mail import Mail
from dotenv import load_dotenv
import os

load_dotenv()

# Serve built frontend from ../frontend/build when available so
# backend can provide a single URL for the whole app.
base_dir = os.path.dirname(os.path.abspath(__file__))
frontend_build = os.path.join(base_dir, '..', 'frontend', 'build')
app = Flask(__name__, static_folder=frontend_build, template_folder=frontend_build)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY')

# Mail config-To be used in a later version
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT'))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS') == 'True'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')

db = SQLAlchemy(app)
migrate = Migrate(app, db)
CORS(app, resources={r"/api/*": {"origins": ["http://localhost:3000", "https://bespoke-marzipan-63d200.netlify.app", "https://gym-management-system2.netlify.app"]}})
jwt = JWTManager(app)
mail = Mail(app)