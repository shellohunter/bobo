# -*- coding: utf-8 -*-
# flake8: noqa
import os.path
import hashlib
import base64
import re
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import time
import datetime
import json
import sqlite3
import random
import requests
import markdown

from qiniu import Auth, put_file, etag, BucketManager
import qiniu.config
from collections import namedtuple

root=".."
Article = namedtuple("Article",
    ["title", "content", "link", "date", "view", "tags", "hide"])


class _SingletonWrapper:
    def __init__(self, cls):
        self.__wrapped__ = cls
        self._instance = None

    def __call__(self, *args, **kwargs):
        if self._instance is None:
            self._instance = self.__wrapped__(*args, **kwargs)
        return self._instance

def singleton(cls):
    return _SingletonWrapper(cls)


class BaseHandler(tornado.web.RequestHandler):
    def initialize(self, db = None, subblog = None):
        self.db = db
        self.subblog = subblog

    def prepare(self):
        host = self.request.headers.get("Host", "none")
        if host.find("nossiac.com") < 0 \
        and host.find("127.0") < 0 \
        and host.find("172.26") < 0 \
        and host.find("192.168.") < 0:
            print("an unexpected host "+host)
            return self.redirect("http://nossiac.com"+self.request.uri, permanent=True)
        super().prepare()

    def get_current_user(self):
        return self.get_secure_cookie("1tdhblkfcdhx2a")

    def render(self, template_name, **kwargs):
        print(self.subblog)
        host = self.request.headers.get("Host", "nossiac.com")
        if host.find(":") > 0:
            host = "nossiac.com"
        param = {
            "url": "http://{0}{1}".format(host, self.request.uri),
            "subblog": self.subblog
        }
        return super().render(template_name, param = param, **kwargs)

    def get_template_path(self):
        return os.path.join(os.path.dirname(__file__), "templates")


class WX_JSAPI_Param(tornado.web.UIModule):
    __appid = "wxa9a9ba240b345647"
    __secret = "54267c90d03d814394688f0c0205195a"
    __wx_token = ""
    __wx_token_expire = 0
    __wx_ticket = ""
    __wx_ticket_expire = 0

    def render(self, url="", title=""):
        wx_nonceStr = str(int(time.time())+random.randint(100,999))
        wx_timestamp = int(time.time())

        tmp = "jsapi_ticket={0}&noncestr={1}&timestamp={2}&url={3}".format(
            self.get_wx_ticket(), wx_nonceStr, wx_timestamp, url)

        wx_signature = hashlib.sha1(tmp.encode("ascii")).hexdigest()

        param = {
            "wx_title": title,
            "wx_link": url,
            "wx_nonceStr": wx_nonceStr,
            "wx_timestamp": wx_timestamp,
            "wx_appId": self.__appid,
            "wx_signature": wx_signature,
        }

        #print("{0}={1}".format("tmp", tmp))
        #print("{0}={1}".format("url", url))
        #print("{0}={1}".format("token", self.get_wx_token()))
        #print("{0}={1}".format("ticket", self.get_wx_ticket()))
        #for k,v in param.items():
        #    print("{0}={1}".format(k,v))

        return self.render_string(
            "blog/modules/wx_param.html", param = param)


    def get_wx_token(self):
        def __get_wx_token():
            url = "https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={0}&secret={1}".format(self.__appid, self.__secret)

            try:
                s = requests.Session()
                rsp = s.post(url)
                #print("wx_token", rsp.content)
            except Exception as e:
                #print("wx_token", e)
                return
            try:
                rspjson = json.loads(rsp.content.decode("ascii"))
                #print(type(rspjson), rspjson)
                WX_JSAPI_Param.__wx_token = rspjson["access_token"]
                WX_JSAPI_Param.__wx_token_expire = int(time.time()) + int(rspjson["expires_in"])
            except Exception as e:
                #print(e)
                return
            return WX_JSAPI_Param.__wx_token

        if int(time.time()) < WX_JSAPI_Param.__wx_token_expire - 10:
            return WX_JSAPI_Param.__wx_token
        else:
            return __get_wx_token()

    def get_wx_ticket(self):
        def __get_wx_ticket():
            url = "https://api.weixin.qq.com/cgi-bin/ticket/getticket?access_token={0}&type=jsapi".format(self.get_wx_token())
            try:
                s = requests.Session()
                rsp = s.post(url)
            except Exception as e:
                return
            try:
                rspjson = json.loads(rsp.content.decode("ascii"))
                WX_JSAPI_Param.__wx_ticket = rspjson["ticket"]
                WX_JSAPI_Param.__wx_ticket_expire = int(time.time()) + int(rspjson["expires_in"])
            except Exception as e:
                return
            return WX_JSAPI_Param.__wx_ticket

        if int(time.time()) < WX_JSAPI_Param.__wx_ticket_expire - 10:
            return WX_JSAPI_Param.__wx_ticket
        else:
            return __get_wx_ticket()


