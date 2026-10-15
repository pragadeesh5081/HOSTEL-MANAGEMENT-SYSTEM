import os
from flask import Flask
from config import Config
from models.db import close_db, init_db
from routes.auth_routes import auth_bp
from routes.student_routes import student_bp
from routes.admin_routes import admin_bp


def create_app():
    basedir = os.path.abspath(os.path.dirname(__file__))
    app = Flask(
        __name__,
        template_folder=os.path.join(basedir, 'templates'),
        static_folder=os.path.join(basedir, 'static')
    )
    app.config.from_object(Config)

    # Initialise the SQLite database (creates hms.db + tables on first run)
    with app.app_context():
        init_db()

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(admin_bp)

    # Date formatting filter
    @app.template_filter('format_date')
    def format_date(val, fmt='%b %d, %Y'):
        if not val:
            return ''
        if hasattr(val, 'strftime'):
            try:
                return val.strftime(fmt)
            except Exception:
                pass
        if isinstance(val, str):
            try:
                from datetime import datetime
                clean = val.strip().replace('Z', '')
                if 'T' in clean:
                    dt = datetime.fromisoformat(clean)
                elif ' ' in clean:
                    dt = datetime.strptime(clean.split('.')[0], '%Y-%m-%d %H:%M:%S')
                else:
                    dt = datetime.strptime(clean, '%Y-%m-%d')
                return dt.strftime(fmt)
            except Exception:
                return val[:10]
        return str(val)

    # Close the SQLite connection after every request
    app.teardown_appcontext(close_db)

    return app



app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
