# coding=utf-8
import urllib
from libfajr.markup import parse_html, select_html
from libfajr.webui import WebUIApplication
import re
import requests
from requests.cookies import create_cookie


def create_cosign_cookie(name, value, domain):
    if not re.match(r'^cosign-[a-zA-Z0-9._-]+$', name):
        raise ValueError('cookie name %r does not match pattern' % name)

    value_match = re.match(r'^([A-Za-z0-9 +.@-]+)(/\d+)$', value)
    if not value_match:
        raise ValueError('cookie value %r does not match pattern' % value)
    value = value_match.group(1).replace(' ', '+')

    if not re.match(r'^[a-zA-Z0-9._-]+$', domain):
        raise ValueError('cookie domain %r does not match pattern' % domain)

    return create_cookie(name, value, domain=domain)


class CosignLogin(object):
    def __init__(self, login_url='https://login.uniba.sk/cosign.cgi', logout_url='https://login.uniba.sk/logout.cgi'):
        self._login_url = login_url
        self._logout_url = logout_url

    def logout(self, session):
        resp = session.http.post(self.logout_url, {'verify': u'Odhlásiť', 'url': session.url.main()})
        if not resp.url == session.url.start():
            raise Exception('Landed at unexpected page: %s' % resp.url)


class CosignCookieLogin(CosignLogin):
    def __init__(self, cookie, **kwargs):
        super(CosignCookieLogin, self).__init__(**kwargs)
        self._cookie = cookie

    def login(self, session):
        session.http.cookies.set_cookie(self._cookie)
        session.http.get(session.url.login())


class URLMap(object):
    def __init__(self, hostname, protocol='https'):
        self.hostname = hostname
        self.protocol = protocol
        self._urls = {
            'webui': 'ais/servlets/WebUIServlet',
            'files': 'ais/files/',
            'login': 'ais/login.do',
            'logout': 'ais/logout.do',
            'start': 'ais/start.do',
            'change_module': 'ais/portal/changeModul.do',
            'main': ''
        }

    def __getattr__(self, item):
        path = self._urls[item]

        def add_qs(params=None):
            url = '%s://%s/%s' % (self.protocol, self.hostname, path)
            if params:
                url = url + '?' + urllib.urlencode(params)
            return url

        return add_qs


class WebUISession(object):
    def __init__(self, hostname, login_type, protocol='https'):
        self.http = requests.Session()
        self.url = URLMap(hostname, protocol=protocol)
        self._login_type = login_type
        self._version = None
        self._applications = None

    def login(self):
        self._login_type.login(self)

    def logout(self):
        self._login_type.logout(self)

    def _load_version(self):
        response = self.http.get(self.url.start())
        html = parse_html(response.text)
        version = select_html(html, '.verzia')[0].text
        match = re.match(r'AiS2 verzia (2)\.([0-9]+)\.([0-9]+)\.([0-9]+)', version)
        if not match:
            raise ValueError('Invalid AIS version string: %r' % version)
        self._version = tuple(int(match.group(idx)) for idx in range(1, 5))

    @property
    def version(self):
        if self._version is None:
            self._load_version()
        return self._version

    def _load_applications(self):
        raise NotImplementedError()

    @property
    def applications(self):
        if self._applications is None:
            self._load_applications()
        return self._applications

    def open_application(self, app_class_name, **kwargs):
        return WebUIApplication.open(self, app_class_name, **kwargs)
