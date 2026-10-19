"""Fixed-target guest-only proxies. Does not log payload, SQL or credentials."""
import argparse, json, selectors, socket, threading, time

CONFIG = {
    'pg': (('172.30.28.1', 15483), ('127.0.0.1', 55483)),
    'redis': (('172.30.28.1', 16379), ('127.0.0.1', 6379)),
}
ALLOWED_CLIENT = '172.30.28.2'
SLOTS = threading.BoundedSemaphore(16)

def relay(client, target):
    peer = None
    try:
        client.settimeout(5)
        peer = socket.create_connection(target, timeout=5)
        client.setblocking(False)
        peer.setblocking(False)
        with selectors.DefaultSelector() as poll:
            poll.register(client, selectors.EVENT_READ, peer)
            poll.register(peer, selectors.EVENT_READ, client)
            deadline = time.monotonic() + 60
            while time.monotonic() < deadline:
                events = poll.select(timeout=1)
                if not events:
                    continue
                for key, _ in events:
                    try:
                        data = key.fileobj.recv(65536)
                    except BlockingIOError:
                        continue
                    if not data:
                        return
                    # Blocking bounded send handles backpressure without dropping bytes.
                    destination = key.data
                    destination.settimeout(5)
                    destination.sendall(data)
                    destination.setblocking(False)
                    deadline = time.monotonic() + 60
    except (OSError, TimeoutError):
        pass
    finally:
        client.close()
        if peer is not None:
            peer.close()
        SLOTS.release()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('service', choices=sorted(CONFIG))
    args = parser.parse_args()
    bind, target = CONFIG[args.service]
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(bind)
        listener.listen(16)
        print(json.dumps({'service': args.service, 'bind': bind, 'fixed_target': target,
                          'allowed_client': ALLOWED_CLIENT, 'payload_logging': False}), flush=True)
        while True:
            client, address = listener.accept()
            if address[0] != ALLOWED_CLIENT or not SLOTS.acquire(blocking=False):
                client.close()
                continue
            threading.Thread(target=relay, args=(client, target), daemon=True).start()
