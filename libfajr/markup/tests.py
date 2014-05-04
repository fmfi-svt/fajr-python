from libfajr.markup import ElementBuilder as E, etree
from nose.tools import eq_, raises


def test_element_builder():
    el = E('tag', attribute=u'value')(
        u'he', u'ad', E('other'), u'ta', None, u'il', E('ya')()
    ).create_element()
    eq_(etree.tostring(el, encoding='utf8'),
        '<tag attribute="value">head<other/>tail<ya/></tag>')

def test_append_none():
    el = E('tag').append(None).create_element()
    eq_(etree.tostring(el, encoding='utf8'),
        '<tag/>')

def test_append_unicode_text():
    el = E('tag').append(u'Test').create_element()
    eq_(etree.tostring(el, encoding='utf8'),
        '<tag>Test</tag>')

def test_append_unicode_tail():
    el = E('tag').append(E('inner'), u'Test').create_element()
    eq_(etree.tostring(el, encoding='utf8'),
        '<tag><inner/>Test</tag>')

def test_append_element():
    el = E('tag').append(etree.Element('inner')).create_element()
    eq_(etree.tostring(el, encoding='utf8'),
        '<tag><inner/></tag>')

def test_append_str():
    el = E('tag').append('plain str').create_element()
    eq_(etree.tostring(el, encoding='utf8'),
        '<tag>plain str</tag>')