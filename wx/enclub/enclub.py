import tornado.httpserver
import tornado.web
import tornado.ioloop


class EnglishClubDB():
    def __init__(self, path=None):
        if path != None:
            self.dbconn = sqlite3.connect(path)
        else:
            self.dbconn = sqlite3.connect(".wx.sqlite3.py")

        self.dbcusor = self.dbconn.cursor()
        self.dbcusor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = self.dbcusor.fetchall()
        print(tables)
        for each in tables:
            if "log" == each[0]:
                return
        tmp = """CREATE TABLE enclub (
                openid text,
                name text,
                email text,
                intro text,
                id text,
                type text,
                score integer
                )"""
        self.dbcusor.execute(tmp)
        self.dbconn.commit()

class EnClubReg(tornado.web.RequestHandler):
    def get(self):
        wxid = self.get_argument("wxid", None)
        if wxid is not None:
            self.render("wx/enc/reg.html", wxid=wxid)
        else:
            self.write("not allowed!")

    def post(self):
        wxid=self.get_argument("wxid", None)
        email=self.get_argument("email", None)
        # save. wxid & email.
        self.write("welcome!")

class EnClubTest(tornado.web.RequestHandler):
    def get(self):
        wxid = self.get_argument("wxid", None)
        self.render("wx/enc/test1.html", wxid=wxid)

    def post(self):
        wxid=self.get_argument("wxid", None)
        email=self.get_argument("email", None)
        # save.

from wx.wxbase import WXBase

class EnClubCodes(WXBase):
    @staticmethod
    def handleCode(self, code, msg):
        openid = msg["FromUserName"]
        print("EnClubCodes.handleCode({0})".format(code))
        menu = [
            ("你好，Fans。", "", "http://www.nossiac.com/static/images/360-200.jpg", "", None,  "fans"),
            ("课程表", "", "", "/courses?openid="+openid, None, "fans, member, admin"),
            ("活动查询与报名", "", "", "/activity?action=history&openid="+openid, None, "member, admin"),
        ]
        self.sendMenu(menu, msg)
        return 123

class EnClub():
    def handlers(self):
        return [
            (r'/wx/enc/reg', EnClubReg),
            (r'/wx/enc/test/(\d+)', EnClubTest),
        ]

    def codes(self):
        return [
            (r'enclub', EnClubCodes.handleCode)
        ]

