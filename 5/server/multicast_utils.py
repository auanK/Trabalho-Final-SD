import socket
import logging
import struct

MULTICAST_GROUP = '224.1.1.1' 
MULTICAST_PORT = 5007      

multicast_send_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)

ttl = struct.pack('b', 1) 
multicast_send_socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)

def send_multicast_message(message: str):
    try:
        logging.debug(f" - Enviando msg multicast: '{message}' to {MULTICAST_GROUP}:{MULTICAST_PORT} \n ")
        multicast_send_socket.sendto(message.encode('utf-8'), (MULTICAST_GROUP, MULTICAST_PORT))
    except Exception as e:
        logging.error(f"Falha ao enviar mensagem multicast {e}")
