import os

RELAY_SERVER_IP = os.environ.get('RELAY_IP', '127.0.0.1')
RELAY_SERVER_PORT = int(os.environ.get('RELAY_PORT', 9000))