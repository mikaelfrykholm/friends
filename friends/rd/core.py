import datetime
import logging

RFC6415_TYPE = 'application/xrd+xml'
RFC7033_TYPE = 'application/jrd+json'

JRD_TYPES = ('application/jrd+json', 'application/xrd+json', 'application/json', 'text/json')
XRD_TYPES = ('application/xrd+xml', 'text/xml')

KNOWN_RELS = {
    'activity_streams': 'http://activitystrea.ms/spec/1.0',
    'app': ('http://apinamespace.org/atom', 'application/atomsvc+xml'),
    'avatar': 'http://webfinger.net/rel/avatar',
    'foaf': ('describedby', 'application/rdf+xml'),
    'hcard': 'http://microformats.org/profile/hcard',
    'oauth_access_token':   'http://apinamespace.org/oauth/access_token',
    'oauth_authorize':      'http://apinamespace.org/oauth/authorize',
    'oauth_request_token':  'http://apinamespace.org/oauth/request_token',
    'openid': 'http://specs.openid.net/auth/2.0/provider',
    'opensocial': 'http://ns.opensocial.org/2008/opensocial/activitystreams',
    'portable_contacts': 'http://portablecontacts.net/spec/1.0',
    'profile': 'http://webfinger.net/rel/profile-page',
    'updates_from': 'http://schemas.google.com/g/2010#updates-from',
    'ostatus_sub': 'http://ostatus.org/schema/1.0/subscribe',
    'salmon_endpoint': 'salmon',
    'salmon_key': 'magic-public-key',
    'webfist': 'http://webfist.org/spec/rel',
    'xfn': 'http://gmpg.org/xfn/11',

    'jrd':  ('lrdd', 'application/json'),
    'webfinger': ('lrdd', 'application/jrd+json'),
    'xrd': ('lrdd', 'application/xrd+xml'),
}

logger = logging.getLogger("rd")


def _is_str(s):
    try:
        return isinstance(s, str)
    except NameError:
        return isinstance(s, str)


def loads(content, content_type):

    from rd import jrd, xrd

    content_type = content_type.split(";")[0]

    if content_type in JRD_TYPES:
        logger.debug("loads() loading JRD")
        return jrd.loads(content)

    elif content_type in XRD_TYPES:
        logger.debug("loads() loading XRD")
        return xrd.loads(content)

    raise TypeError('Unknown content type')

#
# helper functions for host parsing and discovery
#

def parse_uri_components(resource, default_scheme='https'):
    hostname = None
    scheme = default_scheme

    from urllib.parse import urlparse

    parts = urlparse(resource)
    if parts.scheme and parts.netloc:
        scheme = parts.scheme
        ''' FIXME: if we have https://user@some.example/ we end up with parts.netloc='user@some.example' here. '''
        hostname = parts.netloc
        path = parts.path

    elif parts.scheme == 'acct' or (not parts.scheme and '@' in parts.path):
        ''' acct: means we expect WebFinger to work, and RFC7033 requires https, so host-meta should support it too. '''
        scheme = 'https'

        ''' We should just have user@site.example here, but if it instead
            is user@site.example/whatever/else we have to split it later
            on the first slash character, '/'.
        '''
        hostname = parts.path.split('@')[-1]
        path = None

        ''' In case we have hostname=='site.example/whatever/else' we do the split
            on the first slash, giving us 'site.example' and 'whatever/else'.
        '''
        if '/' in hostname:
            (hostname, path) = hostname.split('/', maxsplit=1)
            ''' Normalize path so it always starts with /, which is the behaviour of urlparse too. '''
            path = '/' + path

    else:
        if not parts.path:
            raise ValueError('No hostname could be deduced from arguments.')

        elif '/' in parts.path:
            (hostname, path) = parts.path.split('/', maxsplit=1)
            ''' Normalize path so it always starts with /, which is the behaviour of urlparse too. '''
            path = '/' + path
        else:
            hostname = parts.path
            path = None

    return (scheme, hostname, path)

#
# special XRD types
#

class Attribute(object):

    def __init__(self, name, value):
        self.name = name
        self.value = value

    def __cmp__(self, other):
        return cmp(str(self), str(other))

    def __eq__(self, other):
        return str(self) == other

    def __str__(self):
        return "%s=%s" % (self.name, self.value)


class Element(object):

    def __init__(self, name, value, attrs=None):
        self.name = name
        self.value = value
        self.attrs = attrs or {}


class Title(object):

    def __init__(self, value, lang=None):
        self.value = value
        self.lang = lang

    def __cmp__(self, other):
        return cmp(str(self), str(other))

    def __eq__(self, other):
        return str(self) == str(other)

    def __str__(self):
        if self.lang:
            return "%s:%s" % (self.lang, self.value)
        return self.value


