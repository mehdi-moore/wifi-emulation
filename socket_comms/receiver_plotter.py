import socket
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import welch

HOST, PORT         = "127.0.0.1", 5005
BYTES_PER_PACKET   = 4096 * 8  # complex64 = 8 bytes per sample
SAMPLE_RATE        = 40e6
ACCUM_SAMPLES      = 5_000_000
PLOT_SAMPLES       = 500_000
PRINT_EVERY        = 50

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((HOST, PORT))
print(f"[receiver] listening on {HOST}:{PORT}")

plt.ion()
fig, axes = plt.subplots(2, 1, figsize=(12, 6))

total_samples  = 0
packet_cnt     = 0
accumulated    = []
accum_samples  = 0

while True:
    data, _ = sock.recvfrom(BYTES_PER_PACKET)
    samples  = np.frombuffer(data, dtype=np.complex64)
    packet_cnt    += 1
    total_samples += len(samples)
    accum_samples += len(samples)
    accumulated.append(samples)

    if packet_cnt % PRINT_EVERY == 0:
        print(f"[rx] packets: {packet_cnt} | total samples: {total_samples}")

    if accum_samples >= ACCUM_SAMPLES:
        iq        = np.concatenate(accumulated)[:PLOT_SAMPLES]
        accumulated  = []
        accum_samples = 0

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