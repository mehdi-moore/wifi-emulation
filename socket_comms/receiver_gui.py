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


class Receiver:
    def __init__(self, host, port, ax_time, ax_freq):
        self.host          = host
        self.port          = port
        self.ax_time       = ax_time
        self.ax_freq       = ax_freq
        self.sock          = None
        self.running       = False
        self.packet_cnt    = 0
        self.accumulated   = []
        self.accum_samples = 0


class ReceiverGUI:
    def __init__(self, root):
        self.root      = root
        self.root.title("WiFi IQ Receiver")
        self.receivers = []
        self.canvas    = None

        # --- controls ---
        ctrl = tk.Frame(root)
        ctrl.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)

        tk.Label(ctrl, text="IP:").pack(side=tk.LEFT)
        self.host_var = tk.StringVar(value="127.0.0.1")
        tk.Entry(ctrl, textvariable=self.host_var, width=14).pack(side=tk.LEFT, padx=5)

        tk.Label(ctrl, text="Ports:").pack(side=tk.LEFT)
        self.ports_var = tk.StringVar(value="5005,5006")
        tk.Entry(ctrl, textvariable=self.ports_var, width=20).pack(side=tk.LEFT, padx=5)

        self.btn = tk.Button(ctrl, text="Start", width=8, command=self.toggle)
        self.btn.pack(side=tk.LEFT, padx=5)

        self.status = tk.Label(ctrl, text="idle")
        self.status.pack(side=tk.LEFT, padx=10)

        # --- plot area (built on start, once we know how many receivers) ---
        self.plot_frame = tk.Frame(root)
        self.plot_frame.pack(fill=tk.BOTH, expand=True)

    def toggle(self):
        if self.receivers and any(r.running for r in self.receivers):
            self.stop()
        else:
            self.start()

    def start(self):
        host = self.host_var.get()
        try:
            ports = [int(p.strip()) for p in self.ports_var.get().split(",") if p.strip()]
        except ValueError:
            self.status.config(text="invalid ports")
            return
        if not ports:
            self.status.config(text="no ports given")
            return

        self.build_plots(ports)

        self.receivers = []
        for port, (ax_time, ax_freq) in zip(ports, self.plot_axes):
            recv = Receiver(host, port, ax_time, ax_freq)
            try:
                recv.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                recv.sock.bind((host, port))
            except OSError as e:
                self.status.config(text=f"port {port}: {e}")
                for r in self.receivers:
                    r.sock.close()
                self.receivers = []
                return
            recv.running = True
            self.receivers.append(recv)

        self.btn.config(text="Stop")
        self.status.config(text=f"listening on {host}:{ports}")

        for recv in self.receivers:
            threading.Thread(target=self.receive_loop, args=(recv,), daemon=True).start()

    def stop(self):
        for recv in self.receivers:
            recv.running = False
            if recv.sock:
                recv.sock.close()
                recv.sock = None
        self.btn.config(text="Start")
        self.status.config(text="idle")

    def build_plots(self, ports):
        for child in self.plot_frame.winfo_children():
            child.destroy()

        n = len(ports)
        fig = Figure(figsize=(5 * n, 5))
        self.plot_axes = []
        for i, port in enumerate(ports):
            ax_time = fig.add_subplot(2, n, i + 1)
            ax_freq = fig.add_subplot(2, n, n + i + 1)
            ax_time.set_title(f"port {port}")
            self.plot_axes.append((ax_time, ax_freq))
        fig.tight_layout(pad=2.0)

        self.canvas = FigureCanvasTkAgg(fig, master=self.plot_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def receive_loop(self, recv):
        while recv.running:
            try:
                data, _ = recv.sock.recvfrom(BYTES_PER_PACKET)
            except OSError:
                break

            samples             = np.frombuffer(data, dtype=np.complex64)
            recv.packet_cnt    += 1
            recv.accum_samples += len(samples)
            recv.accumulated.append(samples)

            self.root.after(0, self.update_status)

            if recv.accum_samples >= ACCUM_SAMPLES:
                iq                 = np.concatenate(recv.accumulated)[:PLOT_SAMPLES]
                recv.accumulated   = []
                recv.accum_samples = 0
                self.root.after(0, self.update_plot, recv, iq)

    def update_status(self):
        parts = [f"port {r.port}: {r.packet_cnt}" for r in self.receivers]
        self.status.config(text=" | ".join(parts))

    def update_plot(self, recv, iq):
        t_ms       = np.arange(len(iq)) / SAMPLE_RATE * 1e3
        freqs, psd = welch(iq, fs=SAMPLE_RATE, nperseg=128, noverlap=64, return_onesided=False)
        freqs      = np.fft.fftshift(freqs) / 1e6
        psd        = np.fft.fftshift(10 * np.log10(psd + 1e-12))

        recv.ax_time.cla()
        recv.ax_time.plot(t_ms, np.abs(iq), linewidth=0.5)
        recv.ax_time.set(xlabel="Time (ms)", ylabel="|IQ|")
        recv.ax_time.set_title(f"port {recv.port}")
        recv.ax_time.grid(True, alpha=0.4)

        recv.ax_freq.cla()
        recv.ax_freq.plot(freqs, psd, linewidth=1.0)
        recv.ax_freq.set(xlabel="Frequency (MHz)", ylabel="PSD (dB/Hz)")
        recv.ax_freq.set_xlim(-20, 20)
        recv.ax_freq.grid(True, alpha=0.4)

        self.canvas.draw()


if __name__ == "__main__":
    root = tk.Tk()
    app  = ReceiverGUI(root)
    root.mainloop()
