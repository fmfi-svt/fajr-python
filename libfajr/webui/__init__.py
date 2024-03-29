import itertools
from libfajr.markup import parse_html, select_html
import re
from libfajr.markup import ElementBuilder
import lxml.etree as etree


class WebUIEvent(object):
    def __init__(self, class_name, dialog=None, component=None, **fields):
        self.class_name = class_name
        self.fields = fields
        self.dialog = dialog
        self.component = component

    def to_xml(self):
        E = ElementBuilder
        return (E('ev')(
            E('dlgName')(self.dialog.name) if self.dialog is not None else None,
            E('compName')(self.component.name) if self.component is not None else None,
            (E('event', {'class': self.class_name})
                (*[E(name)(value) for name, value in self.fields.iteritems()]))
        )).create_element()


class WebUIProperties(object):
    def __init__(self, name, initial=None):
        self.name = name
        self._current = {}
        self._changed = {}
        if initial:
            self._current.update(initial)
            self._changed.update(initial)

    def __len__(self):
        return len(self._current)

    def __getitem__(self, item):
        return self._current[item]

    def __setitem__(self, item, value):
        self._current[item] = value
        self._changed[item] = value

    def __contains__(self, item):
        return item in self._current

    def __iter__(self):
        return iter(self._current)

    def get(self, item, default=None):
        return self._current.get(item, default)

    def flush_changes(self):
        changed = self._changed
        self._changed = {}
        return changed


class WebUIComponent(object):
    def __init__(self, parent, name, type):
        self.parent = parent
        self.name = name
        self.type = type

    def fire_event(self, event):
        self.parent.fire_event(event)

    def __str__(self):
        return unicode(self).encode('UTF-8')

    def __unicode__(self):
        return u'component {} {}'.format(self.type, self.name)

    @classmethod
    def from_element(cls, parent, element):
        return cls(parent, element.attrib['id'], element.attrib['jsct'])


class WebUIContainer(WebUIComponent):
    def __init__(self, *args, **kwargs):
        super(WebUIContainer, self).__init__(*args, **kwargs)
        self.components = []
        self.components_by_name = {}

    def build_components(self, root_element):
        def walk(element):
            for child in element:
                if 'jsct' in child.attrib:
                    type = component_types.get(child.attrib['jsct'], WebUIContainer)
                    component = type.from_element(self, child)
                    if hasattr(component, 'components'):
                        for child_component in component.components:
                            self.components_by_name[child_component.name] = child_component
                    self.components_by_name[component.name] = component
                    self.components.append(component)
                else:
                    walk(child)
        walk(root_element)

    def __unicode__(self):
        return u'container {} {}'.format(self.type, self.name)

    @classmethod
    def from_element(cls, parent, element):
        component = super(WebUIContainer, cls).from_element(parent, element)
        component.build_components(element)
        return component


class WebUILabel(WebUIComponent):
    def __init__(self, *args, **kwargs):
        super(WebUILabel, self).__init__(*args, **kwargs)
        self.value = u''
        self.name_for = ''

    def __unicode__(self):
        ret = u'{} \'{}\''.format(super(WebUILabel, self).__unicode__(), self.value)
        if self.name_for:
            ret += u' for={}'.format(self.name_for)
        return ret

    @classmethod
    def from_element(cls, parent, element):
        component = super(WebUILabel, cls).from_element(parent, element)
        component.value = element.text or u''
        component.name_for = element.attrib.get('for')
        return component


class WebUITextField(WebUIComponent):
    def __init__(self, *args, **kwargs):
        super(WebUITextField, self).__init__(*args, **kwargs)
        self.value = u''
        self.readonly = False

    def __unicode__(self):
        ret = u'{} \'{}\'{}'.format(super(WebUITextField, self).__unicode__(), self.value, u' readonly' if self.readonly else u'')
        return ret

    @classmethod
    def from_element(cls, parent, element):
        component = super(WebUITextField, cls).from_element(parent, element)
        component.value = element.attrib.get('value', u'')
        component.readonly = (element.attrib.get('_readonly') == 'true')
        return component

