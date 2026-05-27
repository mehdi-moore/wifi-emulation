import socket
import numpy as np

HOST, PORT         = "127.0.0.1", 5005
BYTES_PER_PACKET   = 4096 * 8  # complex64 = 8 bytes per sample

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((HOST, PORT))
print(f"[receiver] listening on {HOST}:{PORT}")

total_samples = 0
while True:
    data, _ = sock.recvfrom(BYTES_PER_PACKET)
    if data == b"END":
        break
    total_samples += len(data) // 8
    print(f"[receiver] packet received | samples: {len(data) // 8} | total: {total_samples}")

sock.close()
print(f"\n[receiver] done. total samples: {total_samples}")