import socket

UDP_IP = "10.147.133.121"
UDP_PORT = "5005"

def send(data, port=UDP_PORT, addr=UDP_IP):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 20)
    sock.sendto(data, (addr,port) )

def recieve(data, port=UDP_PORT, addr=UDP_IP, buf_size=1024):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    except AttributeError:
         pass # Some systems don't support SO_REUSEPORT

    sock.setsockopt(socket.SOL_IP,socket.IP_MULTICAST_TTL,20)
    sock.setsockopt(socket.SOL_IP,socket.IP_MULTICAST_LOOP,1)

    sock.bind(('',port))

    intf = socket.gethostbyname(socket.gethostname())
    sock.setsockopt(socket.SOL_IP, socket.IP_MULTICAST_IF, socket.inet_aton(intf))
    sock.setsockopt(socket.SOL_IP, socket.IP_ADD_MEMBERSHIP, socket.inet_aton(addr) + socket.inet_aton(intf))

    data,sender_addr=s.recvfrom(buf_size)
