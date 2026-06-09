import socket
import threading
import queue
import numpy as np
import uhd
from scipy.signal import resample_poly

SAMPLE_RATE        = 40.96e6
BATCH_DURATION_S   = 0.1
TOTAL_SAMPLES      = int(SAMPLE_RATE * BATCH_DURATION_S)
MEAN_ON_US         = 200.0
DUTY_CYCLE         = 0.4
MEAN_OFF_US        = MEAN_ON_US * (1 - DUTY_CYCLE) / DUTY_CYCLE
SAMPLES_PER_PACKET = 4096
CHUNK              = 2048
UDP_HOST           = "127.0.0.1"
UDP_PORT           = 5005
USRP_ADDR          = "addr=192.168.20.2"
GAIN               = 50.0
FREQ               = 5.18e9
TILE_PATH          = "/home/mehdi/Desktop/wifi-emulation/wifi_ofdm_tile_20MSPS_CMPLX64.bin"


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
    tile         = np.fromfile(TILE_PATH, dtype=np.complex64)
    tile         = resample_poly(tile, 256, 125).astype(np.complex64)
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


def init_usrp():
    usrp = uhd.usrp.MultiUSRP(USRP_ADDR)
    usrp.set_clock_source("internal")
    ch = 0
    usrp.set_tx_rate(SAMPLE_RATE, ch)
    usrp.set_tx_gain(GAIN, ch)
    usrp.set_tx_freq(uhd.types.TuneRequest(FREQ), ch)
    tx_args          = uhd.usrp.StreamArgs("fc32", "sc16")
    tx_args.channels = [ch]
    tx_stream        = usrp.get_tx_stream(tx_args)
    md               = uhd.types.TXMetadata()
    md.start_of_burst = True
    md.end_of_burst   = False
    print(f"[usrp] initialised — rate: {SAMPLE_RATE/1e6} MHz, freq: {FREQ/1e9} GHz, gain: {GAIN} dB")
    return usrp, tx_stream, md


def send_iq_usrp(iq, tx_stream, md, sock):
    n, i = len(iq), 0
    while i < n:
        chunk = np.ascontiguousarray(iq[i:i + CHUNK].reshape(1, -1))
        tx_stream.send(chunk, md)
        sock.sendto(chunk[0].tobytes(), (UDP_HOST, UDP_PORT))
        md.start_of_burst = False
        i += CHUNK


if __name__ == "__main__":
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    usrp, tx_stream, md = init_usrp()
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
            send_iq_usrp(iq, tx_stream, md, sock)

    threading.Thread(target=producer, daemon=True).start()
    threading.Thread(target=consumer, daemon=True).start()

    threading.Event().wait()