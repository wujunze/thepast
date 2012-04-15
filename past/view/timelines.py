#-*- coding:utf-8 -*-
import os
from datetime import datetime

from flask import g, request, redirect, url_for, abort, render_template,\
        make_response

from past import app
from past import config
from past.model.user import User
from past.model.status import Status

from past.utils.pdf import is_pdf_file_exists, get_pdf_filename
from past.utils.escape import json_encode
from past.cws.cut import get_keywords
from .utils import require_login

@app.route("/visual")
@require_login()
def myvisual():
    return redirect("/user/%s/visual" % g.user.id)

@app.route("/user/<uid>/visual")
@require_login()
def visual(uid):
    u = User.get(uid)
    if not u:
        abort(404, "no such user")

    return render_template("visual_timeline.html", user=u, unbinded=[], 
            config=config)

@app.route("/user/<uid>/timeline_json")
@require_login()
def timeline_json(uid):
    limit = 100
    u = User.get(uid)
    if not u:
        abort(404, "no such user")

    cate = request.args.get("cate", None)
    ids = Status.get_ids(user_id=u.id,
            start=g.start, limit=limit, cate=g.cate)
    ids = ids[::-1]

    status_list = Status.gets(ids)
    if not status_list:
        return json_encode({})

    date = []
    for s in status_list:
        headline = s.summary or ''
        text = ''
        images = s.get_data().get_images() or []
        
        if not (headline or text):
            continue

        t = s.create_time

        if s.category in [config.CATE_DOUBAN_STATUS, config.CATE_SINA_STATUS]:
            re_tweet = s.get_retweeted_data()
            re_images = re_tweet and re_tweet.get_images() or []
            images.extend(re_images)
            text = re_tweet and re_tweet.get_content() or ''

        if s.category in [config.CATE_QQWEIBO_STATUS]:
            text = s.get_retweeted_data() or ''
        
        if s.category in [config.CATE_WORDPRESS_POST]:
            uri = s.get_origin_uri()
            headline = '<a href="%s" target="_blank">%s</a>' % (uri and uri[1], s.title)
            text = s.text or ''
        
        tmp = {
            'startDate': t.strftime("%Y,%m,%d,%H,%M,%S"),
            'headline': headline,
            'text': text,
            'asset': {
                'media': images and images[0],
                'credit': '',
                'caption': ''
            },
        }
        date.append(tmp)

    if date:
        tmp = {
            'startDate': datetime.now().strftime("%Y,%m,%d,%H,%M,%S"),
            'headline': '<a href="/user/%s/visual?start=%s">查看更早的内容...</a>' % (u.id, g.start+limit),
            'text': '',
            'asset': {
                'media': '', 'credit': '', 'caption': ''
            },
        }
        date.insert(0, tmp)

    json_data = {
        'timeline':
        {
            'headline': 'The past of you',
            'type': 'default',
            'startDate': date[1]['startDate'],
            'text': 'Storytelling about yourself...',
            'asset':{
                'media': '',
                'credit': '',
                'caption': ''
            },
            'date':date
        }
    }
    return json_encode(json_data)

@app.route("/i")
@require_login()
def timeline():
    ids = Status.get_ids(user_id=g.user.id, start=g.start, limit=g.count, cate=g.cate)
    status_list = Status.gets(ids)
    status_list  = statuses_timelize(status_list)
    if status_list:
        tags_list = [x[0] for x in get_keywords(g.user.id, 30)]
    else:
        tags_list = []
    intros = [g.user.get_thirdparty_profile(x).get("intro") for x in config.OPENID_TYPE_DICT.values()]
    intros = filter(None, intros)
    return render_template("timeline.html", user=g.user, tags_list=tags_list,
            intros=intros, status_list=status_list, config=config)


@app.route("/user/<uid>")
@require_login()
def user(uid):
    u = User.get(uid)
    if not u:
        abort(404, "no such user")

    if g.user and g.user.id == u.id:
        return redirect(url_for("timeline"))
    
    #TODO:增加可否查看其他用户的权限检查
    cate = request.args.get("cate", None)
    ids = Status.get_ids(user_id=u.id, start=g.start, limit=g.count, cate=g.cate)
    status_list = Status.gets(ids)
    status_list  = statuses_timelize(status_list)
    if status_list:
        tags_list = [x[0] for x in get_keywords(u.id, 30)]
    else:
        tags_list = []
    intros = [u.get_thirdparty_profile(x).get("intro") for x in config.OPENID_TYPE_DICT.values()]
    intros = filter(None, intros)
    return render_template("timeline.html", user=u, unbinded=[], 
            tags_list=tags_list, intros=intros, status_list=status_list, config=config)

@app.route("/pdf")
@require_login()
def mypdf():
    if not g.user:
        return redirect(url_for("pdf", uid=config.MY_USER_ID))
    else:
        return redirect(url_for("pdf", uid=g.user.id))

@app.route("/demo-pdf")
def demo_pdf():
    pdf_filename = "demo.pdf"
    full_file_name = os.path.join(config.PDF_FILE_DOWNLOAD_DIR, pdf_filename)
    resp = make_response()
    resp.headers['Cache-Control'] = 'no-cache'
    resp.headers['Content-Type'] = 'application/pdf'
    resp.headers['Content-Disposition'] = 'attachment; filename=%s' % pdf_filename
    resp.headers['Content-Length'] = os.path.getsize(full_file_name)
    redir = '/down/pdf/' + pdf_filename
    resp.headers['X-Accel-Redirect'] = redir
    return resp
    
@app.route("/<uid>/pdf")
@require_login()
def pdf(uid):
    user = User.get(uid)
    if not user:
        abort(404, "No such user")
    
    pdf_filename = get_pdf_filename(user.id)
    if not is_pdf_file_exists(pdf_filename):
        abort(404, "Please wait one day to  download the PDF version, because the vps memory is limited")

    full_file_name = os.path.join(config.PDF_FILE_DOWNLOAD_DIR, pdf_filename)
    resp = make_response()
    resp.headers['Cache-Control'] = 'no-cache'
    resp.headers['Content-Type'] = 'application/pdf'
    resp.headers['Content-Disposition'] = 'attachment; filename=%s' % pdf_filename
    resp.headers['Content-Length'] = os.path.getsize(full_file_name)
    redir = '/down/pdf/' + pdf_filename
    resp.headers['X-Accel-Redirect'] = redir
    return resp



## 把status_list构造为month，day的层级结构
def statuses_timelize(status_list):

    hashed = {}
    for s in status_list:
        hash_s = hash(s)
        if hash_s not in hashed:
            hashed[hash_s] = RepeatedStatus(s)
        else:
            hashed[hash_s].status_list.append(s)

    output = {}
    for hash_s, repeated in hashed.items():
        s = repeated.status_list[0]
        year_month = "%s-%s" % (s.create_time.year, s.create_time.month)
        day = s.create_time.day

        if year_month not in output:
            output[year_month] = {day:[repeated]}
        else:
            if day not in output[year_month]:
                output[year_month][day] = [repeated]
            else:
                output[year_month][day].append(repeated)

    return output

class RepeatedStatus(object):
    def __init__(self, status):
        self.create_time = status.create_time
        self.status_list = [status]
