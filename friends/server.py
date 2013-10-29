import tornado.ioloop
import tornado.web
import os
import tornado.httpserver
class XrdHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("templates/xrd.xml", hostname="ronin.local", url="https://ronin.local")

class UserHandler(tornado.web.RequestHandler):
    def get(self, user):
        #user = self.get_argument("user")
        self.render("templates/user.xml", user=user)

application = tornado.web.Application([
    (r"/.well-known/host-meta", XrdHandler),
    (r"/user/(.+)", UserHandler),
    ],debug=True,
)
srv = tornado.httpserver.HTTPServer(application, ssl_options={
        "certfile":  "ronin.local.pem",
        "keyfile":  "ronin.local.key",
    })

if __name__ == "__main__":
    srv.listen(443)
    tornado.ioloop.IOLoop.instance().start()
    