import tornado.httpserver
import tornado.web
import tornado.ioloop
import json
import sqlite3
import datetime

from io import StringIO


# database path of enclub
enc_db_path = "wx/enclub/.enclub.sqlite3.py"

def identify(openid, dbcusor=None):
    if not openid:
        return
    if not dbcusor:
        dbcusor = sqlite3.connect(enc_db_path).cursor()

    cmd = "SELECT name,openid,type FROM member WHERE openid=?"
    dbcusor.execute(cmd, (openid,))

    ret = dbcusor.fetchone()
    return ret


class EnClubDB():
    def __init__(self, path=None):
        if path != None:
            self.dbconn = sqlite3.connect(path)
        else:
            self.dbconn = sqlite3.connect(".wx.sqlite3.py")

        self.dbcusor = self.dbconn.cursor()
        self.dbcusor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = self.dbcusor.fetchall()
        for each in tables:
            if "member" == each[0]:
                return

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

        tmp = """CREATE TABLE log (
                id INTEGER PRIMARY KEY,
                who TEXT,
                when_ TEXT,
                what TEXT
                )"""
        # when is a keyword of sqlite3 ?
        self.dbcusor.execute(tmp)

        self.dbconn.commit()

class EnClubDump(tornado.web.RequestHandler):
    def get(self):
        self.dbconn = sqlite3.connect(enc_db_path)
        self.dbcusor = self.dbconn.cursor()
        self.dbcusor.execute("SELECT * FROM member ORDER BY name")
        members = self.dbcusor.fetchall()
        self.dbcusor.execute("SELECT * FROM homework ORDER BY id")
        homework = self.dbcusor.fetchall()
        self.render("wx/enc/dump.html", members=members,
            homework=homework)

class EnClubMe(tornado.web.RequestHandler):
    def get(self):
        openid = self.get_argument("openid", None)
        if not identify(openid):
            return self.render("wx/enc/error.html",
                info="Your provided an invalid ID!")
        self.dbconn = sqlite3.connect(enc_db_path)
        self.dbcusor = self.dbconn.cursor()
        self.dbcusor.execute("SELECT * FROM member WHERE openid=?", (openid,))
        me = self.dbcusor.fetchone()

        self.render("wx/enc/me.html", me=me)


class EnClubLog(tornado.web.RequestHandler):
    def get(self):
        self.dbconn = sqlite3.connect(enc_db_path)
        self.dbcusor = self.dbconn.cursor()
        self.dbcusor.execute("SELECT * FROM log ORDER BY id")
        log = self.dbcusor.fetchall()
        self.render("wx/enc/log.html", log=log)


class EnClubDBG(tornado.web.RequestHandler):
    def get(self):
        urls = [
        "/wx/enc/log",
        "/wx/enc/dump",
        "/wx/enc/reg",
        "/wx/enc/reg?openid=xxx",
        "/wx/enc/reg?openid=12344",
        "/wx/enc/me",
        "/wx/enc/me?openid=xxx",
        "/wx/enc/me?openid=12344",
        "/wx/enc/addtest",
        "/wx/enc/addtest?openid=xxx",
        "/wx/enc/addtest?openid=12344",
        "/wx/enc/test?id=0",
        "/wx/enc/test?id=0&openid=xxx",
        "/wx/enc/test?id=0&openid=12344",
        "/wx/enc/test?id=1",
        "/wx/enc/test?id=1&openid=xxx",
        "/wx/enc/test?id=1&openid=12344",
        "/wx/enc/test?id=1&openid=12344&fr=1&to=5",
        "/wx/enc/test?id=1&openid=12344&fr=2&to=4",
        "/wx/enc/test?id=x",
        "/wx/enc/test?id=x&openid=xxx",
        "/wx/enc/test?id=x&openid=12344",
        ]
        links = ["<a href=\""+x+"\">"+x+"</a>" for x in urls]

        return self.write("<br>\n".join(links))

