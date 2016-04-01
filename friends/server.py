import tornado.ioloop
import tornado.web
import os, os.path
import tornado.httpserver
import sqlite3
import arrow
import datetime
from rd import RD, Link
import hashlib
db = None
#insert into user (name,email) values('mikael','mikael@frykholm.com');
#insert into entry (userid,text) values (1,'My thoughts on ostatus');
import tornado.options

settings = {
    "static_path": os.path.join(os.path.dirname(__file__), "static"),
    "cookie_secret": "__TODO:_GENERATE_YOUR_OWN_RANDOM_VALUE_HERE__",
    "login_url": "/login",
    "xsrf_cookies": False,
    "domain":"https://ronin.frykholm.com",
    
}
class PushHandler(tornado.web.RequestHandler):
#curl -v -k "https://ronin.frykholm.com/hub" -d "hub.callback=a" -d "hub.mode=b" -d "hub.topic=c" -d "hub.verify=d"
    def post(self):
        """ Someone wants to subscribe to hub_topic feed"""
        hub_callback = self.get_argument('hub.callback')
        hub_mode = self.get_argument('hub.mode')
        hub_topic = self.get_argument('hub.topic')
        hub_verify = self.get_argument('hub.verify')
        hub_lease_seconds = self.get_argument('hub.lease_seconds','')
        hub_secret = self.get_argument('hub.sercret','')
        hub_verify_token = self.get_argument('hub.verify_token','')
        print(self.request.body)
        if hub_mode == 'unsubscribe':
            pass #FIXME
        path = hub_topic.split(self.settings['domain'])[1]
        user = path.split('user/')[1]
        row = db.execute("select id from user where name=?",(user,)).fetchone()
        if row: #FIXME calculate expire timestamp
            db.execute("INSERT into subscriptions (userid, expires, callback, secret, verified) values (?,?,?,?)",(row['id'],datetime.datetime.now(),hub_secret,hub_callback,False))
            db.commit()
            self.set_status(202)
            #TODO add GET callback with the same data we got
            #TODO add secret to outgoing feeds with hmac

class XrdHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("templates/xrd.xml", hostname="ronin.frykholm.com", url=self.settings['domain'])

class FingerHandler(tornado.web.RequestHandler):
    def get(self):
        user = self.get_argument('resource')
        user = user.split('acct:')[1]
        (user,domain) = user.split('@')
        rows = db.execute("select id from user where user.name=?",(user,)).fetchone()
        if not rows:
            self.set_status(404)
            self.write("Not found")
            self.finish()
            return
        lnk = Link(rel='http://spec.example.net/photo/1.0', 
                   type='image/jpeg', 
                   href='{}/static/{}.jpg'.format(self.settings['domain'],user))
        lnk.titles.append(('User Photo', 'en'))
        lnk.titles.append(('Benutzerfoto', 'de'))
        lnk.properties.append(('http://spec.example.net/created/1.0', '1970-01-01'))
        lnk2 = Link(rel='http://schemas.google.com/g/2010#updates-from', 
                    type='application/atom+xml', 
                    href='{}/user/{}'.format(self.settings['domain'],user))

        rd = RD(subject='{}/{}'.format(self.settings['domain'],user))
        rd.properties.append('http://spec.example.net/type/person')
        rd.links.append(lnk)
        rd.links.append(lnk2)
        self.write(rd.to_json())

class UserHandler(tornado.web.RequestHandler):
    def get(self, user):
        entries = db.execute("select entry.id,text,ts from user,entry where user.id=entry.userid and user.name=?",(user,))
        #import pdb;pdb.set_trace()
        self.set_header("Content-Type", 'application/atom+xml')
        self.render("templates/feed.xml", 
                    user=user, 
                    feed_url="{}/user/{}".format(self.settings['domain'], user), 
                    hub_url="{}/hub".format(self.settings['domain']), 
                    entries=entries,
                    arrow=arrow )

application = tornado.web.Application([
    (r"/.well-known/host-meta", XrdHandler),
    (r"/.well-known/webfinger", FingerHandler),
    (r"/user/(.+)", UserHandler),
    (r"/hub", PushHandler),
    ],debug=True,**settings)
srv = tornado.httpserver.HTTPServer(application, ssl_options={
        "certfile":  "ronin.frykholm.com.pem",
        "keyfile":  "ronin.frykholm.com.key",
    })
def setup_db(path):
    print("No db found, creating in {}".format(path))
    con = sqlite3.connect(path)
    con.execute(""" create table user (id integer primary key,
                                       name varchar,
                                       email varchar);
                    create table entry (id integer primary key, 
                                        userid INTEGER, 
                                        text varchar,
                                        ts timestamp default current_timestamp,
                                        FOREIGN KEY(userid) REFERENCES user(id));
                    create table subscriptions (id integer primary key,
                                        userid integer,
                                        expires datetime,
                                        callback varchar,
                                        secret varchar,
                                        verified bool,
                                        FOREIGN KEY(userid) REFERENCES user(id));""")
    con.commit()

if __name__ == "__main__":
    dbPath = 'friends.db'
    tornado.options.parse_command_line()
    if not os.path.exists(dbPath):
        setup_db(dbPath)
    db = sqlite3.connect(dbPath, detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
    db.row_factory = sqlite3.Row
    srv.listen(443)
    tornado.ioloop.IOLoop.instance().start()
