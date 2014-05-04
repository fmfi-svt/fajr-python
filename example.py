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
app.close()