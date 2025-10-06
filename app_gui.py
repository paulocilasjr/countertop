# app_gui.py
from threading import Thread
from time import sleep
from werkzeug.serving import make_server
import webview

from app import app  # imports your Flask app object

HOST, PORT = "127.0.0.1", 5000

class ServerThread(Thread):
    def __init__(self, wsgi_app, host, port):
        super().__init__(daemon=True)
        self._server = make_server(host, port, wsgi_app)

    def run(self):
        self._server.serve_forever()

    def stop(self):
        self._server.shutdown()

server = ServerThread(app, HOST, PORT)
server.start()
sleep(0.5)  # small buffer to start the server

win = webview.create_window("Despesas", f"http://{HOST}:{PORT}", width=1100, height=800)
win.events.closed += lambda: server.stop()  # stop Flask when window closes
webview.start()
