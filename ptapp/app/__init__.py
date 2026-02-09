from flask import Flask
from .config import Config
from .extensions import db
from .main.routes import main_bp
from app.journal.routes import journal_bp
from app.backtest.routes import backtest_bp
from app.planner.routes import planner_bp

def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(Config)

    db.init_app(app)
    
    from flask_login import LoginManager
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)
    
    from app.models import User
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    app.register_blueprint(main_bp)
    app.register_blueprint(journal_bp, url_prefix='/journal')
    app.register_blueprint(backtest_bp, url_prefix='/backtest')
    app.register_blueprint(planner_bp) # url prefix handles inside
    from app.analytics import analytics_bp
    app.register_blueprint(analytics_bp, url_prefix='/analytics')
    from app.auth.routes import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    return app
