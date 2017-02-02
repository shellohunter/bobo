#!/usr/bin/python
# -*- coding: utf-8 -*-

import hashlib
import time
import os
import sys
import re
if sys.platform == "linux":
    import daemon
import tornado.web
import tornado.httpserver
import tornado.options
import tornado.ioloop
import sqlite3



class WifiDB():
    def __init__(self, path=None):
        if path != None:
            self.dbconn = sqlite3.connect(path)
        else:
            self.dbconn = sqlite3.connect("wifigod.sqlite3")

        self.dbcusor = self.dbconn.cursor()
        self.dbcusor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = self.dbcusor.fetchall()
        for each in tables:
            if "auth" == each[0]:
                return
        tmp = """
            create table auth (
                openid text,
                fans text,
                token text,
                maclist text,
                subscribe text,
                unsubscribe text,
                lastactive text,
                lastauth text,
                comment text
                )
        """
        self.dbcusor.execute(tmp)
        tmp = """
            create table log (
                time text,
                who text,
                type text,
                event text
                )
        """
        self.dbcusor.execute(tmp)
        self.dbconn.commit()

    def __del__(self):
        self.dbconn.commit()
        self.dbconn.close()

    def isfan(self, openid):
        self.dbcusor.execute("select fans from auth where openid='"+openid+"'")
        fan = self.dbcusor.fetchone()
        if fan == None or fan[0] == 0:
            return False
        else:
            return True


    def addauth(self, openid, fans=None, token=None, maclist=None, subscribe=None,
                unsubscribe=None, lastactive=None, lastauth=None, comment = None):
        data=[]
        if openid == None:
            return False

        # order matters!

        data.append(("openid", openid))
        data.append(("token", token))
        data.append(("fans", fans))
        data.append(("maclist", maclist))
        data.append(("subscribe", subscribe))
        data.append(("unsubscribe", unsubscribe))
        data.append(("lastactive", lastactive))
        data.append(("lastauth", lastauth))
        data.append(("comment", comment))

        self.dbcusor.execute("select count(*) from auth where openid='"+openid+"'")
        if self.dbcusor.fetchone()[0] == 0:
            tmp = "insert into auth values("
            for k,v in data:
                if v == None:
                    tmp = tmp + "\"\","
                else:
                    tmp = tmp + "\"" + v + "\","
            tmp = tmp[:-1] + ")"
            print(tmp)
            self.dbcusor.execute(tmp)
        else:
            tmp = "update auth set "
            for k,v in data:
                if v != None:
                    tmp = tmp + k + "=\"" + v + "\","
            tmp = tmp[:-1] + "where openid=\""+openid+"\""
            print(tmp)
            self.dbcusor.execute(tmp)

    def getauth(self):
        self.dbcusor.execute("select * from auth")
        auth = self.dbcusor.fetchall()
        return auth

    def addlog(self, who, etype, event):
        timestamp = str(int(time.time()))
        self.dbcusor.execute("insert into log values(\""+timestamp+"\",\""+who+"\",\""+etype+"\",\""+event+"\")")

    def getlog(self):
        self.dbcusor.execute("select time, who, type, event from log")
        log = self.dbcusor.fetchall()
        return log

    def testdata(self):
        self.dbcusor.execute("insert into auth values(\"aaaa\", \"aaaa\", \"aaaa\", \"aaaa\", \"aaaa\", \"aaaa\", \"aaaa\", \"aaaa\")")

    def dumplog(self):
        ret = self.dbcusor.execute("select * from log")
        for each in ret:
            print(each)
        ret = self.dbcusor.execute("select count(*) from log")
        print(ret.fetchone())

    def dumpauth(self):
        ret = self.dbcusor.execute("select * from auth")
        for each in ret:
            print(each)
        ret = self.dbcusor.execute("select count(*) from auth")
        print(ret.fetchone())


class HandleUnknown(tornado.web.RequestHandler):
    def get(self):
        self.write("Hello World!")

