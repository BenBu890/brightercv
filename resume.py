#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'Michael Liao'

' Resume module '

import os, re, json, time, base64, hashlib, logging, functools

from transwarp.web import ctx, view, get, post, route, Dict, Template, seeother, notfound, badrequest
from transwarp import db

from api import APIError, jsonresult, check_email, check_md5_passwd

# (kind, name, style)
_SECTIONS = (
    (u'about',          u'About',          u'li'   ),
    (u'summary',        u'Summary',        u'text' ),
    (u'experience',     u'Experience',     u'entry'),
    (u'skills',         u'Skills',         u'entry'),
    (u'languages',      u'Languages',      u'entry'),
    (u'education',      u'Education',      u'entry'),
    (u'publications',   u'Publications',   u'entry'),
    (u'certifications', u'Certifications', u'entry'),
    (u'patents',        u'Patents',        u'entry'),
)

_SECTIONS_DICT = dict([(s[0], s[1]) for s in _SECTIONS])
_SECTIONS_TUPLE = tuple([s[0] for s in _SECTIONS])
_SECTIONS_SET = frozenset(_SECTIONS_TUPLE)
_SECTIONS_STYLE = dict([(s[0], s[2]) for s in _SECTIONS])

def get_default_cv(uid):
    cvs = None
    while not cvs:
        cvs = db.select('select * from resumes where user_id=?', uid)
        if not cvs:
            cv_id = db.next_str()
            db.insert('resumes', id=cv_id, user_id=uid, title='My Resume', version=0)
            db.insert('sections', id=db.next_str(), user_id=uid, resume_id=cv_id, display_order=0, kind='about', title='About', description='', version=0)

    cv = cvs[0]
    cv.sections = db.select('select * from sections where resume_id=? order by display_order', cv.id)
    for section in cv.sections:
        section.style = _SECTIONS_STYLE[section.kind]
        section.entries = db.select('select * from entries where section_id=? order by display_order', section.id)
    return cv

def cv_by_user(uid):
    target_user = db.select_one('select * from users where id=?', uid)
    cv = get_default_cv(uid)
    return dict(cv=cv, user=ctx.user, target=target_user, editable=ctx.user and ctx.user.id==uid)

@get('/')
@view('templates/index.html')
def home():
    return dict(user=ctx.user)

@get('/cv/<uid>')
@view('templates/resume.html')
def cv(uid):
    return cv_by_user(uid)

@get('/u/<path>')
@view('templates/resume.html')
def shortcut(path):
    s = db.select_one('select * from shortcuts where path=?', path)
    return cv_by_user(s.user_id)

@get('/print/<uid>')
@view('templates/print.html')
def print_cv(uid):
    return cv_by_user(uid)

@jsonresult
@post('/resumes/update')
def update_resume():
    _check_user()
    i = ctx.request.input(id='', title='')
    if not i.id:
        raise APIError('value', 'id', 'id is empty.')
    title = i.title.strip()
    if not title:
        raise APIError('value', 'title', 'title is empty')
    cv = get_default_cv(ctx.user.id)
    _check_user_id(cv.user_id)
    db.update('update resumes set title=?, version=version+1 where id=?', title, cv.id)
    return dict(result=True)

@jsonresult
@post('/sections/add/list')
def sections_for_add():
    _check_user()
    cv = get_default_cv(ctx.user.id)
    L = list(_SECTIONS_TUPLE)
    for s in cv.sections:
        if s.kind in L:
            L.remove(s.kind)
    return [(key, _SECTIONS_DICT[key]) for key in L]

@jsonresult
@post('/sections/add')
def add_section():
    _check_user()
    i = ctx.request.input(kind='', title='', description='')
    kind = i.kind
    if not kind in _SECTIONS_SET:
        raise APIError('value', 'kind', 'Invalid kind.')
    title = i.title.strip()
    if not title:
        title = _SECTIONS_DICT.get(kind)
    description = i.description.strip()

    cv = get_default_cv(ctx.user.id)
    for s in cv.sections:
        if s.kind==kind:
            raise APIError('value', '', 'Section exist.')
    next_id = db.next_str()
    db.insert('sections', id=next_id, user_id=ctx.user.id, resume_id=cv.id, display_order=len(cv.sections), kind=kind, title=title, description=description, version=0)
    return dict(id=next_id, kind=kind, title=title, description=description)

