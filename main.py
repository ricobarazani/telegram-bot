
import threading
import time
import socket

def fake_port():
    s = socket.socket()
    s.bind(("0.0.0.0", 10000))
    s.listen(1)
    while True:
        time.sleep(10)

threading.Thread(target=fake_port, daemon=True).start()

