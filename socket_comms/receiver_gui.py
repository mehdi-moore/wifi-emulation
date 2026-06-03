import socket
import threading
import numpy as np
import tkinter as tk
from scipy.signal import welch
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


BYTES_PER_PACKET   = 4096 * 8
SAMPLE_RATE        = 40e6
ACCUM_SAMPLES      = 5_000_000
PLOT_SAMPLES       = 500_000


class ReceiverGUI:
    def __init__(self, root):
        self.root       = root
        self.root.title("WiFi IQ Receiver")
        self.sock       = None
        self.running    = False
        self.packet_cnt = 0

        # --- controls ---
        ctrl = tk.Frame(root)
        ctrl.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)

        tk.Label(ctrl, text="IP:").pack(side=tk.LEFT)
        self.host_var = tk.StringVar(value="127.0.0.1")
        tk.Entry(ctrl, textvariable=self.host_var, width=14).pack(side=tk.LEFT, padx=5)

        tk.Label(ctrl, text="Port:").pack(side=tk.LEFT)
        self.port_var = tk.StringVar(value="5005")
        tk.Entry(ctrl, textvariable=self.port_var, width=8).pack(side=tk.LEFT, padx=5)

        self.btn = tk.Button(ctrl, text="Start", width=8, command=self.toggle)
        self.btn.pack(side=tk.LEFT, padx=5)

        self.status = tk.Label(ctrl, text="idle")
        self.status.pack(side=tk.LEFT, padx=10)

        # --- plots ---
        fig = Figure(figsize=(10, 5))
        self.ax_time = fig.add_subplot(2, 1, 1)
        self.ax_freq = fig.add_subplot(2, 1, 2)
        fig.tight_layout(pad=2.0)

        self.canvas = FigureCanvasTkAgg(fig, master=root)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def toggle(self):
        if self.running:
            self.stop()
        else:
            self.start()

    def start(self):
        host = self.host_var.get()
        port = int(self.port_var.get())
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((host, port))
        self.running    = True
        self.packet_cnt = 0
        self.btn.config(text="Stop")
        self.status.config(text=f"listening on {host}:{port}")
        threading.Thread(target=self.receive_loop, daemon=True).start()

    def stop(self):
        self.running = False
        if self.sock:
            self.sock.close()
            self.sock = None
        self.btn.config(text="Start")
        self.status.config(text="idle")

    def receive_loop(self):
        accumulated   = []
        accum_samples = 0

        while self.running:
            try:
                data, _ = self.sock.recvfrom(BYTES_PER_PACKET)
            except OSError:
                break

            samples        = np.frombuffer(data, dtype=np.complex64)
            self.packet_cnt += 1
            accum_samples  += len(samples)
            accumulated.append(samples)

            self.root.after(0, self.status.config,
                            {"text": f"packets: {self.packet_cnt}"})

            if accum_samples >= ACCUM_SAMPLES:
                iq            = np.concatenate(accumulated)[:PLOT_SAMPLES]
                accumulated   = []
                accum_samples = 0
                self.root.after(0, self.update_plot, iq)

    def update_plot(self, iq):
        t_ms       = np.arange(len(iq)) / SAMPLE_RATE * 1e3
        freqs, psd = welch(iq, fs=SAMPLE_RATE, nperseg=128, noverlap=64, return_onesided=False)
        freqs      = np.fft.fftshift(freqs) / 1e6
        psd        = np.fft.fftshift(10 * np.log10(psd + 1e-12))

        self.ax_time.cla()
        self.ax_time.plot(t_ms, np.abs(iq), linewidth=0.5)
        self.ax_time.set(xlabel="Time (ms)", ylabel="|IQ|")
        self.ax_time.grid(True, alpha=0.4)

        self.ax_freq.cla()
        self.ax_freq.plot(freqs, psd, linewidth=1.0)
        self.ax_freq.set(xlabel="Frequency (MHz)", ylabel="PSD (dB/Hz)")
        self.ax_freq.set_xlim(-20, 20)
        self.ax_freq.grid(True, alpha=0.4)

        self.canvas.draw()


if __name__ == "__main__":
    root = tk.Tk()
    app  = ReceiverGUI(root)
    root.mainloop()