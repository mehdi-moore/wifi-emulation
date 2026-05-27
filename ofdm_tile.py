import numpy as np
import matplotlib.pyplot as plt

# Parameters
SAMPLE_RATE   = 20e6
FFT_SIZE      = 64
CP_LEN        = 16

# 802.11a subcarrier map: 48 data, 4 pilots, DC null, guard bands
DATA_CARRIERS  = [i % FFT_SIZE for i in
                  list(range(-26, -21)) + list(range(-20, -7)) +
                  list(range(-6,   0)) + list(range(1,   7))  +
                  list(range(8,   21)) + list(range(22, 27))]
PILOT_CARRIERS = [i % FFT_SIZE for i in [-21, -7, 7, 21]]

freq_bins = np.arange(-32, 32)



def qpsk(n):
    b = np.random.randint(0, 2, (n, 2))
    return (1 - 2*b[:, 0] + 1j*(1 - 2*b[:, 1])) / np.sqrt(2)

# Build symbol
freq = np.zeros(FFT_SIZE, dtype=np.complex64)
freq[freq_bins]  = qpsk(len(freq_bins))

time   = np.fft.ifft(freq)
symbol = np.concatenate([time[-CP_LEN:], time]).astype(np.complex64)

print(f"Samples : {len(symbol)}  ({len(symbol)/SAMPLE_RATE*1e6:.1f} µs)")
symbol.tofile("wifi_ofdm_tile.bin")
print(f"Saved   : wifi_ofdm_tile.bin  ({symbol.nbytes} bytes)")

# --- Plots ---
t_us  = np.arange(len(symbol)) / SAMPLE_RATE * 1e6
spec  = np.fft.fftshift(np.fft.fft(symbol))
freqs = np.fft.fftshift(np.fft.fftfreq(len(symbol), d=1/SAMPLE_RATE)) / 1e6
psd   = 20 * np.log10(np.abs(spec) + 1e-12)

fig, axes = plt.subplots(2, 1, figsize=(9, 6))
fig.suptitle("802.11a OFDM Symbol (4 µs tile)", fontweight="bold")

axes[0].plot(t_us, symbol.real, label="I")
axes[0].plot(t_us, symbol.imag, label="Q", linestyle="--")
axes[0].set_xlabel("Time (µs)")
axes[0].set_ylabel("Amplitude")
axes[0].legend(fontsize=8)
axes[0].grid(True, alpha=0.4)

axes[1].plot(freqs, psd)
axes[1].set_xlabel("Frequency (MHz)")
axes[1].set_ylabel("Magnitude (dB)")
axes[1].grid(True, alpha=0.4)

plt.tight_layout()
plt.show()
cccc=0;
