#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'Michael Liao'

import re, json, logging, functools

from transwarp.web import ctx, get, post, forbidden, HttpError, Dict
from transwarp import db, cache

class APIError(StandardError):

    def __init__(self, error, data, message=''):
        super(APIError, self).__init__(message)
        self.error = error
        self.data = data
        self.message = message

def jsonresult(func):
    '''
    A decorator that makes a function return value as json.

    @jsonresult
    @post('/articles/create')
    def api_articles_create():
        return dict(id='123')
    '''
    @functools.wraps(func)
    def _wrapper(*args, **kw):
        ctx.response.content_type = 'application/json; charset=utf-8'
        try:
            return json.dumps(func(*args, **kw))
        except HttpError, e:
            ctx.response.content_type = None
            raise
        except APIError, e:
            return json.dumps(dict(error=e.error, data=e.data, message=e.message))
        except Exception, e:
            logging.exception('Error when calling api function.')
            return json.dumps(dict(error='server:error', data=e.__class__.__name__, message=e.message))
    return _wrapper

_RE_MD5 = re.compile(r'^[0-9a-f]{32}$')
#_RE_SHA1 = re.compile(r'^[0-9a-f]{40}$')

def check_md5_passwd(passwd):
    pw = str(passwd)
    if _RE_MD5.match(pw) is None:
        raise APIError('value', '', 'Invalid password.')
    return pw

_REG_EMAIL = re.compile(r'^[0-9a-z]([\-\.\w]*[0-9a-z])*\@([0-9a-z][\-\w]*[0-9a-z]\.)+[a-z]{2,9}$')

def check_email(email):
    '''
    Validate email address and return formated email.
    '''
    e = str(email).strip().lower()
    if _REG_EMAIL.match(e) is None:
        raise APIError('value', '', 'Invalid email address.')
    return e
 