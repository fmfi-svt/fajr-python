import lxml.etree as etree
import html5lib
from cssselect import HTMLTranslator


class ElementBuilder(object):
    def __init__(self, tag, attributes=None, **attributes_kw):
        self._tag = tag
        self._attributes = {}
        if attributes:
            self._attributes.update(attributes)
        self._attributes.update(attributes_kw)
        self._content = []

    def create_element(self):
        el = etree.Element(self._tag, self._attributes)
        for index, item in enumerate(self._content):
            if isinstance(item, unicode):
                if len(el):
                    el[-1].tail = (el[-1].tail or u'') + item
                else:
                    el.text = (el.text or u'') + item
            elif etree.iselement(item):
                el.append(item)
            else:
                raise TypeError('Bad content item %r at index %s' % (item, index))
        return el

    def append(self, *content):
        for index, item in enumerate(content):
            if item is None:
                continue
            elif isinstance(item, str):
                self._content.append(item.decode('UTF-8'))
            elif isinstance(item, unicode):
                self._content.append(item)
            elif isinstance(item, ElementBuilder):
                self._content.append(item.create_element())
            elif etree.iselement(item):
                self._content.append(item)
            else:
                raise TypeError('Bad argument %r at index %s' % (item, index))
        return self

    def __call__(self, *content):
        return self.append(*content)


def parse_html(text, encoding=None):
    return html5lib.parse(text, encoding=encoding, treebuilder="lxml", namespaceHTMLElements=False)

def select_html(tree, selector):
    return tree.xpath(HTMLTranslator().css_to_xpath(selector))