class HandlePing(tornado.web.RequestHandler):
    def get(self):
        gw_id = self.get_argument("gw_id", "<unknown>")
        sys_uptime = self.get_argument("sys_uptime", "<unknown>")
        print(gw_id)
        print(sys_uptime)
        self.write("Pong")

class HandleLogin(tornado.web.RequestHandler):
    def get(self):
        print(self.request.arguments)
        args={}
        args["gw_address"] = self.get_argument("gw_address", "<unknown>")
        args["gw_port"] = self.get_argument("gw_port", "2060")
        args["gw_id"] = self.get_argument("gw_id", "<unknown>")
        args["mac"] = self.get_argument("mac", "<unknown>")
        args["url"] = self.get_argument("url", "#")
        print(args)

        # check if url is wx auth.
        m = re.search(r"wx(.+)wx", args["url"])
        if m != None:
            # for wx fans
            wxuser = m.group(1)
            print("detect a wx auth pair! openid=<%s>, mac=<%s>"%(wxuser, args["mac"]))
            db.addauth(openid=wxuser, maclist=args["mac"])
            self.redirect("http://%s:%s/wifidog/auth?token=%s"%(gw_address, gw_port, token))
        else:
            # normal authentication
            self.render("wifigod/login.htm", args=args)

class HandleAuth(tornado.web.RequestHandler):
    def post(self):
        username = self.get_argument("username","<unknown>")
        password = self.get_argument("password","<unknown>")
        gw_address = tornado.escape.url_unescape(self.get_argument("gw_address","<unknown>"))
        gw_port = tornado.escape.url_unescape(self.get_argument("gw_port","<unknown>"))
        print(username)
        print(password)
        m = hashlib.md5()
        m.update(username.encode("utf8"))
        m.update(password.encode("utf8"))
        token = base64.b64encode(m.digest())
        print(token)

        self.redirect("http://%s:%s/wifidog/auth?token=%s"%(gw_address, gw_port, token))

    def get(self):
        arguments = self.request.arguments
        print(arguments)
        self.set_header("Auth","1")

class HandlePortal(tornado.web.RequestHandler):
    def get(self):
        print(self.request.arguments)
        self.render("wifigod/success.htm", url=None)

class WifiDump(tornado.web.RequestHandler):
    def get(self):
        self.write("WXDump!")
        log = db.getlog()
        auth = db.getauth()
        self.render("wx/dump.htm", log=log, auth=auth)


class WifiGod(object):
    """docstring for WifiGod"""
    def __init__(self):
        super(WifiGod, self).__init__()
        global db
        db = WifiDB()


    def handlers(self):
        return [
            (r'/wifi/dump', WifiDump),
            (r"/wifi/ping/?", HandlePing),
            (r"/wifi/login/?", HandleLogin),
            (r"/wifi/auth/?", HandleAuth),
            (r"/wifi/portal/?", HandlePortal)
        ]



if __name__ == "__main__":
    from tornado.options import define, options
    define("port", default=80, help="run on the given port", type=int)
    global db

    tornado.options.parse_command_line()
    log = open('tornado.' + str(options.port) + '.log', 'a+')

    if options.daemon != 0 and sys.platform == "linux":
        ctx = daemon.DaemonContext(stdout=log, stderr=log,  working_directory='.')
        ctx.open()

    db = WifiDB()
    app = tornado.web.Application(
        handlers = [
            (r'/wifi/dump', HandleDump),
            (r"/wifi/ping/?", HandlePing),
            (r"/wifi/login/?", HandleLogin),
            (r"/wifi/auth/?", HandleAuth),
            (r"/wifi/portal/?", HandlePortal)
        ],
        Debug=True,
        static_path =os.path.join(os.path.dirname(__file__), "static"),
        template_path=os.path.join(os.path.dirname(__file__), "templates")
    )
    server = tornado.httpserver.HTTPServer(app)
    server.listen(options.port)
    try:
        tornado.ioloop.IOLoop.instance().start()
    except KeyboardInterrupt:
        tornado.ioloop.IOLoop.instance().stop()
