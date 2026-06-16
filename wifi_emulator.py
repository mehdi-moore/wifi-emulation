import socket
import time
import threading
import queue
import multiprocessing
import numpy as np
import uhd
from scipy.signal import resample_poly, welch
import matplotlib.pyplot as plt

TX_MODE            = "usrp"  # "usrp" or "socket"
SAMPLE_RATE        = 40.96e6
BATCH_DURATION_S   = 0.1
TOTAL_SAMPLES      = int(SAMPLE_RATE * BATCH_DURATION_S)
MEAN_ON_US         = 200.0
DUTY_CYCLE         = 0.4
MEAN_OFF_US        = MEAN_ON_US * (1 - DUTY_CYCLE) / DUTY_CYCLE
CHUNK              = 2048
UDP_HOST           = "127.0.0.1"
UDP_PORT           = 5005
USRP_ADDR          = "addr=192.168.20.2"
GAIN               = 50.0
RX_GAIN            = 30.0
FREQ               = 5.18e9
TILE_PATH          = "/home/mehdi/Desktop/wifi-emulation/wifi_ofdm_tile_20MSPS_CMPLX64.bin"
ACCUM_SAMPLES      = 5_000_000
PLOT_SAMPLES       = 500_000


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


def send_iq(iq, sock):
    for i in range(0, len(iq), CHUNK):
        sock.sendto(iq[i:i + CHUNK].tobytes(), (UDP_HOST, UDP_PORT))


def init_usrp():
    usrp = uhd.usrp.MultiUSRP(USRP_ADDR)
    usrp.set_clock_source("internal")

    # --- TX ---
    tx_ch = 0
    usrp.set_tx_rate(SAMPLE_RATE, tx_ch)
    usrp.set_tx_gain(GAIN, tx_ch)
    usrp.set_tx_freq(uhd.types.TuneRequest(FREQ), tx_ch)
    tx_args          = uhd.usrp.StreamArgs("fc32", "sc16")
    tx_args.channels = [tx_ch]
    tx_stream        = usrp.get_tx_stream(tx_args)
    md               = uhd.types.TXMetadata()
    md.start_of_burst = True
    md.end_of_burst   = False

    # --- RX ---
    rx_ch = 1
    usrp.set_rx_rate(SAMPLE_RATE, rx_ch)
    usrp.set_rx_gain(RX_GAIN, rx_ch)
    usrp.set_rx_freq(uhd.types.TuneRequest(FREQ), rx_ch)
    usrp.set_rx_antenna("RX1", rx_ch)
    rx_args          = uhd.usrp.StreamArgs("fc32", "sc16")
    rx_args.channels = [rx_ch]
    rx_stream        = usrp.get_rx_stream(rx_args)

    print(f"[usrp] TX — rate: {SAMPLE_RATE/1e6} MHz, freq: {FREQ/1e9} GHz, gain: {GAIN} dB")
    print(f"[usrp] RX — rate: {SAMPLE_RATE/1e6} MHz, freq: {FREQ/1e9} GHz, gain: {RX_GAIN} dB")
    return usrp, tx_stream, md, rx_stream


def send_iq_usrp(iq, tx_stream, md):
    n, i = len(iq), 0
    while i < n:
        chunk = np.ascontiguousarray(iq[i:i + CHUNK].reshape(1, -1))
        tx_stream.send(chunk, md)
        md.start_of_burst = False
        i += CHUNK


def receive_iq_usrp(rx_stream, plot_q):
    recv_md    = uhd.types.RXMetadata()
    stream_cmd = uhd.types.StreamCMD(uhd.types.StreamMode.start_cont)
    stream_cmd.stream_now = True
    rx_stream.issue_stream_cmd(stream_cmd)

    accumulated   = []
    accum_samples = 0
    recv_buf      = np.zeros((1, CHUNK), dtype=np.complex64)

    while True:
        rx_stream.recv(recv_buf, recv_md)
        samples        = recv_buf[0].copy()
        accumulated.append(samples)
        accum_samples += len(samples)

        if accum_samples >= ACCUM_SAMPLES:
            iq            = np.concatenate(accumulated)[:PLOT_SAMPLES]
            accumulated   = []
            accum_samples = 0
            if not plot_q.full():
                plot_q.put(iq)


def plot_worker(plot_q):
    plt.ion()
    fig, axes = plt.subplots(2, 1, figsize=(12, 6))
    while True:
        iq = plot_q.get()

        t_ms       = np.arange(len(iq)) / SAMPLE_RATE * 1e3
        freqs, psd = welch(iq, fs=SAMPLE_RATE, nperseg=128, noverlap=64, return_onesided=False)
        freqs      = np.fft.fftshift(freqs) / 1e6
        psd        = np.fft.fftshift(10 * np.log10(psd + 1e-12))

        axes[0].cla()
        axes[0].plot(t_ms, np.abs(iq), linewidth=0.5)
        axes[0].set(xlabel="Time (ms)", ylabel="|IQ|")
        axes[0].grid(True, alpha=0.4)
        axes[1].cla()
        axes[1].plot(freqs, psd, linewidth=1.0)
        axes[1].set(xlabel="Frequency (MHz)", ylabel="PSD (dB/Hz)")
        axes[1].set_xlim(-20, 20)
        axes[1].grid(True, alpha=0.4)
        plt.tight_layout()
        plt.pause(0.01)


if __name__ == "__main__":
    send_q = queue.Queue(maxsize=4)

    if TX_MODE == "usrp":
        usrp, tx_stream, md, rx_stream = init_usrp()
        plot_q = multiprocessing.Queue(maxsize=2)

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
                send_iq_usrp(iq, tx_stream, md)

        def receiver():
            receive_iq_usrp(rx_stream, plot_q)

        threading.Thread(target=producer,  daemon=True).start()
        threading.Thread(target=consumer,  daemon=True).start()
        threading.Thread(target=receiver,  daemon=True).start()
        multiprocessing.Process(target=plot_worker, args=(plot_q,), daemon=True).start()

    elif TX_MODE == "socket":
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

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
                send_iq(iq, sock)

        threading.Thread(target=producer, daemon=True).start()
        threading.Thread(target=consumer, daemon=True).start()

    threading.Event().wait()