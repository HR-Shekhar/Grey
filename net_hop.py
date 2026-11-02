import socket
import json
import threading
import time

BROADCAST_PORT = 5005

class GreyNetworkNode(threading.Thread):
    def __init__(self, device_id="pi_1", is_active=True, on_hop_in=None):
        super().__init__(daemon=True)
        self.device_id = device_id
        self.is_active = is_active
        self.on_hop_in = on_hop_in
        self.running = True

        # Setup UDP socket with broadcast enabled
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sock.bind(('', BROADCAST_PORT))

    def run(self):
        while self.running:
            try:
                data, addr = self.sock.recvfrom(1024)
                if not data:
                    continue

                msg = json.loads(data.decode('utf-8'))
                sender = msg.get("sender")
                action = msg.get("action")

                # If we are currently dormant and another device tells us to take over
                if not self.is_active and action == "HOP_IN" and sender != self.device_id:
                    print(f"[NetHop] Received hop command from {sender}! Activating...")
                    self.is_active = True
                    if self.on_hop_in:
                        self.on_hop_in()

            except Exception as e:
                time.sleep(0.05)

    def send_hop(self):
        """Sends broadcast to other devices and makes this device dormant."""
        msg = {
            "sender": self.device_id,
            "action": "HOP_IN",
            "timestamp": time.time()
        }
        data = json.dumps(msg).encode('utf-8')
        # Broadcast to entire local subnet
        self.sock.sendto(data, ('<broadcast>', BROADCAST_PORT))
        self.is_active = False
        print(f"[NetHop] Sent HOP_IN broadcast. Becoming dormant.")

    def stop(self):
        self.running = False
        self.sock.close()