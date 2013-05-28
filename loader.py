#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'Michael Liao'

' Loader module that load modules dynamic. '

import os, logging, functools

from transwarp.web import ctx, forbidden, notfound
from transwarp import db, i18n

from auth import extract_session_cookie

def load_user(func):
    @functools.wraps(func)
    def _wrapper(*args, **kw):
        user = extract_session_cookie()
        logging.info('bind ctx.user')
        ctx.user = user
        try:
            return func(*args, **kw)
        finally:
            del ctx.user
    return _wrapper

def load_i18n(func):
    @functools.wraps(func)
    def _wrapper(*args, **kw):
        lc = 'en'
        al = ctx.request.header('ACCEPT-LANGUAGE')
        if al:
            lcs = al.split(',')
            lc = lcs[0].strip().lower()
        with i18n.locale(lc):
            return func(*args, **kw)
    return _wrapper
