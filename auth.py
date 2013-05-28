#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'Michael Liao'

' Auth module '

import os, re, time, base64, hashlib, logging, functools

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

from transwarp.web import ctx, view, get, post, route, Dict, Template, seeother, notfound, badrequest
from transwarp import db

from api import APIError, jsonresult, check_email, check_md5_passwd

_SESSION_COOKIE_NAME = '_auth_session_cookie_'
_SESSION_COOKIE_SALT = '_Auth-SalT_'
_SESSION_COOKIE_EXPIRES = 604800.0

@get('/auth/signin')
@view('templates/signin.html')
def signin():
    redirect = ctx.request.get('redirect', '')
    if not redirect:
        redirect = ctx.request.header('REFERER')
    if not redirect or redirect.find('/signin')!=(-1):
        redirect = '/'
    return dict(redirect=redirect)

@jsonresult
@post('/auth/signin')
def do_signin():
    i = ctx.request.input(email='', passwd='', remember='')
    email = i.email.strip().lower()
    passwd = i.passwd
    if not email:
        raise APIError('auth:failed', '', 'Bad email or password.')
    if not passwd:
        raise APIError('auth:failed', '', 'Bad email or password.')
    us = db.select('select * from users where email=?', email)
    if not us:
        raise APIError('auth:failed', '', 'Bad email or password.')
    u = us[0]
    if passwd != u.passwd:
        raise APIError('auth:failed', '', 'Bad email or password.')
    expires = None
    if i.remember:
        expires = time.time() + _SESSION_COOKIE_EXPIRES
    make_session_cookie(u.id, passwd, expires)
    # clear passwd:
    u.passwd = '******'
    return dict(redirect='/cv/%s' % u.id)

@get('/auth/signout')
def signout():
    delete_session_cookie()
    redirect = ctx.request.get('redirect', '')
    if not redirect:
        redirect = ctx.request.header('REFERER', '')
    if not redirect or redirect.find('/admin/')!=(-1) or redirect.find('/signin')!=(-1):
        redirect = '/'
    logging.debug('signed out and redirect to: %s' % redirect)
    raise seeother(redirect)

@get('/auth/register')
@view('/templates/register.html')
def register():
    return dict()

@jsonresult
@post('/auth/register')
def do_register():
    i = ctx.request.input(name='', email='', passwd='')

    name = i.name.strip()
    if not name:
        raise APIError('value', '', 'Invalid name.')

    email = i.email.strip().lower()
    check_email(email)

    passwd = i.passwd
    check_md5_passwd(passwd)

    us = db.select('select * from users where email=?', email)
    if us:
        raise APIError('register', '', 'Email already registered.')

    uid = db.next_str()
    db.insert('users', id=uid, name=name, email=email, passwd=passwd, version=0)

    make_session_cookie(uid, passwd)
    return {'id': uid}

def make_session_cookie(uid, passwd, expires=None):
    '''
    Generate a secure client session cookie by constructing: 
    base64(uid, expires, md5(uid, expires, passwd, salt)).
    
    Args:
        uid: user id.
        expires: unix-timestamp as float.
        passwd: user's password.
        salt: a secure string.
    Returns:
        base64 encoded cookie value as str.
    '''
    sid = str(uid)
    exp = str(int(expires)) if expires else str(int(time.time() + 86400))
    secure = ':'.join([sid, exp, str(passwd), _SESSION_COOKIE_SALT])
    cvalue = ':'.join([sid, exp, hashlib.md5(secure).hexdigest()])
    logging.info('make cookie: %s' % cvalue)
    cookie = base64.urlsafe_b64encode(cvalue).replace('=', '_')
    ctx.response.set_cookie(_SESSION_COOKIE_NAME, cookie, expires=expires)

def extract_session_cookie():
    '''
    Decode a secure client session cookie and return user object, or None if invalid cookie.

    Returns:
        user as object, or None if cookie is invalid.
    '''
    try:
        s = str(ctx.request.cookie(_SESSION_COOKIE_NAME, ''))
        logging.debug('read cookie: %s' % s)
        if not s:
            return None
        ss = base64.urlsafe_b64decode(s.replace('_', '=')).split(':')
        if len(ss)!=3:
            raise ValueError('bad cookie: %s' % s)
        uid, exp, md5 = ss
        if float(exp) < time.time():
            raise ValueError('expired cookie: %s' % s)
        user = db.select_one('select * from users where id=?', uid)
        expected_pwd = str(user.passwd)
        expected = ':'.join([uid, exp, expected_pwd, _SESSION_COOKIE_SALT])
        if hashlib.md5(expected).hexdigest()!=md5:
            raise ValueError('bad cookie: unexpected md5.')
        # clear password in memory:
        user.passwd = '******'
        return user
    except BaseException, e:
        logging.debug('something wrong when extract cookie: %s' % e.message)
        delete_session_cookie()
        return None

def delete_session_cookie():
    ' delete the session cookie immediately. '
    logging.debug('delete session cookie.')
    ctx.response.delete_cookie(_SESSION_COOKIE_NAME)
