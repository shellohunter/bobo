import tornado.web
import tornado.httpserver

class WXBase(tornado.web.RequestHandler):
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