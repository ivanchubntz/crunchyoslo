"""Local-only bridge between the desktop point of sale and the mobile reader."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hmac
import json
import queue
import secrets
import socket
import threading
from urllib.parse import parse_qs, urlparse


def _lan_addresses():
    addresses = []
    try:
        for item in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            address = item[4][0]
            if not address.startswith(("127.", "169.254.")) and address not in addresses:
                addresses.append(address)
    except OSError:
        pass
    private = []
    for address in addresses:
        first_octet, second_octet, *_ = (int(part) for part in address.split("."))
        if first_octet == 10 or first_octet == 192 and second_octet == 168 or first_octet == 172 and 16 <= second_octet <= 31:
            private.append(address)
    return private + [address for address in addresses if address not in private] or ["127.0.0.1"]


class ScanService:
    def __init__(self, scan_queue, product_lookup, port=8765):
        self.scan_queue = scan_queue
        self.product_lookup = product_lookup
        self.port = port
        self.token = secrets.token_urlsafe(24)
        self.addresses = _lan_addresses()
        self.server = None
        self.thread = None

    def start(self):
        service = self

        class Handler(BaseHTTPRequestHandler):
            def _json(self, status, payload):
                body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type")
                self.end_headers()
                self.wfile.write(body)

            def do_OPTIONS(self):
                self.send_response(204)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type")
                self.send_header("Access-Control-Max-Age", "600")
                self.end_headers()

            def do_GET(self):
                parsed = urlparse(self.path)
                if parsed.path == "/health":
                    self._json(200, {"status": "ready", "service": "oslo-reader"})
                elif parsed.path == "/api/session":
                    supplied = parse_qs(parsed.query).get("token", [""])[0]
                    valid = hmac.compare_digest(str(supplied), service.token)
                    self._json(200, {"valid": valid})
                else:
                    self._json(404, {"error": "not_found"})

            def do_POST(self):
                if urlparse(self.path).path != "/api/scan":
                    self._json(404, {"error": "not_found"})
                    return
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    if length <= 0 or length > 4096:
                        self._json(413, {"error": "invalid_payload_size"})
                        return
                    data = json.loads(self.rfile.read(length).decode("utf-8"))
                except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
                    self._json(400, {"error": "invalid_json"})
                    return
                if not isinstance(data, dict):
                    self._json(400, {"error": "invalid_payload"})
                    return

                supplied_token = str(data.get("token", ""))
                barcode = str(data.get("barcode", "")).strip()
                if not hmac.compare_digest(supplied_token, service.token):
                    self._json(403, {"error": "invalid_session"})
                    return
                if not barcode or len(barcode) > 128 or any(ord(char) < 32 for char in barcode):
                    self._json(400, {"error": "invalid_barcode"})
                    return

                try:
                    product = service.product_lookup(barcode)
                except Exception:
                    product = None
                service.scan_queue.put({"barcode": barcode})
                if product:
                    self._json(200, {
                        "found": True,
                        "barcode": barcode,
                        "product": product["nombre"],
                        "price": product["precio_venta"],
                    })
                else:
                    self._json(200, {"found": False, "barcode": barcode})

            def log_message(self, format, *args):
                return

        try:
            self.server = ThreadingHTTPServer(("0.0.0.0", self.port), Handler)
        except OSError:
            self.server = ThreadingHTTPServer(("0.0.0.0", 0), Handler)
            self.port = self.server.server_address[1]
        self.server.daemon_threads = True
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def pairing_payload(self, address=None):
        address = address or self.addresses[0]
        return json.dumps({
            "type": "oslo-reader",
            "version": 1,
            "baseUrl": f"http://{address}:{self.port}",
            "token": self.token,
        }, separators=(",", ":"))

    def close(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.server = None
