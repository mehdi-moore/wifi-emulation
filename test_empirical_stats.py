import numpy as np
import matplotlib.pyplot as plt

# ------------------------------------------------------------
# 1. LOAD
# ------------------------------------------------------------
PACKET_LEN_PATH = "/home/mehdi/Desktop/wifi_traffic_analysis/IQ-analysis/packet_length_arr.npy"
GAPS_PATH       = "/home/mehdi/Desktop/wifi_traffic_analysis/IQ-analysis/gaps_arr.npy"

packet_len_arr = np.load(PACKET_LEN_PATH)
gaps_arr       = np.load(GAPS_PATH)

# ------------------------------------------------------------
# 2. SAMPLE
# ------------------------------------------------------------
n_samples = 1000
packet_len_arr_test = np.random.choice(packet_len_arr, size=n_samples, replace=True)
gaps_arr_test       = np.random.choice(gaps_arr,       size=n_samples, replace=True)

# ------------------------------------------------------------
# 3. PLOT OVERLAYED HISTOGRAMS WITH X-LIMITS
# ------------------------------------------------------------
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

# ---- Packet Length (left) ----
bins_packet = np.histogram_bin_edges(
    np.concatenate([packet_len_arr, packet_len_arr_test]),
    bins='auto'
)
ax1.hist(packet_len_arr, bins=bins_packet, alpha=0.5, color='blue',
         label='Original', density=True)
ax1.hist(packet_len_arr_test, bins=bins_packet, alpha=0.5, color='red',
         label='Sampled', density=True)
ax1.set_title('Packet Duration')
ax1.set_xlabel('Duration')
ax1.set_ylabel('Density')
ax1.set_xlim(0, 10)          # <-- limit left plot x-axis
ax1.legend()

# ---- Gaps Duration (right) ----
bins_gaps = np.histogram_bin_edges(
    np.concatenate([gaps_arr, gaps_arr_test]),
    bins='auto'
)
ax2.hist(gaps_arr, bins=bins_gaps, alpha=0.5, color='blue',
         label='Original', density=True)
ax2.hist(gaps_arr_test, bins=bins_gaps, alpha=0.5, color='red',
         label='Sampled', density=True)
ax2.set_title('Gaps Duration')
ax2.set_xlabel('Duration')
ax2.set_ylabel('Density')
ax2.set_xlim(0, 100)         # <-- limit right plot x-axis
ax2.legend()

plt.tight_layout()
plt.show()
cccc = 0