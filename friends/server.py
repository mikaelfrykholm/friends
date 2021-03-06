#!/usr/bin/python3
import tornado.ioloop
import tornado.web
import os
import os.path
import tornado.httpserver
import tornado.httpclient as httpclient
import salmoning
import sqlite3
import arrow
import datetime
from rd import RD, Link
import hmac
from tornado.options import options, define
import logging
db = None
# insert into user (name,email) values('mikael','mikael@frykholm.com');
# insert into entry (userid,text) values (1,'My thoughts on ostatus');


settings = {
    "static_path": os.path.join(os.path.dirname(__file__), "static"),
    "cookie_secret": "supersecret123",
    "login_url": "/login",
    "xsrf_cookies": False,
    "domain":"https://ronin.frykholm.com",
    
}

#curl -v -k "https://ronin.frykholm.com/hub" -d "hub.callback=a" -d "hub.mode=b" -d "hub.topic=c" -d "hub.verify=d"

class PushHandler(tornado.web.RequestHandler):
    def post(self):
        """ Someone wants to subscribe to hub_topic feed"""
        hub_callback = self.get_argument('hub.callback')
        hub_mode = self.get_argument('hub.mode')
        hub_topic = self.get_argument('hub.topic')
        hub_verify = self.get_argument('hub.verify')
        hub_lease_seconds = self.get_argument('hub.lease_seconds','')
        hub_secret = self.get_argument('hub.secret','')
        hub_verify_token = self.get_argument('hub.verify_token','')
        print(self.request.body)
        if hub_mode == 'unsubscribe':
            pass #FIXME
        path = hub_topic.split(self.settings['domain'])[1]
        user = path.split('user/')[1]
        row = db.execute("select id from author where name=?",(user,)).fetchone()
        expire = datetime.datetime.utcnow() + datetime.timedelta(seconds=int(hub_lease_seconds))
        if row:
            db.execute("INSERT into subscriptions (author, expires, callback, secret, verified) "
                       "values (?,?,?,?,?)",(row['id'],expire,hub_callback,hub_secret,False))
            db.commit()
            self.set_status(202)
            http_client = httpclient.HTTPClient()
            try:
                response = http_client.fetch(hub_callback+"?hub.mode={}&hub.topic={}&hub.secret".format(hub_mode,hub_topic,hub_secret))
                print(response.body)
            except httpclient.HTTPError as e:
                # HTTPError is raised for non-200 responses; the response
                # can be found in e.response.
                print("Error: " + str(e))
            except Exception as e:
                # Other errors are possible, such as IOError.
                print("Error: " + str(e))
                http_client.close()
            #TODO add secret to outgoing feeds with hmac

class XrdHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("templates/xrd.xml", hostname="ronin.frykholm.com", url=self.settings['domain'])

class apa():
    def LookupPublicKey(self, signer_uri=None):
        return """RSA.jj2_lJ348aNh_9s3eCHlJlbMQdnHVm9svdU2ESW86TvV-4wZId-z3M029pjPvco0UEvlUUnJytXwoTLd70pzfZ8Cu5MMwGbvm9asI9-PKUDSNFgr5T_B017qUXOG5UH1ZNI_fVA2mSAkxxfEksv4HXg43dBvEIW94JpyAtqggHM=.AQAB.Bzz_LcnoLCu7RfDa3sMizROnq0YwzaY362UZLkA0X84KspVLhhzDI15SCLR4BdlvVhK2pa9SlH7Uku9quc2ZGNyr5mEdqjO7YTbQA9UCgbobEq2ImqV_j7Y4IfjPc8prDPCKb_mO9DUlS_ZUxJYfsOuc-SVlGmPZ93uEl8i9OjE="""


class SalmonHandler(tornado.web.RequestHandler):
    def post(self, user):
        sp = salmoning.SalmonProtocol()
        sp.key_retriever = apa()
        data = sp.ParseSalmon(self.request.body)
        pass

