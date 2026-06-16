# WiFi IQ Emulation Pipeline

A Python-based Wi-Fi signal emulator that generates synthetic OFDM IQ data using a Markov on/off model and streams it either to a USRP X410 SDR for over-the-air transmission, or to a UDP socket for local testing. Received samples are captured and plotted live.

---

## Directory Structure

```
wifi-emulation/
├── wifi_markov_gen.py                  # Main transmitter pipeline
├── wifi_ofdm_tile_20MSPS_CMPLX64.bin  # Pre-recorded OFDM IQ tile (20 MSPS, complex64)
├── socket_comms/
│   ├── receiver.py                     # Minimal UDP receiver with live plot
│   ├── receiver_gui.py                 # Tkinter GUI receiver with embedded plots
│   └── sender.py                       # Test UDP sender (random IQ data)
└── README.md
```

---

## How It Works

### Signal Generation
A pre-recorded OFDM tile (`wifi_ofdm_tile_20MSPS_CMPLX64.bin`) is loaded and resampled from 20 MSPS to 40.96 MSPS using `resample_poly(tile, 256, 125)`. A 2-state Markov chain generates ON/OFF burst segments with exponentially distributed durations, mimicking real Wi-Fi traffic at a configurable duty cycle. The OFDM tile is tiled into ON slots; OFF slots are zeros.

### Streaming Pipeline
Two threads always run:

- **Producer** — calls `generate_iq()` continuously, puts batches into `send_q`
- **Consumer** — pulls batches from `send_q`, sends via USRP or socket depending on `TX_MODE`

In USRP mode, two additional components run:

- **Receiver thread** — captures samples from USRP RX, accumulates into `plot_q`
- **Plot process** — separate `multiprocessing.Process` consuming from `plot_q`, renders live time-domain and spectrum plots

---

## Running

### Selecting Mode
Set `TX_MODE` at the top of `wifi_markov_gen.py`:

```python
TX_MODE = "usrp"    # transmit via USRP X410
TX_MODE = "socket"  # transmit via UDP socket
```

---

### USRP Mode
Requires a USRP X410 connected at `192.168.20.2`. TX and RX both handled internally — no separate receiver needed.

```bash
cd ~/Desktop/wifi-emulation
python3 wifi_markov_gen.py
```

A live plot window will open showing the received time-domain waveform and spectrum.

---

### Socket Mode
The transmitter and receiver run in separate terminals.

**Terminal 1 — start the receiver first:**
```bash
cd ~/Desktop/wifi-emulation/socket_comms
python3 receiver_gui.py
```
Enter the IP and port (defaults: `127.0.0.1`, `5005`) and click Start.

**Terminal 2 — start the transmitter:**
```bash
cd ~/Desktop/wifi-emulation
python3 wifi_markov_gen.py
```

The receiver GUI will show live time-domain and spectrum plots as packets arrive. The receiver must be started before the transmitter since UDP packets sent before the socket is bound are silently lost.

Alternatively, use the minimal terminal receiver instead of the GUI:
```bash
python3 socket_comms/receiver.py
```

---

### Test sender (no USRP, no Markov generator)
Sends random IQ data to the receiver for quick testing:

```bash
# Terminal 1
python3 socket_comms/receiver.py

# Terminal 2
python3 socket_comms/sender.py
```

---

## USRP Configuration
- **Device:** NI USRP X410 at `192.168.20.2`
- **TX:** channel 0, antenna TX/RX0
- **RX:** channel 1, antenna RX1
- **Sample rate:** 40.96 MSPS
- **Frequency:** 5.18 GHz (Wi-Fi channel 36)
- **TX gain:** 50 dB, **RX gain:** 30 dB

---

## Key Parameters

| Parameter | Default | Description |
|---|---|---|
| `TX_MODE` | `"usrp"` | Transmission mode: `"usrp"` or `"socket"` |
| `SAMPLE_RATE` | 40.96 MHz | TX/RX sample rate |
| `BATCH_DURATION_S` | 0.1 s | Duration of each generated IQ batch |
| `MEAN_ON_US` | 200 µs | Mean ON burst duration |
| `DUTY_CYCLE` | 0.4 | Fraction of time signal is ON |
| `CHUNK` | 2048 | Samples per send call |
| `ACCUM_SAMPLES` | 5,000,000 | RX samples to accumulate before plotting |
| `PLOT_SAMPLES` | 500,000 | Samples actually plotted (first 10% of accumulation) |
| `FREQ` | 5.18 GHz | Centre frequency |
| `GAIN` | 50 dB | TX gain |
| `RX_GAIN` | 30 dB | RX gain |
| `UDP_HOST` | `127.0.0.1` | Socket receiver IP address |
| `UDP_PORT` | 5005 | Socket receiver port |

---

## Dependencies

```
numpy
scipy
matplotlib
tkinter (built-in)
uhd (UHD Python API, required for USRP mode only)
```
