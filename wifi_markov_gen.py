import socket
import threading
import queue
import numpy as np
from scipy.signal import resample_poly

UPSAMPLE           = 2
SAMPLE_RATE        = 20e6 * UPSAMPLE
TOTAL_SAMPLES      = int(SAMPLE_RATE * 1.0)
MEAN_ON_US         = 200.0
DUTY_CYCLE         = 0.4
MEAN_OFF_US        = MEAN_ON_US * (1 - DUTY_CYCLE) / DUTY_CYCLE
SAMPLES_PER_PACKET = 4096
UDP_HOST           = "127.0.0.1"
UDP_PORT           = 5005


def markov_onoff(total_samples, mean_on_us, mean_off_us, fs):
    segments = []
    n, state = 0, 0
    while n < total_samples:
        dur = max(1, int(np.random.exponential((mean_on_us if state == 1 else mean_off_us) * 1e-6 * fs)))
        segments.append((state, min(dur, total_samples - n)))
        n += dur
        state ^= 1
    return segments


def generate_iq():
    tile         = np.fromfile("wifi_ofdm_tile_20MSPS_CMPLX64.bin", dtype=np.complex64)
    tile         = resample_poly(tile, UPSAMPLE, 1).astype(np.complex64)
    tile_samples = len(tile)

    segments = markov_onoff(TOTAL_SAMPLES, MEAN_ON_US, MEAN_OFF_US, SAMPLE_RATE)
    iq = np.zeros(TOTAL_SAMPLES, dtype=np.complex64)
    idx = 0
    for state, n_samp in segments:
        if state == 1:
            iq[idx:idx + n_samp] = np.tile(tile, int(np.ceil(n_samp / tile_samples)))[:n_samp]
        idx += n_samp
    return iq


def send_iq(iq):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    for i in range(0, len(iq), SAMPLES_PER_PACKET):
        sock.sendto(iq[i:i + SAMPLES_PER_PACKET].tobytes(), (UDP_HOST, UDP_PORT))
    sock.close()


if __name__ == "__main__":
    send_q = queue.Queue(maxsize=4)

    def producer():
        batch_cnt = 0
        while True:
            iq = generate_iq()
            batch_cnt += 1
            print(f"[gen] batch {batch_cnt} ready")
            send_q.put(iq)

    def consumer():
        while True:
            if send_q.empty():
                print("[tx] WARNING: queue empty, waiting for data...")
            iq = send_q.get()
            send_iq(iq)

    threading.Thread(target=producer, daemon=True).start()
    threading.Thread(target=consumer, daemon=True).start()

    threading.Event().wait()