class FingerHandler(tornado.web.RequestHandler):
    def get(self):
        user = self.get_argument('resource')
        user = user.split('acct:')[1]
        (user,domain) = user.split('@')
        row = db.execute("select id,salmon_pubkey from author where author.name=?",(user,)).fetchone()
        if not row:
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
        rd.links.append(Link(rel="magic-public-key",
                             href="data:application/magic-public-key,RSA."+row['salmon_pubkey']))
        rd.links.append(Link(rel="salmon",
                             href="{}/salmon/{}".format(self.settings['domain'],user)))
        rd.links.append(Link(rel="http://salmon-protocol.org/ns/salmon-replies",
                             href="{}/salmon/{}".format(self.settings['domain'],user)))
        rd.links.append(Link(rel="http://salmon-protocol.org/ns/salmon-mention",
                             href="{}/salmon/{}".format(self.settings['domain'],user)))
        self.write(rd.to_json())

class UserHandler(tornado.web.RequestHandler):
    def get(self, user):
        entries = db.execute("select entry.id,text,ts from author,entry where author.id=entry.author and author.name=?",(user,))
        # import pdb;pdb.set_trace()
        self.set_header("Content-Type", 'application/atom+xml')
        out = self.render("templates/feed.xml",
                    user=user, 
                    feed_url="{}/user/{}".format(self.settings['domain'], user), 
                    hub_url="{}/hub".format(self.settings['domain']), 
                    entries=entries,
                    arrow=arrow )
        #digest = hmac.new()

    def post(self, user):
        entries = db.execute("select entry.id,text,ts from user,entry where user.id=entry.userid and user.name=?",(user,))

        self.set_header("Content-Type", 'application/atom+xml')
        out = self.render_string("templates/feed.xml",
                          user=user,
                          feed_url="{}/user/{}".format(self.settings['domain'], user),
                          hub_url="{}/hub".format(self.settings['domain']),
                          entries=entries,
                          arrow=arrow)
        #import pdb;pdb.set_trace()
        # Notify subscribers
        subscribers = db.execute("select callback, secret from subscriptions, author where author.id=subscriptions.author and author.name=?",(user,))
        for url,secret in subscribers:
            digest = hmac.new(secret.encode('utf8'), out, digestmod='sha1').hexdigest()

            req = httpclient.HTTPRequest(url=url, allow_nonstandard_methods=True,method='POST', body=out, headers={"X-Hub-Signature":"sha1={}".format(digest),"Content-Type": 'application/atom+xml',"Content-Length":len(out)})
            apa = httpclient.HTTPClient()
            apa.fetch(req)

application = tornado.web.Application([
    (r"/.well-known/host-meta", XrdHandler),
    (r"/.well-known/webfinger", FingerHandler),
    (r"/salmon/(.+)", SalmonHandler),
    (r"/user/(.+)", UserHandler),
    (r"/hub", PushHandler),
    ],debug=True,**settings)
srv = tornado.httpserver.HTTPServer(application, )

def setup_db(path):
    gen_log = logging.getLogger("tornado.general")
    gen_log.warn("No db found, creating in {}".format(path))
    con = sqlite3.connect(path)
    con.execute("""create table author (id integer primary key,
                                       uri varchar,
                                       name varchar,
                                       email varchar,
                                       salmon_pubkey varchar, -- base64_urlencoded public modulus +.+ base64_urlencoded public exponent
                                       salmon_privkey varchar  -- base64_urlencoded private exponent
                                       );""")
    con.execute(""" create table entry (id integer primary key, 
                                        author INTEGER, 
                                        text varchar, -- xml atom <entry>
                                        verb varchar,
                                        ts timestamp default current_timestamp,
                                        FOREIGN KEY(author) REFERENCES author(id));""")
    con.execute("""
                    create table subscriptions (id integer primary key,
                                        author integer,
                                        expires datetime,
                                        callback varchar,
                                        secret varchar,
                                        verified bool,
                                        FOREIGN KEY(author) REFERENCES author(id));""")
    con.commit()


options.define("config_file", default="/etc/friends/friends.conf", type=str)
options.define("webroot", default="/srv/friends/", type=str)

if __name__ == "__main__":
    dbPath = 'friends.db'
#    options.log_file_prefix="/tmp/friends"
    tornado.options.parse_config_file(options.config_file)
    tornado.options.parse_command_line()
    gen_log = logging.getLogger("tornado.general")
    gen_log.info("Reading config from: %s", options.config_file,)
    if not os.path.exists(dbPath):
        setup_db(dbPath)
    db = sqlite3.connect(dbPath, detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
    db.row_factory = sqlite3.Row
    srv.listen(80)
    tornado.ioloop.IOLoop.instance().start()