@jsonresult
@post('/sections/update')
def update_section():
    _check_user()
    i = ctx.request.input(id='', title='', description='')
    if not i.id:
        raise APIError('value', 'id', 'id is empty.')
    title = i.title.strip()
    description = i.description.strip()
    if not title:
        raise APIError('value', 'title', 'title is empty')
    section = db.select_one('select * from sections where id=?', i.id)
    _check_user_id(section.user_id)
    db.update('update sections set title=?, description=?, version=version+1 where id=?', title, description, section.id)
    db.update('update resumes set version=version+1 where id=?', section.resume_id)
    return dict(result=True)

@jsonresult
@post('/sections/delete')
def delete_section():
    _check_user()
    i = ctx.request.input(id='')
    if not i.id:
        raise APIError('value', 'id', 'id is empty.')
    section = db.select_one('select * from sections where id=?', i.id)
    _check_user_id(section.user_id)
    cv = get_default_cv(ctx.user.id)
    sections = db.select('select * from sections where resume_id=? order by display_order', cv.id)
    display_ids = [s.id for s in sections if s.id != i.id]
    db.update('delete from entries where section_id=?', i.id)
    db.update('delete from sections where id=?', i.id)
    n = 0
    for i in display_ids:
        db.update('update sections set display_order=? where id=?', n, i)
    db.update('update resumes set version=version+1 where id=?', cv.id)
    return dict(result=True)

@jsonresult
@post('/entries/add')
def add_entry():
    _check_user()
    i = ctx.request.input(id='', title='', subtitle='', description='')
    title = i.title.strip()
    subtitle = i.subtitle.strip()
    description = i.description.strip()
    if not title:
        raise APIError('value', 'title', 'Title is empty')
    cv = get_default_cv(ctx.user.id)
    for s in cv.sections:
        if s.id==i.id:
            next_id = db.next_str()
            logging.info('NEXT-ID: ' + next_id)
            db.insert('entries', id=next_id, user_id=ctx.user.id, resume_id=cv.id, section_id=s.id, display_order=len(s.entries), title=title, subtitle=subtitle, description=description, picture='', version=0)
            return dict(id=next_id, title=title, subtitle=subtitle, description=description)
    raise APIError('value', 'id', 'Invalid section id.')

@jsonresult
@post('/entries/update')
def update_entry():
    _check_user()
    i = ctx.request.input(id='', title='', subtitle='', description='')
    if not i.id:
        raise APIError('value', 'id', 'id is empty.')
    title = i.title.strip()
    subtitle = i.subtitle.strip()
    description = i.description.strip()
    if not title:
        raise APIError('value', 'title', 'title is empty')
    entry = db.select_one('select * from entries where id=?', i.id)
    _check_user_id(entry.user_id)
    db.update('update entries set title=?, subtitle=?, description=?, version=version+1 where id=?', title, subtitle, description, entry.id)
    db.update('update sections set version=version+1 where id=?', entry.section_id)
    db.update('update resumes set version=version+1 where id=?', entry.resume_id)
    return dict(result=True)

@jsonresult
@post('/entries/delete')
def delete_entry():
    _check_user()
    i = ctx.request.input(id='')
    if not i.id:
        raise APIError('value', 'id', 'id is empty.')
    entry = db.select_one('select * from entries where id=?', i.id)
    _check_user_id(entry.user_id)
    entries = db.select('select * from entries where section_id=? order by display_order', entry.section_id)
    display_ids = [en.id for en in entries if en.id != i.id]
    db.update('delete from entries where id=?', i.id)
    n = 0
    for i in display_ids:
        db.update('update entries set display_order=? where id=?', n, i)
    db.update('update sections set version=version+1 where id=?', entry.section_id)
    return dict(result=True)

def _check_user():
    if ctx.user is None:
        raise APIError('permission', '', 'Please sign in first.')

def _check_user_id(uid):
    if ctx.user.id != uid:
        raise APIError('permission', '', 'No permission.')
