import numpy as np
from scipy.signal import resample_poly

# --- config ---
SAMPLE_RATE      = 80e6
DURATION_S       = 1.0
TOTAL_SAMPLES    = int(SAMPLE_RATE * DURATION_S)
TILE_PATH        = "/home/labuser/Desktop/wifi-emulation/wifi_ofdm_tile_20MSPS_CMPLX64.bin"
PACKET_LEN_PATH  = "/home/labuser/Desktop/wifi_traffic_analysis/IQ-analysis/packet_length_arr.npy"
GAPS_PATH        = "/home/labuser/Desktop/wifi_traffic_analysis/IQ-analysis/gaps_arr.npy"
OUT_PATH         = "iq_1sec.cfile"

# --- empirical traffic data ---
packet_len_arr = np.load(PACKET_LEN_PATH)
gaps_arr       = np.load(GAPS_PATH)

# --- OFDM tile, loaded and resampled once ---
tile         = np.fromfile(TILE_PATH, dtype=np.complex64)
tile         = resample_poly(tile, 4, 1).astype(np.complex64)
tile_samples = len(tile)


def empirical_onoff(total_samples, packet_len_arr, gaps_arr, fs):
    segments = []
    n, state = 0, 0
    while n < total_samples:
        dur_us = np.random.choice(packet_len_arr) if state == 1 else np.random.choice(gaps_arr)
        dur    = int(dur_us * 1e-6 * fs)
        segments.append((state, min(dur, total_samples - n)))
        n += dur
        state ^= 1
    return segments


def generate_iq(total_samples):
    segments = empirical_onoff(total_samples, packet_len_arr, gaps_arr, SAMPLE_RATE)
    iq = np.zeros(total_samples, dtype=np.complex64)
    idx = 0
    for state, n_samp in segments:
        if state == 1:
            iq[idx:idx + n_samp] = np.tile(tile, int(np.ceil(n_samp / tile_samples)))[:n_samp]
        idx += n_samp
    return iq


if __name__ == "__main__":
    iq = generate_iq(TOTAL_SAMPLES)
    iq.tofile(OUT_PATH)
    print(f"Wrote {len(iq)} complex64 samples ({len(iq) * 8} bytes) to {OUT_PATH}")