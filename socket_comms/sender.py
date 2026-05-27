import socket
import numpy as np

HOST, PORT         = "127.0.0.1", 5005
SAMPLES_PER_PACKET = 4096
N_PACKETS          = 10

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

for i in range(N_PACKETS):
    samples = (np.random.randn(SAMPLES_PER_PACKET) + 1j * np.random.randn(SAMPLES_PER_PACKET)).astype(np.complex64)
    sock.sendto(samples.tobytes(), (HOST, PORT))
    print(f"[sender] sent packet {i+1}/{N_PACKETS}")

sock.sendto(b"END", (HOST, PORT))
sock.close()
print("[sender] done")
