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
import time
import sqlite3



"""
item = {}
item["type"] = "choose"
item["id"] = 0
item["text"] = "Many a house ____ been built these years."
item["options"] = [
    ("A", "has"),
    ("A", "have"),
    ("A", "is"),
    ("A", "are"),
]
"""

class WXDB():
    def __init__(self, path=None):
        if path != None:
            self.dbconn = sqlite3.connect(path)
        else:
            self.dbconn = sqlite3.connect(".wx.sqlite3")

        self.dbcusor = self.dbconn.cursor()
        self.dbcusor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = self.dbcusor.fetchall()
        print(tables)
        for each in tables:
            if "log" == each[0]:
                return
        tmp = """
            create table log (
                time text,
                who text,
           1     type text,
                event text
                )
        """
        self.dbcusor.execute(tmp)
        self.dbconn.commit()

    def __del__(self):
        self.dbconn.commit()
        self.dbconn.close()

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
        self.dbcusor.execute("insert into log values(\""
            +timestamp+"\",\""+who+"\",\""+etype+"\",\""+event+"\")")

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


class WXHandler(tornado.web.RequestHandler):
    def verify(self):
        """
        Check if a message is sent from WeChat server.
        """
        token = "mytoken" # set from wx server
        ll = []
        signature = self.get_argument("signature", "<none>")
        ll.append(self.get_argument("timestamp", "<none>"))
        ll.append(self.get_argument("nonce", "<none>"))
        ll.append(token)
        ll.sort()
        m = hashlib.sha1()
        m.update("".join(ll).encode("ascii"))
        digest = m.hexdigest()

        if signature != digest:
            print("signature not match, discard this msg!")
            return False
        else:
            print("signature match, got a wechat msg!")
            return True

    def sendmenu(self, menu, msg):
        """
        a menu entry should be like:
            [(text, detail=None, pic=None, url=None)]
        """
        rspxml = et.Element("xml")
        e = et.SubElement(rspxml, "ToUserName")
        e.text = msg["FromUserName"]
        e = et.SubElement(rspxml, "FromUserName")
        e.text = msg["ToUserName"]
        e = et.SubElement(rspxml, "CreateTime")
        e.text = str(int(time.time()))
        e = et.SubElement(rspxml, "MsgType")
        e.text = "news"
        e = et.SubElement(rspxml, "ArticleCount")
        e.text = str(len(menu))
        articles = et.SubElement(rspxml, "Articles")
        idx = 0
        for entry in menu:
            text, detail, pic, url, cb, auth = entry
            item = et.SubElement(articles, "item")
            e = et.SubElement(item, "Title")
            if idx > 0:
                e.text = str(idx)+". "+text
            else:
                e.text = text
            e = et.SubElement(item, "Description")
            e.text = detail
            e = et.SubElement(item, "PicUrl")
            e.text = pic
            e = et.SubElement(item, "Url")
            if len(url) == 0:
                e.text = ""
            else:
                e.text = "http://www.nossiac.com/wx"+url
            idx = idx + 1

        rsp = et.tostring(rspxml, encoding="utf-8")
        print("Response:\n"+rsp.decode("utf-8"))
        self.write(rsp.decode("utf-8"))

    def sendtext(self, text, msg):
        """
        a menu entry should be like:
            [(text, detail=None, pic=None, url=None)]
        """
        rspxml = et.Element("xml")
        e = et.SubElement(rspxml, "ToUserName")
        e.text = msg["FromUserName"]
        e = et.SubElement(rspxml, "FromUserName")
        e.text = msg["ToUserName"]
        e = et.SubElement(rspxml, "CreateTime")
        e.text = str(int(time.time()))
        e = et.SubElement(rspxml, "MsgType")
        e.text = "text"
        e = et.SubElement(rspxml, "Content")
        e.text = text
        rsp = et.tostring(rspxml, encoding="utf-8")
        print("Response:\n"+rsp.decode("utf-8"))
        self.write(rsp.decode("utf-8"))

    def addlog(self, msg, *args):
        if msg["MsgType"] == "event":
            db.addlog(msg["FromUserName"], msg["Event"], ",".join(args))
        else:
            db.addlog(msg["FromUserName"], msg["MsgType"], ",".join(args))

    def sendMenu(self, menu, msg):
        """
        Send a menu to subscriber.
        A menu entry should be like:
            [(text, detail=None, pic=None, url=None)]
        """
        rspxml = et.Element("xml")
        e = et.SubElement(rspxml, "ToUserName")
        e.text = msg["FromUserName"]
        e = et.SubElement(rspxml, "FromUserName")
        e.text = msg["ToUserName"]
        e = et.SubElement(rspxml, "CreateTime")
        e.text = str(int(time.time()))
        e = et.SubElement(rspxml, "MsgType")
        e.text = "news"
        e = et.SubElement(rspxml, "ArticleCount")
        e.text = str(len(menu))
        articles = et.SubElement(rspxml, "Articles")
        idx = 0
        for entry in menu:
            text, detail, pic, url, cb, auth = entry
            item = et.SubElement(articles, "item")
            e = et.SubElement(item, "Title")
            if idx > 0:
                e.text = str(idx)+". "+text
            else:
                e.text = text
            e = et.SubElement(item, "Description")
            e.text = detail
            e = et.SubElement(item, "PicUrl")
            e.text = pic
            e = et.SubElement(item, "Url")
            if len(url) == 0:
                e.text = ""
            else:
                e.text = url
            idx = idx + 1

        rsp = et.tostring(rspxml, encoding="utf-8")
        print("Response:\n"+rsp.decode("utf-8"))
        self.write(rsp.decode("utf-8"))

    def sendText(self, text, msg):
        """
        Send a text to subscriber.
        """
        rspxml = et.Element("xml")
        e = et.SubElement(rspxml, "ToUserName")
        e.text = msg["FromUserName"]
        e = et.SubElement(rspxml, "FromUserName")
        e.text = msg["ToUserName"]
        e = et.SubElement(rspxml, "CreateTime")
        e.text = str(int(time.time()))
        e = et.SubElement(rspxml, "MsgType")
        e.text = "text"
        e = et.SubElement(rspxml, "Content")
        e.text = text
        rsp = et.tostring(rspxml, encoding="utf-8")
        print("Response:\n"+rsp.decode("utf-8"))
        self.write(rsp.decode("utf-8"))

    def sendNews(self, msg):
        rspxml = et.Element("xml")
        e = et.SubElement(rspxml, "ToUserName")
        e.text = msg["FromUserName"]
        e = et.SubElement(rspxml, "FromUserName")
        e.text = msg["ToUserName"]
        e = et.SubElement(rspxml, "CreateTime")
        e.text = str(int(time.time()))
        e = et.SubElement(rspxml, "MsgType")
        e.text = "news"
        e = et.SubElement(rspxml, "ArticleCount")
        e.text = "3"
        articles = et.SubElement(rspxml, "Articles")
        item = et.SubElement(articles, "item")
        e = et.SubElement(item, "Title")
        e.text = "first news!"
        e = et.SubElement(item, "Description")
        e.text = "Hollywood fades away in China!"
        e = et.SubElement(item, "PicUrl")
        e.text = "http://www.nossiac.com/static/images/360-200.jpg"
        e = et.SubElement(item, "Url")
        e.text = "http://www.163.com"
        item = et.SubElement(articles, "item")
        e = et.SubElement(item, "Title")
        e.text = "second news!"
        e = et.SubElement(item, "Description")
        e.text = "Are you ready for the comming challeng!"
        e = et.SubElement(item, "PicUrl")
        e.text = "http://www.nossiac.com/static/images/200-200.jpg"
        e = et.SubElement(item, "Url")
        e.text = ""
        item = et.SubElement(articles, "item")
        e = et.SubElement(item, "Title")
        e.text = u"第三行是个菜单!"
        e = et.SubElement(item, "Description")
        e.text = "This is an empty menu!"
        e = et.SubElement(item, "PicUrl")
        e.text = ""
        e = et.SubElement(item, "Url")
        e.text = "http://www.nossiac.com/wx/dump"

        rsp = et.tostring(rspxml, encoding="utf-8")
        print("Response:\n"+rsp.decode("utf-8"))
        self.write(rsp.decode("utf-8"))

    def handleText(self, msg):
        if msg["Content"].find("tuwen") != -1:
            return self.sendNews(msg)

        rspxml = et.Element("xml")
        e = et.SubElement(rspxml, "ToUserName")
        e.text = msg["FromUserName"]
        e = et.SubElement(rspxml, "FromUserName")
        e.text = msg["ToUserName"]
        e = et.SubElement(rspxml, "CreateTime")
        e.text = str(int(time.time()))
        e = et.SubElement(rspxml, "MsgType")
        e.text = "text"
        e = et.SubElement(rspxml, "Content")

        if msg["Content"].find("shangwang") != -1:
            e.text = u"http://mp.weixin.qq.com/wiki/home/fans?id=wx"+msg["FromUserName"]+u"wx"
        else:
            e.text = msg["Content"]+u"\n----一直模仿，从未超越"

        rsp = et.tostring(rspxml, encoding="utf-8")
        print("Response:\n"+rsp.decode("utf-8"))
        self.write(rsp.decode("utf-8"))

    def dumpMsg(self, msg):
        print(len(msg),type(msg))

        for k,v in msg.items():
            if v != None:
                print("dump req: <%s> = <%s>"%(k,v))

        if msg["MsgType"] == "text":
            self.addlog(msg, msg["Content"])
        elif msg["MsgType"] == "image":
            print("Got image from <%s>."%(msg["FromUserName"]))
            self.addlog(msg, msg["MediaId"], msg["PicUrl"])
        elif msg["MsgType"] == "voice":
            print("Got voice from <%s>."%(msg["FromUserName"]))
            self.addlog(msg, msg["MediaId"], msg["Format"])
        elif msg["MsgType"] == "video":
            print("Got video from <%s>."%(msg["FromUserName"]))
            db.addlog(msg, msg["MediaId"], msg["ThumbMediaId"])
        elif msg["MsgType"] == "location":
            print("Got location from <%s>."%(msg["FromUserName"]))
            db.addlog(msg, msg["Location_X"], msg["Location_Y"], msg["Scale"], msg["Label"])
        elif msg["MsgType"] == "link":
            print("Got link from <%s>."%(msg["FromUserName"]))
            self.addlog(msg, msg["Title"], msg["Url"], msg["Description"])
        elif msg["MsgType"] == "event":
            if msg["Event"] == "subscribe":
                print("Got subscribe event from <%s>."%(msg["FromUserName"]))
                if msg["EventKey"] != None and  msg["Ticket"] != None:
                    self.addlog(msg, msg["EventKey"], msg["Ticket"])
                else:
                    self.addlog(msg)
                db.addauth(openid=msg["FromUserName"], fans="1", subscribe=msg["CreateTime"], lastactive=msg["CreateTime"])
            elif msg["Event"] == "unsubscribe":
                print("Got unsubscribe event from <%s>."%(msg["FromUserName"]))
                self.addlog(msg)
                db.addauth(openid=msg["FromUserName"], fans="0", unsubscribe=msg["CreateTime"], lastactive=msg["CreateTime"])
            elif msg["Event"] == "SCAN":
                print("Got SCAN event from <%s>."%(msg["FromUserName"]))
                self.addlog(msg, msg["EventKey"], msg["Ticket"])
            elif msg["Event"] == "LOCATION":
                print("Got LOCATION event from <%s>."%(msg["FromUserName"]))
                self.addlog(msg, msg["Latitude"], msg["Longitude"], msg["Precision"])
            elif msg["Event"] == "CLICK":
                print("Got CLICK event from <%s>."%(msg["FromUserName"]))
                self.addlog(msg, msg["EventKey"])
            elif msg["Event"] == "VIEW":
                print("Got VIEW event from <%s>."%(msg["FromUserName"]))
                self.addlog(msg, msg["EventKey"])
            else:
                print("Unsupported Event! %s"%(msg["Event"]))
                self.addlog(msg, msg["EventKey"])
        else:
            print("Unsupported MsgType! %s"%(msg["MsgType"]))

    def parseMsg(self):
        """
        Transform XML msg into dict.
        """
        # These 4 elements are always present
        #     "ToUserName"
        #     "FromUserName"
        #     "CreateTime"
        #     "MsgType"

        # Following elements depends on MsgType
        #     "MsgId"
        #     "Content"
        #     "MediaId"
        #     "PicUrl"
        #     "Format"
        #     "ThumbMediaId"
        #     "Location_X"
        #     "Location_Y"
        #     "Scale"
        #     "Label"
        #     "Title"
        #     "Description"
        #     "Url"
        #     "Event"
        #     "EventKey"
        #     "Ticket"
        #     "Latitude"
        #     "Longitude"
        #     "Precision"
        #     "Recognition"

        def getField(req, key):
            if req.find(key) != None:
                return req.find(key).text


        msg = {}
        req = et.fromstring(self.request.body.decode("utf-8"))

        # These 4 elements are always present
        msg["ToUserName"] = getField(req, "ToUserName")
        msg["FromUserName"] = getField(req, "FromUserName")
        msg["CreateTime"] = getField(req, "CreateTime")
        msg["MsgType"] = getField(req, "MsgType")

        # Following elements depends on MsgType
        msg["MsgId"] = getField(req, "MsgId")
        msg["Content"] = getField(req, "Content")
        msg["MediaId"] = getField(req, "MediaId")
        msg["PicUrl"] = getField(req, "PicUrl")
        msg["Format"] = getField(req, "Format")
        msg["ThumbMediaId"] = getField(req, "ThumbMediaId")
        msg["Location_X"] = getField(req, "Location_X")
        msg["Location_Y"] = getField(req, "Location_Y")
        msg["Scale"] = getField(req, "Scale")
        msg["Label"] = getField(req, "Label")
        msg["Title"] = getField(req, "Title")
        msg["Description"] = getField(req, "Description")
        msg["Url"] = getField(req, "Url")
        msg["Event"] = getField(req, "Event")
        msg["EventKey"] = getField(req, "EventKey")
        msg["Ticket"] = getField(req, "Ticket")
        msg["Latitude"] = getField(req, "Latitude")
        msg["Longitude"] = getField(req, "Longitude")
        msg["Precision"] = getField(req, "Precision")
        msg["Recognition"] = getField(req, "Recognition")
        return msg

    def post(self):
        msg = self.parseMsg()
        self.dumpMsg(msg)
        openid = msg["FromUserName"]
        print(openid)
        content = msg["Content"]

        mtype="admin"

        menu_entries = [
                ("你好，Admin。", "", "http://www.nossiac.com/static/images/360-200.jpg", "", None, "admin"),
                ("你好，健将。", "", "http://www.nossiac.com/static/images/360-200.jpg", "", None,  "member"),
                ("你好，Fans。", "", "http://www.nossiac.com/static/images/360-200.jpg", "", None,  "fans"),
                ("课程表", "", "", "/courses?openid="+openid, None, "fans, member, admin"),
                ("活动查询与报名", "", "", "/activity?action=history&openid="+openid, None, "member, admin"),
                ("个人信息", "", "", "/member?action=edit&openid="+openid, None, "member, admin"),
                ("会员信息", "", "", "/member?action=all&openid="+openid, None, "admin,member"),
                ("会员通知（邮件+微信）", "", "", "/notify?openid="+openid, None, "admin"),
                ("关于外研社", "", "", "/about", None, "fans, member, admin"),
                ("使用帮助", "", "", "/help", None, "fans, member, admin"),
                ("意见反馈", "", "", "/feedback?openid="+openid, None, "admin,member"),
                ("会员认证", "", "", "/member?action=reg&openid="+openid, None, "fans"),
                ]

        if str.isdigit(content):
            instruction = int(content)
            counter = 0
            for menu in menu_entries:
                print(menu[-1], mtype)
                if menu[-1].find(mtype) != -1:
                    counter = counter + 1
                    if counter == instruction:
                        self.sendText(menu[-2](openid), msg)
                        break
            else:
                self.sendText("错误的指令。\n输入？获得帮助。", msg)
        else:
            tmpmenu=[]
            for each in menu_entries:
                if each[5].find(mtype) >= 0:
                    tmpmenu.append(each)
            self.sendMenu(tmpmenu, msg)
            #self.sendNews(msg)


    def post(self):
        self.dumpmsg(self)
        msg = self.parsemsg()
        openid = msg["FromUserName"]
        print(openid)
        mtype = db.membertype(openid) or "fans"
        print(mtype)
        content = msg["Content"]

        menus = [
                ("你好，Admin。", "", "http://www.shello.name/static/images/360-200.jpg", "",  "", "admin"),
                ("你好，健将。", "", "http://www.shello.name/static/images/360-200.jpg", "", "",  "member"),
                ("你好，Fans。", "", "http://www.shello.name/static/images/360-200.jpg", "", "",  "fans"),
                ("课程表", "", "", "/courses?openid="+openid, self.courses, "fans, member, admin"),
                ("活动查询与报名", "", "", "/activity?action=history&openid="+openid, self.activity, "member, admin"),
                ("个人信息", "", "", "/member?action=edit&openid="+openid, self.aboutme, "member, admin"),
                ("会员信息", "", "", "/member?action=all&openid="+openid, self.members, "admin,member"),
                ("会员通知（邮件+微信）", "", "", "/notify?openid="+openid, self.notify, "admin"),
                ("关于健身社", "", "", "/about", self.aboutclub, "fans, member, admin"),
                ("使用帮助", "", "", "/help", self.help, "fans, member, admin"),
                ("意见反馈", "", "", "/feedback?openid="+openid, "", "admin,member"),
                ("会员认证", "", "", "/member?action=reg&openid="+openid, self.auth, "fans"),
                ]

        if str.isdigit(content):
            instruction = int(content)
            counter = 0
            for menu in menus:
                print(menu[-1], mtype)
                if menu[-1].find(mtype) != -1:
                    counter = counter + 1
                    if counter == instruction:
                        self.sendtext(menu[-2](openid), msg)
                        break
            else:
                self.sendtext("错误的指令。\n输入？获得帮助。", msg)
        else:
            tmpmenu=[]
            for each in menus:
                if each[5].find(mtype) >= 0:
                    tmpmenu.append(each)
            self.sendmenu(tmpmenu, msg)

    def get(self):
        if not self.verify():
            self.write("no,no,no")
        else:
            echostr = self.get_argument("echostr", "<none>")
            self.write(echostr)


class WXDump(tornado.web.RequestHandler):
    def get(self):
        print(self.request)
        self.write("WXDump!")
        log = db.getlog()
        auth = db.getauth()
        self.render("wx/dump.htm", log=log, auth=auth)



if __name__=="__main__":
    import requests
    import sys
    url = "http://192.168.0.200:8081/wx"
    msg = """<xml>
    <ToUserName><![CDATA[toUser]]></ToUserName>
    <FromUserName><![CDATA[fromUser]]></FromUserName>
    <CreateTime>1348831860</CreateTime>
    <MsgType><![CDATA[text]]></MsgType>
    <Content><![CDATA[{0}]]></Content>
    <MsgId>1234567890123456</MsgId>
    </xml>""".format(sys.argv[1])

    r = requests.post(url, msg)