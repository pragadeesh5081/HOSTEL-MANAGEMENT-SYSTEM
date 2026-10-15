import os
import sys

# Ensure the root directory of the repository is in Python's module search path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from app import create_app

# Vercel's Python runtime looks for WSGI callable named `app`
app = create_app()


class VercelPathFix:
    """WSGI middleware to translate Vercel rewrite paths to the original URL."""
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        matched = environ.get('HTTP_X_MATCHED_PATH') or environ.get('HTTP_X_FORWARDED_URI')
        if matched:
            environ['PATH_INFO'] = matched.split('?')[0] or '/'
        else:
            p = environ.get('PATH_INFO', '')
            for pre in ('/api/index', '/api'):
                if p.startswith(pre):
                    rem = p[len(pre):]
                    environ['PATH_INFO'] = rem if rem else '/'
                    break

        environ['SCRIPT_NAME'] = ''
        return self.wsgi_app(environ, start_response)


app.wsgi_app = VercelPathFix(app.wsgi_app)

