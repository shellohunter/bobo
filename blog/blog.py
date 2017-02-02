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
#import daemon
import sqlite3
import random
import requests
from qiniu import Auth, put_file, etag, BucketManager
import qiniu.config

blog=None
root=".."

class BaseHandler(tornado.web.RequestHandler):
    def prepare(self):
        host = self.request.headers.get("Host", "none")
        if host.find("nossiac.com") < 0 \
        and host.find("127.0.0") < 0 \
        and host.find("172.26") < 0 \
        and host.find("192.168.") < 0:
            print("an unexpected host "+host)
            return self.redirect("http://nossiac.com", permanent=True)
        super().prepare()

    def get_current_user(self):
        return self.get_secure_cookie("1tdhblkfcdhx2a")

    def ismobile(self):
        #print(self.request.headers)
        ua = self.request.headers.get("User-Agent", None)
        if not ua:
            return False
        key1 = ["iPad","Windows","x86","X11","MAC","Vista","MSIE","Firefox"]
        key2 = ["Android","iPod", "iPhone"]
        for k in key1:
            if ua.find(k) >= 0:
                return False 
        for k in key2:
            if ua.find(k) >= 0:
                return True
        return False

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
            print("visitor!")
            auth = False
            cmd1 = """SELECT COUNT(*) FROM articles WHERE hide <> 1"""
            cmd2 = """SELECT title,link,hide,view
                      FROM articles
                      WHERE hide <> 1
                      ORDER BY rowid DESC
                      LIMIT 20 OFFSET ?"""

        c = blog.conn.cursor()
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
        if self.ismobile():
            self.render("blog/m-blog.html", aa=articles, pages=pages, auth = auth)
        else:
            self.render("blog/blog.html", aa=articles, pages=pages, auth = auth)

class Tags(BaseHandler):
    """docstring for Tags"""
    def get(self, tags):
        if self.get_current_user() != None:
            print("authenticated user!")
            auth = True
        else:
            print("visitor!")
            auth = False

        taglist = tags.split('-')

        c = blog.conn.cursor()
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
        if self.ismobile():
            self.render("blog/m-blog.html", aa=articles, pages=pages, auth = auth)
        else:
            self.render("blog/blog.html", aa=articles, pages=pages, auth = auth)

class Read(BaseHandler):
    def get(self, link = None):
        if self.get_current_user() != None:
            print("authenticated user!")
            auth = True
        else:
            print("visitor!")
            auth = False
        try:
            if link != None:
                link = "".join(link.rsplit(".html", 1)) # nice trick for rreplace!
                c = blog.conn.cursor()
                a = c.execute("SELECT * FROM articles WHERE link == ?",(link,)).fetchone()
        except tornado.web.MissingArgumentError:
            self.redirect("/page-not-exist")
        if a == None:
            self.redirect("/page-not-exist")

        c.execute("UPDATE articles SET view=view+1 WHERE link == ?",(link,))
        blog.conn.commit()
        if self.ismobile():
            self.render("blog/m-read.html", a=a, auth=auth)
        else:
            self.render("blog/read.html", a=a, auth=auth)

class Write(BaseHandler):
    def get(self, link = None):
        if link == None:
            return self.render("blog/write.html", a=None)
        link = link.replace(".html","")
        action = self.get_argument("a", None)
        c = blog.conn.cursor()
        a = c.execute("SELECT * FROM articles WHERE link == ?",(link,)).fetchone()
        if not a:
            return self.redirect("/page-not-exist")
        if action == "d":
            # delete
            c.execute("DELETE FROM articles WHERE link == ?",(link,))
        elif action == "h":
            # hide
            c.execute("UPDATE articles SET hide=? WHERE link == ?",(1,link))
        elif action == "s":
            # show
            c.execute("UPDATE articles SET hide=? WHERE link == ?",(0,link))
        else:
            return self.render("blog/write.html", a=a)
        blog.conn.commit()
        return self.redirect("/blog")

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
            #raise tornado.web.HTTPError(400, "ad")
            self.clear()
            self.set_status(400)
            self.finish("bad request")
            return
        if len(posttime.strip()) == 0:
            posttime= str(datetime.datetime.utcnow()).split(".")[0]

        a = ()
        c = blog.conn.cursor()
        if origin_link != None:
            origin_link = origin_link.replace(".html","")
            a = c.execute("SELECT * FROM articles WHERE link == ?",(origin_link,)).fetchone()
            if not a:
                return self.redirect("/page-not-exist")
            cmd = "UPDATE articles SET title=?, content=?, \
                link=?, date=?, tags=?, hide=? where link = ?"
            c.execute(cmd, (title, content, link, posttime, tags, hide, origin_link))
            blog.conn.commit()
        else:
            cmd = """INSERT INTO articles(title, content, link, date, view, tags, hide)
                     VALUES(?,?,?,?,?,?,?)"""
            c.execute(cmd, (title, content, link, posttime, 0, tags, hide))
            blog.conn.commit()

        self.redirect("/blog/"+link+".html")


