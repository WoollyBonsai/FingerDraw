import os
import socket
import subprocess
from zeroconf import ServiceInfo, Zeroconf

CERTS_DIR = os.path.join(os.path.dirname(__file__), "certs")

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

def setup_tls():
    """Uses mkcert to generate SSL certificates for the local network."""
    os.makedirs(CERTS_DIR, exist_ok=True)
    ip = get_local_ip()
    cert_file = os.path.join(CERTS_DIR, "cert.pem")
    key_file = os.path.join(CERTS_DIR, "key.pem")
    
    # Check if certs exist, if not generate them
    if not os.path.exists(cert_file) or not os.path.exists(key_file):
        print(f"Generating SSL certificates for {ip} and vault.local...")
        try:
            # Install local CA
            subprocess.run(["mkcert", "-install"], check=True)
            # Generate the certs
            subprocess.run([
                "mkcert", 
                "-cert-file", cert_file, 
                "-key-file", key_file,
                "vault.local", ip, "localhost", "127.0.0.1"
            ], check=True)
        except Exception as e:
            print(f"Failed to generate mkcert certificates: {e}")
            return None, None
            
    return cert_file, key_file

def start_mdns(port=8000):
    """Starts the mDNS service to broadcast vault.local."""
    ip = get_local_ip()
    info = ServiceInfo(
        "_http._tcp.local.",
        "Notebook Vault._http._tcp.local.",
        addresses=[socket.inet_aton(ip)],
        port=port,
        server="vault.local.",
        properties={"description": "Notebook Local Server"}
    )
    zc = Zeroconf()
    zc.register_service(info)
    print(f"mDNS service started: vault.local is now pointing to {ip}:{port}")
    return zc, info
