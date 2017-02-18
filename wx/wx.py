#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
import hashlib
import time
import os
import re
if sys.platform == "linux":
    import daemon
import tornado.web
import tornado.httpserver
import tornado.options
import tornado.ioloop
import xml.etree.ElementTree as et
import time



from wx.wxbase import WXBase
from wx.enclub.enclub import EnClub

class WXBaseHandler(WXBase):
    """handle wechat message from server."""
    def __init__(self):
        self.codes = enclub.EnClub().codes()

    def get(self):
        if self.verify():
            return self.write("you peeper!")
        msg = self.parseMsg(self)
        self.dumpMsg(msg)

        openid = msg["FromUserName"]
        print(openid)

        if msg["MsgType"] == "text":
            msgtext = msg["Content"]
            for hdl in self.codes:
                if string.trim(msgtext) == hdl[0]:
                    hdl[1](msgtext, msg)
            else:
                self.sendText("自动回复："+msgtext, msg)


    def post(self):
        if self.verify():
            return self.write("you peeper!")
        msg = self.parseMsg(self)
        self.dumpMsg(msg)






class WX(object):
    def handlers(self):
        print("wx.WX.handlers()")
        x = [
            #(r'/wx/dump', WXDump),
            (r'/wx', WXBaseHandler),
        ]
        x.extend(EnClub().handlers())
        return x

if __name__ == "__main__":
    global db
    from tornado.options import define, options
    define("port", default=80, help="run on the given port", type=int)
    define("daemon", default=0, help="run as a daemon", type=int)
    tornado.options.parse_command_line()
    if options.daemon != 0 and sys.platform == "linux":
        log = open('tornado.' + str(options.port) + '.log', 'a+')
        ctx = daemon.DaemonContext(stdout=log, stderr=log,  working_directory='.')
        ctx.open()
    db = WXDB()
    app = tornado.web.Application(
        handlers = [
            (r"/wx/dump", WXDump),
            (r'/wx', WXHandler),
        ],
        Debug=True,
        static_path =os.path.join(os.path.dirname(__file__), "../static"),
        template_path=os.path.join(os.path.dirname(__file__), "../templates")
    )
    server = tornado.httpserver.HTTPServer(app)
    server.listen(options.port)
    try:
        tornado.ioloop.IOLoop.instance().start()
    except KeyboardInterrupt:
        tornado.ioloop.IOLoop.instance().stop()
