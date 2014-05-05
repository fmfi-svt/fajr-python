#!/usr/bin/env python
from libfajr.session import WebUISession, CosignCookieLogin, create_cosign_cookie
from argparse import ArgumentParser

parser = ArgumentParser()
parser.add_argument('host')
parser.add_argument('cookie')

args = parser.parse_args()

ais = WebUISession(args.host, CosignCookieLogin(create_cosign_cookie('cosign-filter-%s' % args.host, args.cookie, args.host)))
ais.login()
print ais.version
app = ais.open_application('ais.gui.vs.es.VSES017App', kodAplikacie='VSES017')
print app.active_dialog
app.active_dialog.open()

def print_components(container, indent=0):
    for component in container.components:
        is_container = hasattr(component, 'components')
        print '  ' * indent + str(component)
        if is_container:
            if component.components:
                print_components(component, indent=indent + 1)
            else:
                print '  ' * (indent + 1) + '<no children>'

print_components(app.active_dialog)

app.close()