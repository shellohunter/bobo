import tornado.httpserver
import tornado.web
import tornado.ioloop
import json
import sqlite3

from io import StringIO


# database path of enclub
enc_db_path = "wx/enclub/.wx.sqlite3.py"

class EnClubDB():
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
            if "member" == each[0]:
                print("EnClub db exists.")
                return
        #if "member" in tables:
        #    print("EnClub db exists.")
        #    return
        else:
            print("EnClub does not exist, create it now.")

        tmp = """CREATE TABLE member (
                openid text,
                name text,
                email text,
                type text,
                score integer,
                hw integer
                )"""
        self.dbcusor.execute(tmp)

        tmp = """CREATE TABLE homework (
                id integer,
                item text,
                point integer
                )"""
        self.dbcusor.execute(tmp)

        self.dbconn.commit()

class EnClubDump(tornado.web.RequestHandler):
    def get(self):
        self.dbconn = sqlite3.connect(enc_db_path)
        self.dbcusor = self.dbconn.cursor()
        self.dbcusor.execute("SELECT * FROM member ORDER BY name")
        members = self.dbcusor.fetchall()
        print(members)
        self.dbcusor.execute("SELECT * FROM homework ORDER BY id")
        homework = self.dbcusor.fetchall()
        print(homework)
        self.render("wx/enc/dump.html", members=members, homework=homework)

class EnClubReg(tornado.web.RequestHandler):
    def get(self):
        openid = self.get_argument("openid", None)
        if openid is not None:
            self.render("wx/enc/reg.html", openid=openid)
        else:
            self.write("not allowed!")

    def post(self):
        openid=self.get_argument("openid", None)
        email=self.get_argument("email", None)
        if not openid or not email:
            return self.write("invalid argument!")

        self.dbconn = sqlite3.connect(enc_db_path)
        self.dbcusor = self.dbconn.cursor()
        cmd = """INSERT INTO member(openid, name, email, type, score, hw)
                 VALUES(?,?,?,?,?,?)"""
        self.dbcusor.execute(cmd, (openid, "", email, "member", 0, 0))
        self.dbconn.commit()

        # save. openid & email.
        self.write("welcome!")

class EnClubAddTest(tornado.web.RequestHandler):
    def get(self):
        openid = self.get_argument("openid", None)
        if openid is not None:
            self.render("wx/enc/addtest.html", openid=openid)
        else:
            self.write("not allowed!")

    def post(self):
        openid=self.get_argument("openid", None)

        xml=self.get_argument("xml", None)
        if xml:
            point = self.get_argument("point", 1)
            self.dbconn = sqlite3.connect(enc_db_path)
            self.dbcusor = self.dbconn.cursor()
            cmd = """INSERT INTO homework(id, item, point)
                     VALUES(?,?,?)"""
            self.dbcusor.execute(cmd, (openid, xml, point))
            self.dbconn.commit()

            return self.write("Appreciate  your contribution!")

        qtype=self.get_argument("type", None)
        point=self.get_argument("point", None)

        if qtype == "choose":
            question = self.get_argument("question", "")
            option_a = self.get_argument("A", "")
            option_b = self.get_argument("B", "")
            option_c = self.get_argument("C", "")
            option_d = self.get_argument("D", "")
            answer   = self.get_argument("answer", "")
            point    = self.get_argument("point", 1)

            print("question={0}\noption_a:{1}\noption_b:{2}\
                \noption_c:{3}\noption_d:{4}\nanswer={5}\npoint={6}\n".format(
                question, option_a, option_b, option_c,
                option_d, answer, point
                )
            )
        elif qtype == "fill":
            pass
        elif qtype == "read":
            pass
        elif qtype == "listen":
            pass
        elif qtype == "dictate":
            pass
        else:
            pass

        item = {}
        item["type"] = qtype
        item["id"] = 0
        item["question"] = question
        item["options"] = [
            ("A", option_a),
            ("B", option_b),
            ("C", option_c),
            ("D", option_d),
        ]
        item["answer"] = answer

        io = StringIO()
        json.dump(item, io)
        xml = io.getvalue()
        return self.render("wx/enc/test.html", 
            openid=openid, item=item, point=point, xml=xml)



class ItemUI(tornado.web.UIModule):
    def render(self, item):
        if item["type"] == "choose":
            return self.render_string('wx/enc/ui_choose.html', item=item)
        elif item["type"] == "fill":
            return self.render_string('wx/enc/ui_fill.html', item=item)
        elif item["type"] == "dictate":
            return self.render_string('wx/enc/ui_fill.html', item=item)
        else:
            return self.render_string('wx/enc/ui_fill.html', item=item)


class EnClubTest(tornado.web.RequestHandler):
    def get(self, id=0):
        openid = self.get_argument("openid", None)
        if openid is None:
            print("not a member!")
            self.write("you are not a member yet.")
            return

        self.dbconn = sqlite3.connect(enc_db_path)
        self.dbcusor = self.dbconn.cursor()
        cmd = """SELECT * FROM homework WHERE ROWID=?"""
        self.dbcusor.execute(cmd, (id,))
        item = self.dbcusor.fetchall()
        print("======", item)
        item = {}
        item["type"] = "choose"
        item["id"] = 0
        item["question"] = "Many a house ____ been built these years."
        item["options"] = [
            ("A", "has"),
            ("B", "have"),
            ("C", "is"),
            ("D", "are"),
        ]
        item["answer"] = "AB"
        self.render("wx/enc/test.html", openid=openid, item=item, xml=None)

    def post(self):
        openid=self.get_argument("openid", None)
        email=self.get_argument("email", None)
        # save.
        self.write("OK!")

from wx.wxbase import WXBase

class EnClubCodes(WXBase):
    @staticmethod
    def handleCode(self, code, msg):
        openid = msg["FromUserName"]
        print("EnClubCodes.handleCode({0})".format(code))

        # if user is not our member.
        menu = [
            ("Hello，Fans。", "", "http://www.nossiac.com/static/images/360-200.jpg", "", None,  "fans"),
            ("Register", "", "", "/wx/enc/reg?openid="+openid, None, "fan"),
            ("About Me", "", "", "/wx/enc/me?openid="+openid, None, "member, admin"),
            ("Homework", "", "", "/wx/enc/test?&openid="+openid, None, "member, admin"),
        ]
        self.sendMenu(menu, msg)
        return 123

class EnClub():
    def __init__(self):
        EnClubDB(enc_db_path)

    def handlers(self):
        return [
            (r'/wx/enc/reg', EnClubReg),
            (r'/wx/enc/dump', EnClubDump),
            (r'/wx/enc/addtest', EnClubAddTest),
            (r'/wx/enc/test/*', EnClubTest),
            (r'/wx/enc/test/(\d+)', EnClubTest),
        ]

    def codes(self):
        return [
            (r'enclub', EnClubCodes.handleCode)
        ]

    def uimodules(self):
        return [
            {'Item':ItemUI}
        ]