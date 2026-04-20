import sys, os

# Activate the virtualenv — update path if Python version changes
venv_path = '/home/mofengco/virtualenv/jobs.mof-eng.com/3.11/lib/python3.11/site-packages'
sys.path.insert(0, venv_path)

# Set app directory
app_dir = '/home/mofengco/jobs.mof-eng.com'
sys.path.insert(0, app_dir)
os.chdir(app_dir)

os.environ['FLASK_ENV'] = 'production'

from app import create_app
application = create_app('production')