class Baidu_Post(tornado.web.RequestHandler):
    def get_all_urls(self):
        cmd = """SELECT link
                 FROM articles
                 WHERE hide <> 1
                 ORDER BY rowid DESC"""
        c = blog.conn.cursor()
        articles = c.execute(cmd).fetchall()
        urllist = []
        for article in articles:
            urllist.append("http://nossiac.com/blog/"+article[0]+".html")
        return urllist

    def get(self):
        urllist = self.get_all_urls()
        s = requests.Session()
        rsp = s.post("http://data.zz.baidu.com/urls?site=nossiac.com&token=pNFdxNnPHI3NGGeo&type=orignal", data="\r\n".join(urllist))
        self.write(rsp.content.decode("ascii"))
        self.write("<br>"+"<br>".join(urllist)+"<br>")
        pass


def upload_to_qiniu(filepath, key=None):
    # -*- coding: utf-8 -*-
    # flake8: noqa
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

        self.render("blog/upload.html", files=files)

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
        self.redirect("/blog/upload")

class Blog(object):
    def __init__(self):
        global blog
        self.tryinitdb()
        try:
            self.conn = sqlite3.connect(os.path.join(os.path.dirname(__file__), root,".db.py"))
        except:
            print("unable to connect to sqlite3!")
            return
        blog = self

    def tryinitdb(self):
        if os.path.exists(os.path.join(os.path.dirname(__file__), root,".db.py")):
            self.conn = sqlite3.connect(os.path.join(os.path.dirname(__file__), root,".db.py"))
            c = self.conn.cursor()
            ret = c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='articles';")
            if ret != None:
                return
        # else we create a new db
        self.conn = sqlite3.connect(os.path.join(os.path.dirname(__file__), root,".db.py"))
        c = self.conn.cursor()
        cmd = """CREATE TABLE articles
                 (title text, content text, link text, date text,
                 view integer, tags text, hide boolean)"""
        print(cmd)
        c.execute(cmd)
        self.conn.commit()
        for i in range(0):
            title = "测试文章"+str(i+1)
            content = ("这是测试的文章，没有任何意义."+str(i+1))*100
            link = "test-article-"+str(i+1)
            date = "2016-4-"+str(i+1)
            view = str(random.randint(1,1000))
            tags = "(测试)"
            hide = 0
            cmd = """INSERT INTO articles (title,content,link,date,view,tags,hide)
                     VALUES(?,?,?,?,?,?,?)"""
            c.execute(cmd, (title, content, link, date, view, tags, hide))
            self.conn.commit()
        self.conn.close()

    def __del__(self):
        if self.conn != None:
            self.conn.close()

    def handlers(self):
        return [
            (r"/blog/baidu_post", Baidu_Post),
            (r"/blog/upload", Upload),
            (r"/blog/*", Index),
            (r"/blog/w/*", Write),
            (r"/blog/w/(.*)", Write),
            (r"/blog/tags/(.*)", Tags),
            (r"/blog/(.*)", Read),
        ]



if __name__ == "__main__":
    from tornado.options import define, options
    define("port", default=8081, help="run on the given port", type=int)
    #define("daemon", default=0, help="run as a daemon", type=int)
    define("db", default=0, help="can be \"mongodb\" or \"sqlite\"", type=str)
    tornado.options.parse_command_line()
    #if options.daemon != 0:
    #    log = open('tornado.' + str(options.port) + '.log', 'a+')
    #    ctx = daemon.DaemonContext(stdout=log, stderr=log,  working_directory='.')
    #    ctx.open()

    root = ".."
    blog = Blog()

    app = tornado.web.Application(
        handlers = blog.handlers(),
        template_path = os.path.join(os.path.dirname(__file__), root,"templates"),
        static_path =os.path.join(os.path.dirname(__file__), root, "static"),
        debug = True,
        login_url = "/login",
        cookie_secret = "61oETzKXQAGaYdkL5gEmGeJJFuYh7EQnp2XdTP1o/Vo=",
    )
    http_server = tornado.httpserver.HTTPServer(app)
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()