class Index(BaseHandler):
    def get(self):
        if self.get_current_user() != None:
            print("authenticated user!")
            auth = True
            cmd1 = """SELECT COUNT(*) FROM articles"""
            cmd2 = """SELECT title,link,hide,view
                      FROM articles
                      ORDER BY rowid DESC
                      LIMIT 20 OFFSET ?"""
        else:
            auth = False
            cmd1 = """SELECT COUNT(*) FROM articles WHERE hide <> 1"""
            cmd2 = """SELECT title,link,hide,view
                      FROM articles
                      WHERE hide <> 1
                      ORDER BY rowid DESC
                      LIMIT 20 OFFSET ?"""

        c = self.db.cursor()
        page = int(self.get_argument("p", "1"))

        pages = int((c.execute(cmd1).fetchone()[0]-1)/20+1)
        # efficient way of pagination in sqlite3
        # http://stackoverflow.com/questions/14468586/efficient-paging-in-sqlite-with-millions-of-records
        # SELECT *
        # FROM MyTable
        # WHERE SomeColumn > LastValue
        # ORDER BY SomeColumn
        # LIMIT 100
        articles = c.execute(cmd2,((page-1)*20,)).fetchall()
        self.render("index.html", aa=articles, pages=pages,
            auth = auth)

class Tags(BaseHandler):
    def get(self, tags):
        if self.get_current_user() != None:
            print("authenticated user!")
            auth = True
        else:
            print("visitor!")
            auth = False

        taglist = tags.split('-')

        c = self.db.cursor()
        page = int(self.get_argument("p", "1"))

        cmd = "SELECT title,link,hide,view FROM articles WHERE"
        for tag in taglist:
            cmd = cmd + " tags LIKE '%("+tag+")%' AND"
        if cmd.endswith("AND"):
            cmd = cmd[:-3]
        if not auth:
            cmd = cmd + " AND hide <> 1"
        cmd = cmd + " ORDER BY rowid DESC LIMIT 20 OFFSET ?"
        print(cmd)
        articles = c.execute(cmd,((page-1)*20,)).fetchall()

        cmd = "SELECT COUNT(*) FROM articles WHERE"
        for tag in taglist:
            cmd = cmd + " tags LIKE '%("+tag+")%' AND"
        if cmd.endswith("AND"):
            cmd = cmd[:-3]
        if not auth:
            cmd = cmd + " AND hide <> 1"
        #print(cmd)
        pages = int((c.execute(cmd).fetchone()[0]-1)/20+1)
        self.render("index.html", aa=articles, pages=pages, auth = auth)

class Read(BaseHandler):
    def get(self, link):
        if self.get_current_user() != None:
            print("authenticated user!")
            auth = True
        else:
            auth = False
            print("visitor!")

        link = "".join(link.rsplit(".html", 1)) # nice trick for rreplace!
        c = self.db.cursor()
        a = c.execute("SELECT * FROM articles WHERE link == ?",(link,)).fetchone()
        try:
            a = Article(*a)._asdict()
            a["content"] = markdown.markdown(a["content"])
            c.execute("UPDATE articles SET view=view+1 WHERE link == ?",(link,))
            self.db.commit()
            self.render("read.html", a=a, auth=auth)
        except Exception as e:
            print(e)
            return self.redirect("/page-not-exist")

