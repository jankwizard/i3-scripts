#!/usr/bin/env python3
##################
# Simple server that allows firefox to request fake "fullscreen"
# Visually it's fullscreen, but _net_wm_state is not changed
# This is intended to be used with:
#   Firefox:full-screen-api.ignore-widgets = true
# to disable normal fullscreen, and fake fullscreen enabled via a client/hook
# in firefox pages (firefox_fakefullscreen_client.js)
##################
# Issues:
# - for "fullscreen" window in stacked/tabbed container, changing focus to
#   sibling windows causes "fullscreen" to end
# - "fullscreen" ending in one firefox window will also end fullscreen in all
#   other windows

import os
import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler

os.chdir(os.path.dirname(os.path.realpath(__file__)))

class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        print(f"do_GET - {self.path}")
        self.send_response(200)
        self.end_headers()
        if self.path == "/maxoff":
            subprocess.check_output("python3 fakefullscreen.py --maxoff", shell=True)
        elif self.path == "/maxon":
            subprocess.check_output("python3 fakefullscreen.py --maxon", shell=True)


httpd = HTTPServer(('localhost', 8000), SimpleHTTPRequestHandler)
httpd.serve_forever()