component_types = {
    'popupMenu': WebUIContainer,
    'panel': WebUIContainer,
    'tabbedPane': WebUIContainer,

    'menuItem': WebUIComponent,
    'button': WebUIComponent,
    'table': WebUIComponent,
    'separator': WebUIComponent,
    'textField': WebUITextField,
    'action': WebUIComponent,
    'valueInteractive': WebUIComponent,
    'label': WebUILabel
}


class WebUIMainDialog(WebUIContainer):
    def __init__(self, app, name, title):
        super(WebUIMainDialog, self).__init__(app, name, 'body')
        self.app = app
        self.title = title

    def open(self):
        response = self.app.session.http.get(self.app.session.url.webui({'appId': self.app.id, 'form': self.name}))
        html = parse_html(response.text)
        body = select_html(html, '[jsct=body]')[0]
        self.build_components(body)

    def fire_event(self, event):
        event.dialog = self
        self.app.fire_event(event)

    def __repr__(self):
        return '<%s %r in application %r>' % (self.__class__.__name__, self.name, self.app.id)


class WebUIApplication(object):
    def __init__(self, session, app_id):
        self.session = session
        self.id = app_id
        self._events = []
        self.fire_event(WebUIEvent('avc.ui.event.AVCComponentEvent', command='INIT'))
        self._serial = itertools.count()
        self.forms = {}
        self.closed = False
        self.properties = WebUIProperties('app')
        self._active_dialog = None

    def fire_event(self, event):
        self._events.append(event)

    @property
    def active_dialog(self):
        return self._active_dialog

    @active_dialog.setter
    def active_dialog(self, dialog):
        self._active_dialog = dialog
        self.properties['activeDlgName'] = dialog.name

    def execute(self):
        url = self.session.url.webui({'appId': self.id})
        E = ElementBuilder
        request = E('request')(
            E('serial')(str(next(self._serial))),
            E('events')(*[event.to_xml() for event in self._events])
        ).create_element()
        xml_spec = etree.tostring(request)
        params = {
            'appId': self.id,
            'xml_spec': xml_spec
        }
        response = self.session.http.post(url, params)
        html = parse_html(response.text)
        script = select_html(html, 'script')[0].text
        if re.search(r'webui\(\).serverCloseApplication\(\);', script):
            self.closed = True
        error = re.search(r'webui\(\).messageBox\("([^"]+)","Chyba","",""\);', script)
        if error:
            raise Exception(error.group(1).encode('UTF-8'))
        for form_match in re.finditer(r'dm\(\).openMainDialog\("([^"]+)","([^"]+)","([^"]+)",(?:-?\d+,){6}'
                                      r'(?:true|false),(?:true|false),(?:true|false),(?:true|false)\);',
                                      script):
            form = WebUIMainDialog(self, form_match.group(1), form_match.group(2))
            self.forms[form.name] = form
            if self.active_dialog is None:
                self.active_dialog = form

    def close(self):
        self.fire_event(WebUIEvent('avc.framework.webui.WebUIKillEvent', command='CLOSE'))

    @classmethod
    def open(cls, session, class_name, **kwargs):
        params = {'appClassName': class_name,
                  'fajr': 'A'}
        params.update(**kwargs)
        init_url = session.url.webui(params)
        response = session.http.get(init_url)
        html = parse_html(response.text)
        body = select_html(html, 'body')[0]
        match = re.match(r'window\.setTimeout\("WebUI_init\(\\\"([0-9]+)\\\", \\\"ais\\\", \\\"ais/webui2\\\"\)", 1\)', body.attrib['onload'])
        if not match:
            raise ValueError('Neviem najst appId v odpovedi vo faze inicializacie aplikacie %s!' % class_name)
        app_id = int(match.group(1))
        app = cls(session, app_id)
        app.execute()
        return app