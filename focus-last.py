#!/usr/bin/env python3

import os
import socket
import selectors
import tempfile
import threading
from argparse import ArgumentParser
import i3ipc

SOCKET_DIR = '{}/i3_focus_last.{}{}'.format(tempfile.gettempdir(), os.geteuid(),
                                            os.getenv("DISPLAY"))
SOCKET_FILE = '{}/socket'.format(SOCKET_DIR)
MAX_WIN_HISTORY = 15


class FocusWatcher:
    def __init__(self):
        self.i3 = i3ipc.Connection()
        self.i3.on('window::focus', self.on_window_focus)
        self.i3.on('workspace::focus', self.on_workspace_focus)
        # Make a directory with permissions that restrict access to
        # the user only.
        os.makedirs(SOCKET_DIR, mode=0o700, exist_ok=True)
        self.listening_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        if os.path.exists(SOCKET_FILE):
            os.remove(SOCKET_FILE)
        self.listening_socket.bind(SOCKET_FILE)
        self.listening_socket.listen(1)
        tree = self.i3.get_tree()
        focused = tree.find_focused()
        self.workspace = focused.workspace().name
        self.window = focused
        self.prev_workspace = self.workspace
        self.prev_window = self.window
        print(f"Init - ws:{self.workspace}, con:{self.window.id}")

    def swap2prev(self):
        if self.prev_window != None:
            self.i3.command('[con_id=%s] focus' % self.prev_window.id)

    def on_workspace_focus(self, i3conn, event):
        # remember prev window+workspace
        self.prev_window    = self.window
        self.prev_workspace = self.workspace
        # track new window+workspace
        self.workspace = event.current.name
        self.window = event.current.find_focused()
        print(f"\nnew workspace: {self.workspace}")
        if self.prev_window == None:
            print(f"( prev ws:{self.prev_workspace}, con:None")
        else:
            print(f"( prev ws:{self.prev_workspace}, con:{self.prev_window.id}")

    def on_window_focus(self, i3conn, event):
        # update current focused window
        print(f"\tcon: class:{event.container.window_class}, id:{event.container.id}")
        self.window = event.container

    def launch_i3(self):
        self.i3.main()

    def launch_server(self):
        selector = selectors.DefaultSelector()

        def accept(sock):
            conn, addr = sock.accept()
            selector.register(conn, selectors.EVENT_READ, read)

        def read(conn):
            data = conn.recv(1024)
            if data == b'switch':
                self.swap2prev()
            elif data:
                if self.workspace.startswith(data.decode()):
                    self.swap2prev()
                else:
                    self.i3.command('workspace number ' + data.decode())
            elif not data:
                selector.unregister(conn)
                conn.close()

        selector.register(self.listening_socket, selectors.EVENT_READ, accept)

        while True:
            for key, event in selector.select():
                callback = key.data
                callback(key.fileobj)

    def run(self):
        t_i3 = threading.Thread(target=self.launch_i3)
        t_server = threading.Thread(target=self.launch_server)
        for t in (t_i3, t_server):
            t.start()


if __name__ == '__main__':
    parser = ArgumentParser(prog='focus-last.py',
                            description='''
        Focus last focused window.

        This script should be launch from the .xsessionrc without argument.

        Then you can bind this script with the `--switch` option to one of your
        i3 keybinding.
        ''')
    parser.add_argument('--switch',
                        dest='switch',
                        action='store_true',
                        help='Switch to the previous window',
                        default=False)
    parser.add_argument('--window',
                        nargs=1,
                        dest='window',
                        help='Switch to window or the previous',
                        default=False)
    args = parser.parse_args()

    if args.switch:
        client_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        client_socket.connect(SOCKET_FILE)
        client_socket.send(b'switch')
        client_socket.close()
    elif args.window:
        client_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        client_socket.connect(SOCKET_FILE)
        client_socket.send(args.window[0].encode())
        client_socket.close()
    else:
        focus_watcher = FocusWatcher()
        focus_watcher.run()