class EnClubReg(tornado.web.RequestHandler):
    def get(self):
        openid = self.get_argument("openid", None)
        if not openid:
            return self.render("wx/enc/error.html",
                info="You must register in wechat!")

        if identify(openid):
            return self.render("wx/enc/error.html",
                info="This wechat account has already registered in the club!")

        self.render("wx/enc/reg.html", openid=openid)

    def post(self):
        openid=self.get_argument("openid", None)
        email=self.get_argument("email", None)
        name=self.get_argument("name", None)
        if not openid:
            return self.render("wx/enc/error.html",
                info="You must register in wechat!")
        elif not email:
            return self.render("wx/enc/error.html",
                info="Email address cannot be empty!")
        elif not name:
            return self.render("wx/enc/error.html",
                info="Nickname cannot be empty!")

        with open("wx/enclub/member.list", "rb") as fp:
            data = fp.read()
            data = data.decode("utf-8")
            if data.find(email) < 0:
                return self.render("wx/enc/error.html",
                    info="Email not expected, seems you are not invited. sorry.")

        self.dbconn = sqlite3.connect(enc_db_path)
        self.dbcusor = self.dbconn.cursor()

        cmd = "SELECT openid FROM member WHERE email=?"
        self.dbcusor.execute(cmd, (email,))
        found = self.dbcusor.fetchone()
        if found:
            return self.render("wx/enc/error.html", info="Email already registered.")

        cmd = """INSERT INTO member(openid, name, email, type, score, hw)
                 VALUES(?,?,?,?,?,?)"""

        _type = "member"
        if openid=="oLXaujm8FO_2mnq3ummrE2V7ajwQ":
            _type = "admin"
        self.dbcusor.execute(cmd, (openid, name, email, _type, 0, 0))


        cmd = """INSERT INTO log(id, who, when_, what)
                 VALUES(?,?,?,?)"""
        who = "{0}({1})".format(name, openid)
        when_ = str(datetime.datetime.utcnow()).split(".")[0]
        what = "REGISTER, email={0}, openid={1}".format(email, openid)
        self.dbcusor.execute(cmd, (None, who, when_, what))

        self.dbconn.commit()

        # save. openid & email.
        self.render("wx/enc/error.html",
            info="Welcome to English Club!")

class EnClubAddTest(tornado.web.RequestHandler):
    def get(self):
        openid = self.get_argument("openid", None)
        if identify(openid):
            self.render("wx/enc/addtest.html", openid=openid)
        else:
            self.render("wx/enc/error.html", info="You are not authorized to do this!")

    def post(self):
        openid=self.get_argument("openid", None)
        print(openid)
        me = identify(openid)
        if not me:
            return self.render("wx/enc/error.html", info="You are not authorized to do this!")

        item_json=self.get_argument("item_json", None)
        if item_json:
            point = self.get_argument("point", 1)
            self.dbconn = sqlite3.connect(enc_db_path)
            self.dbcusor = self.dbconn.cursor()
            cmd = """INSERT INTO homework VALUES(?,?,?)"""
            self.dbcusor.execute(cmd, (None, item_json, point))

            cmd = """INSERT INTO log(id, who, when_, what) VALUES(?,?,?,?)"""
            who = "{0}({1})".format(me[0], me[1])
            when_ = str(datetime.datetime.utcnow()).split(".")[0]
            what = "ADDTEST, item={0}".format(item_json)
            self.dbcusor.execute(cmd, (None, openid, when_, what))

            self.dbconn.commit()
            return self.render("wx/enc/error.html",
                info="We really appreciate your contribution!")

        qtype=self.get_argument("type", None)
        item = {}
        item_json = ""
        point = self.get_argument("point", 1)

        if qtype == "choose":
            question = self.get_argument("question", "")
            option_a = self.get_argument("A", "")
            option_b = self.get_argument("B", "")
            option_c = self.get_argument("C", "")
            option_d = self.get_argument("D", "")
            answer   = self.get_argument("answer", "")
            explain   = self.get_argument("explain", "")

            # print("question={0}\noption_a:{1}\noption_b:{2}\
            #     \noption_c:{3}\noption_d:{4}\nanswer={5}\npoint={6}\n".format(
            #     question, option_a, option_b, option_c,
            #     option_d, answer, point
            #     )
            # )

            item["type"] = qtype
            item["question"] = question
            item["options"] = [
                ("A", option_a),
                ("B", option_b),
                ("C", option_c),
                ("D", option_d),
            ]
            item["answer"] = answer
            item["explain"] = explain

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

        return self.render("wx/enc/preview.html", 
            openid=openid, item=item, point=point, item_json=item_json, id="Preview")



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


class ItemResultUI(tornado.web.UIModule):
    def render(self, item):
        if item["type"] == "choose":
            return self.render_string('wx/enc/ui_choose_result.html', item=item)
        elif item["type"] == "fill":
            return self.render_string('wx/enc/ui_fill.html', item=item)
        elif item["type"] == "dictate":
            return self.render_string('wx/enc/ui_fill.html', item=item)
        else:
            return self.render_string('wx/enc/ui_fill.html', item=item)

