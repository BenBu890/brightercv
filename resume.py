#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'Michael Liao'

' Resume module '

import os, re, json, time, base64, hashlib, logging, functools

from transwarp.web import ctx, view, get, post, route, Dict, Template, seeother, notfound, badrequest
from transwarp import db

from api import APIError, jsonresult, check_email, check_md5_passwd

def get_default_cv(uid):
    cvs = None
    while not cvs:
        cvs = db.select('select * from resumes where user_id=?', uid)
        if not cvs:
            db.insert('resumes', id=db.next_str(), user_id=uid, title='My Resume', version=0)

    cv = cvs[0]
    cv.sections = db.select('select * from sections where resume_id=? order by display_order', cv.id)
    for section in cv.sections:
        section.items = db.select('select * from items where section_id=? order by display_order', section.id)
    return cv

@get('/cv/<uid>')
@view('templates/resume.html')
def cv(uid):
    target_user = db.select_one('select * from users where id=?', uid)
    cv = get_default_cv(uid)
    return dict(cv=cv, user=ctx.user, target=target_user, editable=ctx.user and ctx.user.id==uid)

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

_SECTIONS = (
    (u'about', u'About', ),
    (u'summary', u'Summary', ),
    (u'experience', u'Experience', ),
    (u'skills', u'Skills', ),
    (u'languages', u'Languages', ),
    (u'education', u'Education', ),
    (u'publications', u'Publications', ),
    (u'certifications', u'Certifications', ),
    (u'patents', u'Patents', ),
)

_SECTIONS_DICT = dict(_SECTIONS)
_SECTIONS_TUPLE = tuple([s[0] for s in _SECTIONS])
_SECTIONS_SET = frozenset(_SECTIONS_TUPLE)

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

    cv = get_default_cv(ctx.user.id)
    for s in cv.sections:
        if s.kind==kind:
            raise APIError('value', '', 'Section exist.')
    db.insert('sections', id=db.next_str(), user_id=ctx.user.id, resume_id=cv.id, display_order=len(cv.sections), kind=kind, title=title, description=i.description.strip(), version=0)
    return dict(result=True)

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
@post('/items/add')
def add_item():
    _check_user()
    i = ctx.request.input(section_id='', title='', subtitle='', description='')
    title = i.title.strip()
    subtitle = i.subtitle.strip()
    description = i.description.strip()
    if not title:
        raise APIError('value', 'title', 'Title is empty')
    cv = get_default_cv(ctx.user.id)
    for s in cv.sections:
        if s.id==i.section_id:
            db.insert('items', id=db.next_str(), user_id=ctx.user.id, resume_id=cv.id, section_id=s.id, display_order=len(s.items), title=title, subtitle=subtitle, description=description, picture='', version=0)
            return dict(result=True)
    raise APIError('value', 'section_id', 'Invalid section id.')

@jsonresult
@post('/items/update')
def update_item():
    _check_user()
    i = ctx.request.input(id='', title='', subtitle='', description='')
    if not i.id:
        raise APIError('value', 'id', 'id is empty.')
    title = i.title.strip()
    subtitle = i.subtitle.strip()
    description = i.description.strip()
    if not title:
        raise APIError('value', 'title', 'title is empty')
    item = db.select_one('select * from items where id=?', i.id)
    _check_user_id(item.user_id)
    db.update('update items set title=?, subtitle=?, description=?, version=version+1 where id=?', title, subtitle, description, item.id)
    db.update('update sections set version=version+1 where id=?', itme.section_id)
    db.update('update resumes set version=version+1 where id=?', itme.resume_id)
    return dict(result=True)

def _check_user():
    if ctx.user is None:
        raise APIError('permission', '', 'Please sign in first.')

def _check_user_id(uid):
    if ctx.user.id != uid:
        raise APIError('permission', '', 'No permission.')
