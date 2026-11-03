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

        # Setup UDP socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        
        # Bind to all interfaces on the port
        self.sock.bind(('', BROADCAST_PORT))

    def run(self):
        print(f"[NetHop] Network listener running for device '{self.device_id}'. Active: {self.is_active}")
        while self.running:
            try:
                data, addr = self.sock.recvfrom(2048)
                if not data:
                    continue

                msg = json.loads(data.decode('utf-8'))
                sender = msg.get("sender")
                action = msg.get("action")

                # If WE are dormant, and SOMEONE ELSE sent a HOP_IN broadcast:
                if not self.is_active and action == "HOP_IN" and sender != self.device_id:
                    print(f"[NetHop] Inbound hop from '{sender}' received! Becoming ACTIVE.")
                    self.is_active = True
                    if self.on_hop_in:
                        self.on_hop_in()

            except Exception as e:
                time.sleep(0.05)

    def send_hop(self):
        """Sends broadcast to wake up other devices and puts this device into dormant state."""
        msg = {
            "sender": self.device_id,
            "action": "HOP_IN",
            "timestamp": time.time()
        }
        data = json.dumps(msg).encode('utf-8')
        
        # Send broadcast to standard 255.255.255.255
        try:
            self.sock.sendto(data, ('255.255.255.255', BROADCAST_PORT))
            # Also send to fallback '<broadcast>' for cross-platform compatibility
            self.sock.sendto(data, ('<broadcast>', BROADCAST_PORT))
        except Exception as e:
            print(f"[NetHop] Send error: {e}")

        self.is_active = False
        print(f"[NetHop] Sent HOP_IN broadcast from '{self.device_id}'. Now DORMANT.")

    def stop(self):
        self.running = False
        try:
            self.sock.close()
        except:
            pass