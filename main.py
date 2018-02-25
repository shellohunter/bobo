#!/usr/local/bin/python3
# -*- coding: utf-8 -*-

import os.path
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import sys
if sys.platform == "linux":
    import daemon
import hashlib
import requests

from qiniu import Auth
from qiniu import BucketManager

from tornado.options import define, options
define("port", default=8080, help="run on the given port", type=int)
define("daemon", default=0, help="run as a daemon", type=int)


class BaseHandler(tornado.web.RequestHandler):
    def prepare(self):
        host = self.request.headers.get("Host", "none")
        print(host)
        if host.find("nossiac.com") < 0 \
        and host.find("127.0.0") < 0 \
        and host.find("172.26") < 0 \
        and host.find("192.168.") < 0:
            print("an unexpected host "+host)
            return self.redirect("http://nossiac.com", permanent=True)
        super().prepare()

class Home(BaseHandler):
    def get(self):
        self.render('home.html')

class Music(BaseHandler):
    def get(self):
        self.render("music.html")

class Message(BaseHandler):
    def get(self):
        self.render("blog/message.html")

    def post(self):
        self.render("500.html")

class Login(BaseHandler):
    def get(self):
        retry = self.get_argument("retry", 0)
        next = self.get_argument("next", "/")
        self.render('login.html', retry=retry, next=next)

    def post(self):
        pwd = self.get_argument("password", None)
        if not pwd:
            return self.redirect("login?retry=1&next="+self.get_argument("next", "/"))
        m = hashlib.sha1()
        m.update(pwd.encode("utf-8"))
        if m.digest() == b".<\x0f\xee\xab\xae\xb5\x95\xf9\x1fm\xcc\x169\x93\x9e\xa0\x12\xc4\x90":
            print("login success!")
            print(self.get_argument("next", "/"))
            next = self.get_argument("next")
            next = next or "/"
            print(next)
            self.set_secure_cookie("1tdhblkfcdhx2a", "str(author_id)")
            self.redirect(next)
        else:
            self.redirect("login?retry=1&next="+self.get_argument("next", "/"))

class Logout(BaseHandler):
    def get(self):
        self.clear_cookie("1tdhblkfcdhx2a")
        self.redirect(self.get_argument("next", "/"))


class Plan(BaseHandler):
    def get(self):
        self.render("plan.html")


class Error(BaseHandler):
    def get(self):
        self.write_error(404)

    def write_error(self, status_code, **kwargs):
        if status_code == 404:
            self.render('404.html')
        else:
            self.render('500.html')


class Qiniu(BaseHandler):
    """
    sync all images to qiniu.
    """

    def get(self):
        # list all resourses
        # bucket=<UrlEncodedBucket>&marker=<Marker>&limit=<Limit>&prefix=<UrlEncodedPrefix>&delimiter=<UrlEncodedDelimiter>
        self.access_key = '6LG96YZtw8bacYtviITUQIFqdK67qZ3SqXE8Lhaw'
        self.secret_key = 'Kc1aI18VwuDyVNdid8UfdPrAPiWXOb09UxmlFfQd'
        self.bucket_name ='nossiac'

        q = Auth(self.access_key, self.secret_key)
        bucket = BucketManager(q)
        prefix = None
        limit = 10
        delimiter = None
        marker = None # offset

        ret, eof, info = bucket.list(self.bucket_name, prefix, marker, limit, delimiter)
        self.write(str(ret))

        self.write("<hr>")
        #import json
        #json_ret = json.loads(ret)
        items = ret["items"]
        for item in items:
            self.write('<img style=\"margin=10px; max-width:100px; max-height: 100px;\" src=\"http://7xthf5.com1.z0.glb.clouddn.com/'+item["key"]+'\"><br>')

        self.write("<hr>")
        self.write(str(eof))
        self.write("<hr>")
        self.write(str(info))



if __name__ == "__main__":

    tornado.options.parse_command_line()

    if options.daemon != 0 and sys.platform == "linux":
        log = open('tornado.' + str(options.port) + '.log', 'a+')
        ctx = daemon.DaemonContext(stdout=log, stderr=log,  working_directory='.')
        ctx.open()


    webhandlers = [
            (r"/", Home),
            (r"/login", Login),
            (r"/logout", Logout),
            (r"/7", Qiniu),
            (r"/(baidu_verify_.*)",tornado.web.StaticFileHandler,{"path":os.path.join(os.path.dirname(__file__), "static")}),
            (r"/(MP_verify_.*)",tornado.web.StaticFileHandler,{"path":os.path.join(os.path.dirname(__file__), "static")}),
        ]

    from blog import blog
    # from geek import geek
    from t9x import t9x
    from wx.wx import WX
    #from wifigod import wifigod
    #from movies import movies
    #from club import club
    #from blog import blog
    #from mysky import mysky
    webhandlers.extend(blog.Blog().handlers())
    webhandlers.extend(t9x.T9x().handlers())
    #webhandlers.extend(club.Club().handlers())
    #webhandlers.extend(wifigod.WifiGod().handlers())
    #webhandlers.extend(movies.Movies().handlers())
    # webhandlers.extend(geek.Geek().handlers())
    #webhandlers.extend(mysky.MySky().handlers())
    webhandlers.extend(WX().handlers())
    webhandlers.append((r"/.*", Error)) # always the last!

    ui_modules = []
    ui_modules.extend(WX().uimodules())
    ui_modules.extend(blog.Blog.uimodules())

    for handler in webhandlers:
        print(handler[0], handler[1])

    app = tornado.web.Application(
        handlers = webhandlers,
        ui_modules = ui_modules, 
        template_path = os.path.join(os.path.dirname(__file__),"templates"),
        static_path =os.path.join(os.path.dirname(__file__), "static"),
        debug = True,
        login_url = "/login",
        cookie_secret = "61oETzKXQAGaYdkL5gEmGeJJFuYh7EQnp2XdTP1o/Vo=",
    )
    http_server = tornado.httpserver.HTTPServer(app)
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()