class Property(object):

    def __init__(self, type_, value=None):
        self.type = type_
        self.value = value

    def __cmp__(self, other):
        return cmp(str(self), str(other))

    def __eq__(self, other):
        return str(self) == other

    def __str__(self):
        if self.value:
            return "%s:%s" % (self.type, self.value)
        return self.type


#
# special list types
#

class ListLikeObject(list):

    def __setitem__(self, key, value):
        value = self.item(value)
        super(ListLikeObject, self).__setitem__(key, value)

    def append(self, value):
        value = self.item(value)
        super(ListLikeObject, self).append(value)

    def extend(self, values):
        values = (self.item(value) for value in values)
        super(ListLikeObject, self).extend(values)


class AttributeList(ListLikeObject):

    def __call__(self, name):
        for attr in self:
            if attr.name == name:
                yield attr

    def item(self, value):
        if isinstance(value, (list, tuple)):
            return Attribute(*value)
        elif not isinstance(value, Attribute):
            raise ValueError('value must be an instance of Attribute')
        return value


class ElementList(ListLikeObject):

    def item(self, value):
        if not isinstance(value, Element):
            raise ValueError('value must be an instance of Type')
        return value


class TitleList(ListLikeObject):

    def item(self, value):
        if _is_str(value):
            return Title(value)
        elif isinstance(value, (list, tuple)):
            return Title(*value)
        elif not isinstance(value, Title):
            raise ValueError('value must be an instance of Title')
        return value


class LinkList(ListLikeObject):

    def __call__(self, rel):
        for link in self:
            if link.rel == rel:
                yield link

    def item(self, value):
        if not isinstance(value, Link):
            raise ValueError('value must be an instance of Link')
        return value


class PropertyList(ListLikeObject):

    def __call__(self, type_):
        for prop in self:
            if prop.type == type_:
                yield prop

    def item(self, value):
        if _is_str(value):
            return Property(value)
        elif isinstance(value, (tuple, list)):
            return Property(*value)
        elif not isinstance(value, Property):
            raise ValueError('value must be an instance of Property')
        return value


#
# Link object
#

class Link(object):

    def __init__(self, rel=None, type=None, href=None, template=None):
        self.rel = rel
        self.type = type
        self.href = href
        self.template = template
        self._titles = TitleList()
        self._properties = PropertyList()

    def get_titles(self):
        return self._titles
    titles = property(get_titles)

    def get_properties(self):
        return self._properties
    properties = property(get_properties)

    def apply_template(self, uri):

        from urllib.parse import quote

        if not self.template:
            raise TypeError('This is not a template Link')
        return self.template.replace('{uri}', quote(uri, safe=''))

    def __str__(self):

        from cgi import escape

        attrs = ''
        for prop in ['rel', 'type', 'href', 'template']:
            val = getattr(self, prop)
            if val:
                attrs += ' {!s}="{!s}"'.format(escape(prop), escape(val))

        return '<Link{!s}/>'.format(attrs)


#
# main RD class
#

class RD(object):

    def __init__(self, xml_id=None, subject=None):

        self.xml_id = xml_id
        self.subject = subject
        self._expires = None
        self._aliases = []
        self._properties = PropertyList()
        self._links = LinkList()
        self._signatures = []

        self._attributes = AttributeList()
        self._elements = ElementList()

    # ser/deser methods

    def to_json(self):
        from rd import jrd
        return jrd.dumps(self)

    def to_xml(self):
        from rd import xrd
        return xrd.dumps(self)

    # helper methods

    def find_link(self, rels, attr=None, mimetype=None):
        if not isinstance(rels, (list, tuple)):
            rels = (rels,)
        for link in self.links:
            if link.rel in rels:
                if mimetype and link.type != mimetype:
                    continue
                if attr:
                    return getattr(link, attr, None)
                return link

    def __getattr__(self, name, attr=None):
        if name in KNOWN_RELS:
            try:
                ''' If we have a specific mimetype for this rel value '''
                rel, mimetype = KNOWN_RELS[name]
            except ValueError:
                rel = KNOWN_RELS[name]
                mimetype = None 
            return self.find_link(rel, attr=attr, mimetype=mimetype)
        raise AttributeError(name)

    # custom elements and attributes

    def get_elements(self):
        return self._elements
    elements = property(get_elements)

    @property
    def attributes(self):
        return self._attributes

    # defined elements and attributes

    def get_expires(self):
        return self._expires

    def set_expires(self, expires):
        if not isinstance(expires, datetime.datetime):
            raise ValueError('expires must be a datetime object')
        self._expires = expires
    expires = property(get_expires, set_expires)

    def get_aliases(self):
        return self._aliases
    aliases = property(get_aliases)

    def get_properties(self):
        return self._properties
    properties = property(get_properties)

    def get_links(self):
        return self._links
    links = property(get_links)

    def get_signatures(self):
        return self._signatures
    signatures = property(get_links)