class Write(BaseHandler):
    @tornado.web.authenticated
    def get(self, link = None):
        if link == None:
            return self.render("write.html", a=None)
        link = link.replace(".html","")
        action = self.get_argument("a", None)
        c = self.db.cursor()
        a = c.execute("SELECT * FROM articles WHERE link == ?",(link,)).fetchone()
        if not a:
            return self.redirect("/page-not-exist")
        if action == "d": # delete
            c.execute("DELETE FROM articles WHERE link == ?",(link,))
        elif action == "h": # hide
            c.execute("UPDATE articles SET hide=? WHERE link == ?",(1,link))
        elif action == "s": # show
            c.execute("UPDATE articles SET hide=? WHERE link == ?",(0,link))
        else:
            return self.render("write.html", a=Article(*a))
        self.db.commit()
        return self.redirect("/"+self.subblog)

    @tornado.web.authenticated
    def post(self, origin_link = None):
        title = self.get_argument("title","").strip()
        hide = int(self.get_argument("hide", "0").strip())
        tags = self.get_argument("tags", "").replace(chr(65292), ",")
        tags = ''.join(['('+x.strip()+')' for x in tags.split(',')])
        posttime = self.get_argument("datetime", "").strip()
        content = self.get_argument("content","").strip()
        link = self.get_argument("link", "").strip()
        if link == "" or title == "":
            self.clear()
            self.set_status(400)
            self.finish("bad request")
            return
        if len(posttime.strip()) == 0:
            posttime= str(datetime.datetime.utcnow()).split(".")[0]

        a = ()
        c = self.db.cursor()
        if origin_link != None:
            origin_link = origin_link.replace(".html","")
            a = c.execute("SELECT * FROM articles WHERE link == ?",(origin_link,)).fetchone()
            if not a:
                return self.redirect("/page-not-exist")
            cmd = ("UPDATE articles SET title=?, content=?,"
                "link=?, date=?, tags=?, hide=? where link = ?")
            c.execute(cmd, (title, content, link, posttime, tags, hide, origin_link))
            self.db.commit()
        else:
            cmd = """INSERT INTO articles(title, content, link, date, view, tags, hide)
                     VALUES(?,?,?,?,?,?,?)"""
            c.execute(cmd, (title, content, link, posttime, 0, tags, hide))
            self.db.commit()

        self.redirect("/{0}/{1}.html".format(self.subblog,link))


class Baidu_Post(BaseHandler):
    def get_all_urls(self):
        cmd = """SELECT link
                 FROM articles
                 WHERE hide <> 1
                 ORDER BY rowid DESC"""
        c = self.db.cursor()
        articles = c.execute(cmd).fetchall()
        urllist = []
        for article in articles:
            urllist.append("http://nossiac.com/{0}/{1}.html".format(self.subblog, article[0]))
        return urllist

    def get(self):
        urllist = self.get_all_urls()
        s = requests.Session()
        rsp = s.post("http://data.zz.baidu.com/urls?site=nossiac.com&token=pNFdxNnPHI3NGGeo&type=orignal", data="\r\n".join(urllist))
        self.write(rsp.content.decode("ascii"))
        self.write("<br>"+"<br>".join(urllist)+"<br>")
        pass


def upload_to_qiniu(filepath, key=None):
    access_key = '6LG96YZtw8bacYtviITUQIFqdK67qZ3SqXE8Lhaw'
    secret_key = 'Kc1aI18VwuDyVNdid8UfdPrAPiWXOb09UxmlFfQd'

    q = Auth(access_key, secret_key)

    bucket_name = 'nossiac'

    if key is None:
        key = filepath;

    #policy={
    # 'callbackUrl':'http://your.domain.com/callback.php',
    # 'callbackBody':'filename=$(fname)&filesize=$(fsize)'
    # }
    #token = q.upload_token(bucket_name, key, 3600, policy)
    token = q.upload_token(bucket_name, key, 3600)

    localfile = filepath

    ret, info = put_file(token, key, localfile)
    print(info)
    assert ret['key'] == key
    assert ret['hash'] == etag(localfile)

