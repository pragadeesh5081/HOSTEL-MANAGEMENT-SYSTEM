import os
import sys

# Ensure the root directory of the repository is in Python's module search path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from app import create_app

# Vercel's Python runtime looks for WSGI callable named `app`
app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
