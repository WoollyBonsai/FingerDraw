import socket
from zeroconf import ServiceInfo, Zeroconf
import time

def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

ip = get_ip()
print(f"IP: {ip}")
info = ServiceInfo(
    "_http._tcp.local.",
    "Notebook Vault._http._tcp.local.",
    addresses=[socket.inet_aton(ip)],
    port=8000,
    server="vault.local.",
)
zc = Zeroconf()
zc.register_service(info)
print("Registered. Press Ctrl+C to exit...")
time.sleep(5)
zc.unregister_service(info)
zc.close()