class Upload(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        #files = os.listdir(os.path.join("static", "upload"))
        #files = [os.path.join("upload", x) for x in files]
        files = []

        # list all resourses
        # bucket=<UrlEncodedBucket>&marker=<Marker>&limit=<Limit>&prefix=<UrlEncodedPrefix>&delimiter=<UrlEncodedDelimiter>
        access_key = '6LG96YZtw8bacYtviITUQIFqdK67qZ3SqXE8Lhaw'
        secret_key = 'Kc1aI18VwuDyVNdid8UfdPrAPiWXOb09UxmlFfQd'
        bucket_name ='nossiac'

        q = Auth(access_key, secret_key)
        bucket = BucketManager(q)
        prefix = None
        limit = 1000
        delimiter = None
        marker = None # offset

        ret, eof, info = bucket.list(bucket_name, prefix, marker, limit, delimiter)

        items = ret["items"]
        for item in items:
            files.append("http://7xthf5.com1.z0.glb.clouddn.com/"+item["key"])

        self.render("upload.html", files=files)

    @tornado.web.authenticated
    def post(self):
        upload_path=os.path.join("static","upload")
        file_metas=self.request.files['file']
        os.makedirs(upload_path, exist_ok=True)
        for meta in file_metas:
            filename=meta['filename']
            filepath=os.path.join(upload_path,filename)
            print(filepath)
            with open(filepath,'wb') as up:
                up.write(meta['body'])
        # post to qiniu
        key = self.get_argument("key", None)
        upload_to_qiniu(filepath, key)
        self.redirect("/{0}/upload".format(self.subblog))


class SubBlog():
    def __init__(self, name):
        if not re.match(r"\w+", name):
            raise Exception("illegal subblog name \"{0}\"".format(name))
        self.name = name
        self.db = self._initdb(".db.{0}.py".format(name))

    def _initdb(self, subblog=".db.py"):
        if os.path.exists(os.path.join(os.path.dirname(__file__), root, subblog)):
            conn = sqlite3.connect(os.path.join(os.path.dirname(__file__), root, subblog))
            c = conn.cursor()
            ret = c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='articles';")
            if ret != None:
                print("db ready "+subblog)
                return conn
            else:
                print("db not really there.")
        # else we create a new db
        print("create new db "+subblog)
        conn = sqlite3.connect(os.path.join(os.path.dirname(__file__), root,subblog))
        c = conn.cursor()
        cmd = """CREATE TABLE articles
                 (title text, content text, link text, date text,
                 view integer, tags text, hide boolean)"""
        c.execute(cmd)
        conn.commit()
        return conn

    def handlers(self):
        param = {
            "db":self.db,
            "subblog":self.name,
        }
        return [
            (r"/"+self.name+"/t/upload", Upload, param),
            (r"/"+self.name+"/t/baidu", Baidu_Post, param),
            (r"/"+self.name+"/*", Index, param),
            (r"/"+self.name+"/w/*", Write, param),
            (r"/"+self.name+"/w/(.*)", Write, param),
            (r"/"+self.name+"/tags/(.*)", Tags, param),
            (r"/"+self.name+"/(.*)", Read, param),
        ]


@singleton
class Blog():
    def __init__(self):
        self.blogs = []
        for entry in os.listdir():
            m = re.match(r".db.(\w+).py", entry)
            if m: self.blogs.append(SubBlog(m.group(1)))

    def handlers(self):
        handlers = [
            (r'/blog/(favicon\.ico)', tornado.web.StaticFileHandler,
                {'path': os.path.join(os.path.dirname(__file__), "static")}),
            (r'/blog/static/(.*)', tornado.web.StaticFileHandler,
                {'path': os.path.join(os.path.dirname(__file__), "static")}),
        ]
        for blog in self.blogs:
            handlers.extend(blog.handlers())
        return handlers

    def uimodules(self):
        return [
            {'WX_JSAPI_Param':WX_JSAPI_Param},
        ]


if __name__ == "__main__":
    from tornado.options import define, options
    define("port", default=8080, help="run on the given port", type=int)
    tornado.options.parse_command_line()

    root = ".."
    blog = Blog()

    app = tornado.web.Application(
        handlers = blog.handlers(),
        ui_modules = blog.uimodules(), 
        #template_path = os.path.join(os.path.dirname(__file__), root,"templates"),
        #static_path =os.path.join(os.path.dirname(__file__), root, "static"),
        debug = True,
        login_url = "/login",
        cookie_secret = hashlib.sha1(str(time.time()).encode("ascii")).hexdigest(),
    )
    http_server = tornado.httpserver.HTTPServer(app)
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()
