import socket
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import welch, resample_poly

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
    #sock.sendto(b"END", (UDP_HOST, UDP_PORT))
    sock.close()
    print("[tx] done")


def plot_iq(iq):
    t_ms        = np.arange(len(iq)) / SAMPLE_RATE * 1e3
    freqs, psd  = welch(iq, fs=SAMPLE_RATE, nperseg=128, noverlap=64, return_onesided=False)
    freqs       = np.fft.fftshift(freqs) / 1e6
    psd         = np.fft.fftshift(10 * np.log10(psd + 1e-12))

    fig, axes = plt.subplots(2, 1, figsize=(12, 6))
    axes[0].plot(t_ms, np.abs(iq), linewidth=0.5)
    axes[0].set(xlabel="Time (ms)", ylabel="|IQ|")
    axes[0].grid(True, alpha=0.4)
    axes[1].plot(freqs, psd, linewidth=1.0)
    axes[1].set(xlabel="Frequency (MHz)", ylabel="PSD (dB/Hz)")
    axes[1].set_xlim(-20, 20)
    axes[1].grid(True, alpha=0.4)
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    for i in range (20):
        print(f"sending batch # {i}")
        iq = generate_iq()
        send_iq(iq)
        #plot_iq(iq)