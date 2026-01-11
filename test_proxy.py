import socket
import threading
import time
import subprocess
import sys


class EchoServer:
    """Simple echo server for testing"""

    def __init__(self, host='127.0.0.1', port=9999):
        self.host = host
        self.port = port
        self.server_socket = None
        self.thread = None

    def start(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)

        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        time.sleep(0.1)  # Let server start

    def _run(self):
        while True:
            try:
                client, addr = self.server_socket.accept()
                data = client.recv(1024)
                if data:
                    client.sendall(data)
                client.close()
            except Exception:
                break

    def stop(self):
        if self.server_socket:
            self.server_socket.close()


def test_tcp_proxy():
    """Test that the TCP proxy forwards data correctly"""
    # Start echo server
    echo_server = EchoServer()
    echo_server.start()

    # Start proxy (listen on 8888, forward to 9999)
    proxy_process = subprocess.Popen([
        sys.executable, 'cli.py',
        '--listen-port', '8888',
        '--target-address', '127.0.0.1',
        '--target-port', '9999'
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    time.sleep(0.5)  # Let proxy start

    # Check if proxy started successfully
    if proxy_process.poll() is not None:
        stdout, stderr = proxy_process.communicate()
        print("Proxy stdout:", stdout.decode())
        print("Proxy stderr:", stderr.decode())
        raise Exception("Proxy process exited early")

    try:
        # Test proxy
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect(('127.0.0.1', 8888))
        test_message = b'Hello from proxy test!'
        client.sendall(test_message)
        response = client.recv(1024)
        client.close()

        assert response == test_message, f"Expected {test_message}, got {response}"

    finally:
        # Clean up
        proxy_process.terminate()
        proxy_process.wait()
        echo_server.stop()