class EnClubTest(tornado.web.RequestHandler):
    def get(self):
        id = self.get_argument("id", 0)
        fr = self.get_argument("fr", 0)
        to = self.get_argument("to", 0)
        openid = self.get_argument("openid", None)
        if not identify(openid):
            return self.render("wx/enc/error.html",
                info="You are not a member yet. Please login via wechat.")
        #if id==0 or fr==0 or to==0 or to < fr or id < fr or to < id :
        #    return self.render("wx/enc/error.html", info="Invalid test id.")

        self.dbconn = sqlite3.connect(enc_db_path)
        self.dbcusor = self.dbconn.cursor()
        cmd = """SELECT * FROM homework WHERE id=?"""
        self.dbcusor.execute(cmd, (id,))

        item = self.dbcusor.fetchone()
        if item:
            # print(json.loads(item[1]))
            self.render("wx/enc/test.html", openid=openid,
                item=json.loads(item[1]), id=id, fr=fr, to=to)
        else:
            self.render("wx/enc/error.html", info="Invalid test id.")

    def post(self):
        id = self.get_argument("id", None)
        fr = self.get_argument("fr", None)
        to = self.get_argument("to", None)
        openid = self.get_argument("openid", None)
        answer = self.get_argument("answer", None)
        me = identify(openid)
        if not me:
            return self.render("wx/enc/error.html",
                info="You must login via wechat first!")

        if not id:
            return self.render("wx/enc/error.html", info="Invalid arguments! id missing!")

        self.dbconn = sqlite3.connect(enc_db_path)
        self.dbcusor = self.dbconn.cursor()

        who = "{0}({1})".format(me[0], me[1])
        cmd = """SELECT * FROM log WHERE who = '{0}' AND what LIKE '%TEST, id={1}%'""".format(who, id)
        self.dbcusor.execute(cmd)
        item = self.dbcusor.fetchone()

        if not item:
            self.dbcusor.execute("UPDATE member SET score=score+1 WHERE openid == ?", (openid,))
        # else:
            # print("没有分！", item)

        when_ = str(datetime.datetime.utcnow()).split(".")[0]
        what = "TEST, id={0}, answer={1}, ".format(id, answer)
        cmd = """INSERT INTO log(id, who, when_, what) VALUES(?,?,?,?)"""
        self.dbcusor.execute(cmd, (None, who, when_, what))

        self.dbconn.commit()

        next = None
        if fr and to and int(id) < int(to):
            next = "/wx/enc/test?id={0}&fr={1}&to={2}&openid={3}".format(int(id)+1, fr, to, openid)

        self.dbcusor.execute("SELECT item FROM homework WHERE id=?", (id,))
        item = self.dbcusor.fetchone()
        item = json.loads(item[0])
        if set(answer.strip().upper()) == set(item["answer"].strip().upper()):
            print("correct!")
            return self.render("wx/enc/error.html",
                info="OK! Next one!",
                next=next)
        else:
            print("Wrong!")
            #return self.render("wx/enc/error.html", info="Wrong!", next=next)
            return self.render("wx/enc/result.html", 
                openid=openid,
                item=item,
                id=id,
                fr=fr,
                to=to,
                next=next)


from wx.wxbase import WXBase

class EnClubCodes(WXBase):
    @staticmethod
    def handleCode(self, code, msg):
        openid = msg["FromUserName"]
        #print("EnClubCodes.handleCode({0})".format(code))

        headpic = "http://nossiac.com/static/images/360-200.jpg"

        who = identify(openid)
        menu = []
        if not who:
            menu.append(("Register First", "", headpic, "http://nossiac.com/wx/enc/reg?openid="+openid, None, ""))
        elif who[2] == "admin":
            menu.append(("Hello，"+who[0], "", headpic, "http://nossiac.com/wx/enc/me?openid="+openid, None, ""))
            menu.append(("Homework", "", "", "http://nossiac.com/wx/enc/test/1?&openid="+openid, None, "member, admin"))
            menu.append(("Club Log", "", "", "http://nossiac.com/wx/enc/log?&openid="+openid, None, "member, admin"))
            menu.append(("Contribute", "", "", "http://nossiac.com/wx/enc/addtest?&openid="+openid, None, "member, admin"))
        elif who[2] == "member":
            menu.append(("Hello，"+who[0], "", headpic, "http://nossiac.com/wx/enc/me?openid="+openid, None, ""))
            menu.append(("Homework", "", "", "http://nossiac.com/wx/enc/test/1?&openid="+openid, None, "member, admin"))
        else:
            menu.append(("Hello，"+who[0], "", headpic, "/wx/enc/reg?openid="+openid, None, ""))

        self.sendMenu(menu, msg)
        return True # we have ended the code, no more procedure.

class EnClub():
    def __init__(self):
        EnClubDB(enc_db_path)

    def handlers(self):
        return [
            (r'/wx/enc/reg', EnClubReg),
            (r'/wx/enc/dbg', EnClubDBG),
            (r'/wx/enc/dump', EnClubDump),
            (r'/wx/enc/log', EnClubLog),
            (r'/wx/enc/me', EnClubMe),
            (r'/wx/enc/addtest', EnClubAddTest),
            (r'/wx/enc/test', EnClubTest),
        ]

    def codes(self):
        return [
            (r'enclub', EnClubCodes.handleCode)
        ]

    def uimodules(self):
        return [
            {'Item':ItemUI},
            {'ItemResult':ItemResultUI}
        ]
