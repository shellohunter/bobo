import tornado.httpserver
import tornado.web
import tornado.ioloop
import json
import sqlite3

from io import StringIO


# database path of enclub
enc_db_path = "wx/enclub/.enclub.sqlite3.py"

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
                openid TEXT,
                name TEXT,
                email TEXT,
                type TEXT,
                score INTEGER,
                hw INTEGER
                )"""
        self.dbcusor.execute(tmp)

        tmp = """CREATE TABLE homework (
                id INTEGER PRIMARY KEY,
                item TEXT,
                point INTEGER
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

        item_json=self.get_argument("item_json", None)
        if item_json:
            point = self.get_argument("point", 1)
            self.dbconn = sqlite3.connect(enc_db_path)
            self.dbcusor = self.dbconn.cursor()
            cmd = """INSERT INTO homework VALUES(?,?,?)"""
            self.dbcusor.execute(cmd, (None, item_json, point))
            self.dbconn.commit()

            return self.write("Appreciate  your contribution!")

        qtype=self.get_argument("type", None)
        item = {}
        item_json = ""
        point    = self.get_argument("point", 1)

        print("AAAAAAAA",qtype)
        if qtype == "choose":
            print("BBBBBBBB")
            question = self.get_argument("question", "")
            option_a = self.get_argument("A", "")
            option_b = self.get_argument("B", "")
            option_c = self.get_argument("C", "")
            option_d = self.get_argument("D", "")
            answer   = self.get_argument("answer", "")

            print("question={0}\noption_a:{1}\noption_b:{2}\
                \noption_c:{3}\noption_d:{4}\nanswer={5}\npoint={6}\n".format(
                question, option_a, option_b, option_c,
                option_d, answer, point
                )
            )

            item["type"] = qtype
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
            item_json = io.getvalue()

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

        return self.render("wx/enc/test.html", 
            openid=openid, item=item, point=point, item_json=item_json, qid="Preview")



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
    def get(self, qid=0):
        openid = self.get_argument("openid", None)
        if openid is None:
            print("not a member!")
            self.write("you are not a member yet.")
            return

        self.dbconn = sqlite3.connect(enc_db_path)
        self.dbcusor = self.dbconn.cursor()
        cmd = """SELECT * FROM homework WHERE ROWID=?"""
        self.dbcusor.execute(cmd, (qid,))

        item = self.dbcusor.fetchone()
        print("======", item)
        if item:
            print(json.loads(item[1]))
            self.render("wx/enc/test.html", openid=openid,
                item=json.loads(item[1]), qid=qid, item_json=None)
        else:
            self.write("no such item.")

    def post(self, qid):
        openid = self.get_argument("openid", None)
        answer = self.get_argument("answer", None)

        if not qid or not openid or not answer:
            self.write("Invalid answer!")
        else:
            self.dbconn = sqlite3.connect(enc_db_path)
            self.dbcusor = self.dbconn.cursor()
            cmd = "SELECT item FROM homework WHERE id=?"
            self.dbcusor.execute(cmd, (qid,))
            item = self.dbcusor.fetchone()
            print("item", item)
            item = json.loads(item[0])
            #print(set(answer.strip().upper()))
            #print(set(item["answer"].strip().upper()))
            if set(answer.strip().upper()) == set(item["answer"].strip().upper()):
                self.write("OK!")
            else:
                self.write("Wrong!")

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
        return True # we have ended the code, no more procedure.

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