

import os.path
import tornado.httpserver
import tornado.web
import tornado.ioloop
import tornado.options

class TestHandler(tornado.web.RequestHandler):
	def get(self, result = ""):
		if result:
			result="{0:09x}".format(int(result, 16))
			t1 = int(result[0], 16)
			t2 = int(result[1], 16)
			t3 = int(result[2], 16)
			t4 = int(result[3], 16)
			t5 = int(result[4], 16)
			t6 = int(result[5], 16)
			t7 = int(result[6], 16)
			t8 = int(result[7], 16)
			t9 = int(result[8], 16)

			self.render("t9x/radar.html",
				t1=t1, t2=t2, t3=t3,
				t4=t4, t5=t5, t6=t6,
				t7=t7, t8=t8, t9=t9,
				)
		else:
			self.render("t9x/test.html")

class T9x(object):
    def handlers(self):
        return [
			(r'/9x/*(.*)', TestHandler),
        ]


if __name__ == "__main__":
	from tornado.options import define, options
	define("port", default=8081, help="http port", type=int)
	tornado.options.parse_command_line()
	app = tornado.web.Application(
		handlers=[
			(r'/9x/*(.*)', TestHandler),
		],
		debug = True,
		template_path = os.path.join(os.path.dirname(__file__), "templates/t9x"),
		static_path = os.path.join(os.path.dirname(__file__), "static/t9x"),
	)
	http_server = tornado.httpserver.HTTPServer(app)
	http_server.listen(options.port)
	tornado.ioloop.IOLoop.instance().start()
