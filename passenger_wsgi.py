import sys

import os
os.environ["OPENBLAS_NUM_THREADS"] = "2"

INTERP = os.path.expanduser("/var/www/u1913510/data/www/kuycon.ru/venv/bin/python")
if sys.executable != INTERP:
   os.execl(INTERP, INTERP, *sys.argv)

sys.path.append(os.getcwd())

from app import app as application
# force debug mode
application.debug = True
from werkzeug.debug import DebuggedApplication
application.wsgi_app = DebuggedApplication(application.wsgi_app, True)
