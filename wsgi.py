#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'Michael Liao'

'''
A WSGI application.
'''

import os, logging

import locale; locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')

#from transwarp import i18n; i18n.install_i18n(); i18n.load_i18n('i18n/zh_cn.txt')
from transwarp import web, db, cache

from loader import load_user

def create_app(debug):
    if debug:
        import conf_dev as conf
    else:
        import conf_prod as conf
    logging.info('db conf: %s' % str(conf.db))
    logging.info('cache conf: %s' % str(conf.cache))
    # init db:
    db.init(db_type=conf.db['type'], db_schema=conf.db['schema'], \
        db_host=conf.db['host'], db_port=conf.db['port'], \
        db_user=conf.db['user'], db_password=conf.db['password'], \
        use_unicode=True, charset='utf8')
    # init cache:
    cache.client = cache.MemcacheClient(conf.cache.get('host', 'localhost:11211'))
    scan = ['auth', 'resume']
    if debug:
        scan.append('static_handler')
    return web.WSGIApplication(scan, \
            document_root=os.path.dirname(os.path.abspath(__file__)), \
            filters=(load_user, ), \
            template_engine='jinja2', \
            DEBUG=debug)
