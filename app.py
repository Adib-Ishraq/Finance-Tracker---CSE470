from flask import Flask
from flask_bootstrap import Bootstrap
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from flask_mail import Mail
from config import Config
from models import db, User
from routes import register_blueprints
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    Bootstrap(app)
    bcrypt = Bcrypt(app)
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    
    # Initialize Flask-Mail
    mail = Mail(app)

    # Initialize database
    db.init_app(app)
    
    with app.app_context():
        try:
            db.create_all()
            print("Database tables created successfully!")
        except Exception as e:
            print(f"Error creating database tables: {e}")

    # User loader
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
      # Register blueprints
    register_blueprints(app)
    
    # Register custom template filters
    @app.template_filter('month_abbr')
    def month_abbr_filter(month_number):
        import calendar
        return calendar.month_abbr[month_number]
  
    return app

if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)