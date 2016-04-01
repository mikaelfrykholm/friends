
from xml.dom.minidom import getDOMImplementation, parseString, Node

from rd.core import RD, Element, Link, Property, Title

XRD_NAMESPACE = "http://docs.oasis-open.org/ns/xri/xrd-1.0"


def _get_text(root):
    text = ''
    for node in root.childNodes:
        if node.nodeType == Node.TEXT_NODE and node.nodeValue:
            text += node.nodeValue
        else:
            text += _get_text(node)
    return text.strip() or None


def loads(content):

    import isodate

    def expires_handler(node, obj):
        obj.expires = isodate.parse_datetime(_get_text(node))

    def subject_handler(node, obj):
        obj.subject = _get_text(node)

    def alias_handler(node, obj):
        obj.aliases.append(_get_text(node))

    def property_handler(node, obj):
        obj.properties.append(Property(node.getAttribute('type'), _get_text(node)))

    def title_handler(node, obj):
        obj.titles.append(Title(_get_text(node), node.getAttribute('xml:lang')))

    def link_handler(node, obj):
        l = Link()
        l.rel = node.getAttribute('rel')
        l.type = node.getAttribute('type')
        l.href = node.getAttribute('href')
        l.template = node.getAttribute('template')
        obj.links.append(l)

    handlers = {
        'Expires': expires_handler,
        'Subject': subject_handler,
        'Alias': alias_handler,
        'Property': property_handler,
        'Link': link_handler,
        'Title': title_handler,
    }

    def unknown_handler(node, obj):
        obj.elements.append(Element(
            name=node.tagName,
            value=_get_text(node),
        ))

    def handle_node(node, obj):
        handler = handlers.get(node.nodeName, unknown_handler)
        if handler and node.nodeType == node.ELEMENT_NODE:
            handler(node, obj)

    doc = parseString(content)
    root = doc.documentElement

    rd = RD(root.getAttribute('xml:id'))

    for name, value in list(root.attributes.items()):
        if name != 'xml:id':
            rd.attributes.append((name, value))

    for node in root.childNodes:
        handle_node(node, rd)
        if node.nodeName == 'Link':
            link = rd.links[-1]
            for child in node.childNodes:
                handle_node(child, link)

    return rd


def dumps(xrd):

    doc = getDOMImplementation().createDocument(XRD_NAMESPACE, "XRD", None)
    root = doc.documentElement
    root.setAttribute('xmlns', XRD_NAMESPACE)

    if xrd.xml_id:
        root.setAttribute('xml:id', xrd.xml_id)

    for attr in xrd.attributes:
        root.setAttribute(attr.name, attr.value)

    if xrd.expires:
        node = doc.createElement('Expires')
        node.appendChild(doc.createTextNode(xrd.expires.isoformat()))
        root.appendChild(node)

    if xrd.subject:
        node = doc.createElement('Subject')
        node.appendChild(doc.createTextNode(xrd.subject))
        root.appendChild(node)

    for alias in xrd.aliases:
        node = doc.createElement('Alias')
        node.appendChild(doc.createTextNode(alias))
        root.appendChild(node)

    for prop in xrd.properties:
        node = doc.createElement('Property')
        node.setAttribute('type', prop.type)
        if prop.value:
            node.appendChild(doc.createTextNode(str(prop.value)))
        else:
            node.setAttribute('xsi:nil', 'true')
        root.appendChild(node)

    for element in xrd.elements:
        node = doc.createElement(element.name)
        node.appendChild(doc.createTextNode(element.value))
        root.appendChild(node)

    for link in xrd.links:

        if link.href and link.template:
            raise ValueError('only one of href or template attributes may be specified')

        link_node = doc.createElement('Link')

        if link.rel:
            link_node.setAttribute('rel', link.rel)

        if link.type:
            link_node.setAttribute('type', link.type)

        if link.href:
            link_node.setAttribute('href', link.href)

        if link.template:
            link_node.setAttribute('template', link.template)

        for title in link.titles:
            node = doc.createElement('Title')
            node.appendChild(doc.createTextNode(str(title)))
            if title.lang:
                node.setAttribute('xml:lang', title.lang)
            link_node.appendChild(node)

        for prop in link.properties:
            node = doc.createElement('Property')
            node.setAttribute('type', prop.type)
            if prop.value:
                node.appendChild(doc.createTextNode(str(prop.value)))
            else:
                node.setAttribute('xsi:nil', 'true')
            link_node.appendChild(node)

        root.appendChild(link_node)

    return doc
