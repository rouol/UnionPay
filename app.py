import os
from flask import Flask
from flask_assets import Environment, Bundle
from flask_sqlalchemy import SQLAlchemy
from flask_breadcrumbs import Breadcrumbs
from flask_caching import Cache
from flask_compress import Compress

import config

class ReverseProxied(object):
    '''Wrap the application in this middleware and configure the 
    front-end server to add these headers, to let you quietly bind 
    this to a URL other than / and to an HTTP scheme that is 
    different than what is used locally.

    In nginx:
    location /prefix {
        proxy_pass http://127.0.0.1:5006;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Scheme $scheme;
        proxy_set_header X-Script-Name /prefix;
        }

    :param app: the WSGI application
    '''
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        script_name = environ.get('HTTP_X_SCRIPT_NAME', '')
        if script_name:
            environ['SCRIPT_NAME'] = script_name
            path_info = environ['PATH_INFO']
            if path_info.startswith(script_name):
                environ['PATH_INFO'] = path_info[len(script_name):]

        scheme = environ.get('HTTP_X_SCHEME', '')
        if scheme:
            environ['wsgi.url_scheme'] = scheme
        return self.app(environ, start_response)


app = Flask(__name__, instance_relative_config=True)
app.wsgi_app = ReverseProxied(app.wsgi_app)
# app.secret_key = config.SECRET_KEY
# file_path = os.path.abspath(os.getcwd())+'/'+config.DB_PATH
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///'+file_path
Breadcrumbs(app=app)
# app.config['CACHE_TYPE'] = 'simple'
# app.config['CACHE_DEFAULT_TIMEOUT'] = 300
# cache = Cache(app=app)
app.config['COMPRESS_MIMETYPES'] = ['text/html', 'text/css', 'text/xml', 'application/json', 'application/javascript']
Compress(app=app)

# assets = Environment(app)
# assets.url = app.static_url_path
# scss = Bundle(
#     "assets/main.scss",
#     filters="libsass",
#     output="css/scss-generated.css"
# )
# assets.register("scss_all", scss)

# db = SQLAlchemy(app)

from views import *

if __name__ == '__main__':
    app.run(host=config.FLASK_APP_HOST, port=config.FLASK_APP_PORT, debug=True, threaded=True)