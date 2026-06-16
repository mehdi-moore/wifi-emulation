# WiFi IQ Emulation Pipeline

A Python-based Wi-Fi signal emulator that generates synthetic OFDM IQ data using a Markov on/off model and streams it to a USRP X410 SDR for over-the-air transmission. Received samples are captured on a second channel and plotted live.

---

## Directory Structure

```
wifi-emulation/
├── wifi_markov_gen.py              # Main transmitter/receiver pipeline
├── wifi_ofdm_tile_20MSPS_CMPLX64.bin  # Pre-recorded OFDM IQ tile (20 MSPS, complex64)
├── socket_comms/
│   ├── receiver.py                 # Minimal UDP receiver with live plot
│   ├── receiver_gui.py             # Tkinter GUI receiver with embedded plots
│   └── sender.py                   # Test UDP sender (random IQ data)
└── README.md
```

---

## How It Works

### Signal Generation
A pre-recorded OFDM tile (`wifi_ofdm_tile_20MSPS_CMPLX64.bin`) is loaded and resampled from 20 MSPS to 40.96 MSPS using `resample_poly(tile, 256, 125)`. A 2-state Markov chain generates ON/OFF burst segments with exponentially distributed durations, mimicking real Wi-Fi traffic at a configurable duty cycle. The OFDM tile is tiled into ON slots; OFF slots are zeros.

### Streaming Pipeline
Three threads run concurrently:

- **Producer** — calls `generate_iq()` continuously, puts batches into `send_q`
- **Consumer** — pulls batches from `send_q`, streams to USRP TX via `send_iq_usrp()`
- **Receiver** — captures samples from USRP RX continuously, accumulates into `plot_q`

A separate **plot process** (`multiprocessing.Process`) consumes from `plot_q` and renders live time-domain and spectrum plots. Using a separate process avoids matplotlib's main-thread restriction and prevents plot overhead from causing TX underruns.

### USRP Configuration
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
| `SAMPLE_RATE` | 40.96 MHz | TX/RX sample rate |
| `BATCH_DURATION_S` | 0.1 s | Duration of each generated IQ batch |
| `MEAN_ON_US` | 200 µs | Mean ON burst duration |
| `DUTY_CYCLE` | 0.4 | Fraction of time signal is ON |
| `CHUNK` | 2048 | Samples per USRP send call |
| `ACCUM_SAMPLES` | 5,000,000 | RX samples to accumulate before plotting |
| `PLOT_SAMPLES` | 500,000 | Samples actually plotted (first 10% of accumulation) |
| `FREQ` | 5.18 GHz | Centre frequency |
| `GAIN` | 50 dB | TX gain |
| `RX_GAIN` | 30 dB | RX gain |

---

## Running

### Main pipeline (USRP required)
```bash
cd ~/Desktop/wifi-emulation
python3 wifi_markov_gen.py
```

### Socket receiver GUI (no USRP needed)
```bash
python3 socket_comms/receiver_gui.py
```

### Test sender (for testing receiver without USRP)
```bash
# Terminal 1
python3 socket_comms/receiver.py

# Terminal 2
python3 socket_comms/sender.py
```

---

## Dependencies

```
numpy
scipy
matplotlib
uhd (UHD Python API, requires UHD 4.x)
tkinter (built-in)
```
