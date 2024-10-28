import os
import hashlib
import datetime
from json import loads, dumps
from uuid import uuid4

from flask import flash, jsonify, render_template, request, session, redirect, url_for, send_from_directory
from flask_breadcrumbs import register_breadcrumb
from flask_sitemapper import Sitemapper

from app import app
import service

sitemapper = Sitemapper()
sitemapper.init_app(app)

@sitemapper.include(lastmod=datetime.datetime.now().strftime('%Y-%m-%d'))
@app.route('/')
@register_breadcrumb(app, '.', 'Главная')
async def home():
    service.update_data()
    exchange_rate_list_main, exchange_rate_list = service.get_exchange_rate_list('RUB')
    data = {
        'exchange_rate_list': exchange_rate_list,
        'exchange_rate_list_main': exchange_rate_list_main,
        'unionpay_update_time': service.get_unionpay_update_time(),
        'cbr_update_time': service.get_cbr_update_time(),
    }
    return render_template('pages/home.html', section='home', title='Главная', data=data)

# serve content from /static/ico folder to /
@app.route('/<path:path>')
async def send_ico(path):
    return send_from_directory('static/ico', path)