#!/usr/bin/env python3
"""
CSI Data Collection GUI — ESP32-CSI-Tool
=========================================
Użycie:
    idf.py monitor | python collect_gui.py > eksperyment.csv

Skrypt czeka na pierwsze dane CSI, a dopiero potem startuje timer.
Markery ruchu są automatycznie wpisywane do pliku (stdout).
Instrukcje widoczne są w oknie GUI — możesz odejść od komputera.
"""

import sys
import time
import threading
import tkinter as tk
import math

# ─────────────────────────────────────────────
#  KONFIGURACJA SESJI  (edytuj tutaj)
# ─────────────────────────────────────────────
STABILIZATION_SECS  = 10   # czas stabilizacji przed pierwszym pomiarem
CYCLES              = 5    # ile razy powtórzyć parę (brak ruchu / ruch)
NO_MOTION_SECS      = 20   # czas fazy "brak ruchu"
MOTION_SECS         = 20   # czas fazy "ruch"
# ─────────────────────────────────────────────

# Kolory
BG          = "#0a0a14"
PANEL_BG    = "#10101e"
ACCENT_WAIT = "#4a9eff"
ACCENT_STILL= "#00e5a0"
ACCENT_MOVE = "#ff3b5c"
ACCENT_DONE = "#ffcc44"
TEXT_DIM    = "#444466"
TEXT_MID    = "#8888bb"
TEXT_BRIGHT = "#eeeeff"

FONT_MONO   = ("Courier New", 12)
FONT_LABEL  = ("Courier New", 13, "bold")
FONT_PHASE  = ("Courier New", 34, "bold")
FONT_TIMER  = ("Courier New", 96, "bold")
FONT_INST   = ("Courier New", 18)
FONT_SMALL  = ("Courier New", 11)

# ─────────────────────────────────────────────
#  SEKWENCJA FAZY
# ─────────────────────────────────────────────
def build_sequence():
    seq = [("STABILIZACJA", STABILIZATION_SECS, ACCENT_WAIT,
            "Stój bez ruchu.\nNie wchodź w zasięg sygnału.")]
    for i in range(1, CYCLES + 1):
        seq.append((f"BRAK RUCHU  [{i}/{CYCLES}]", NO_MOTION_SECS, ACCENT_STILL,
                    "Stój lub siedź nieruchomo.\nNie gestykuluj."))
        seq.append((f"RUCH  [{i}/{CYCLES}]", MOTION_SECS, ACCENT_MOVE,
                    "Macha ręką w poprzek sygnału.\nRegularny ruch co ~2 sekundy."))
    return seq

SEQUENCE = build_sequence()
TOTAL_SECS = sum(s[1] for s in SEQUENCE)


# ─────────────────────────────────────────────
#  STAN GLOBALNY
# ─────────────────────────────────────────────
state = {
    "phase_idx": -1,       # -1 = czekamy na CSI
    "phase_start": None,
    "first_csi": False,
    "running": True,
    "csi_count": 0,
}
state_lock = threading.Lock()


# ─────────────────────────────────────────────
#  ZAPIS DO STDOUT (plik CSV)
# ─────────────────────────────────────────────
def emit(line):
    print(line, flush=True)


def marker(label):
    emit(f"MARKER,{label},{time.time():.6f}")


# ─────────────────────────────────────────────
#  WĄTEK: CZYTANIE STDIN
# ─────────────────────────────────────────────
def stdin_reader():
    for raw in sys.stdin:
        if not state["running"]:
            break
        line = raw.strip()
        if not line.startswith("CSI_DATA"):
            continue
        ts = time.time()
        emit(f"{line},{ts:.6f}")
        with state_lock:
            state["csi_count"] += 1
            if not state["first_csi"]:
                state["first_csi"] = True
                # sygnał do GUI — start sekwencji
                marker("RECORDING_START")


# ─────────────────────────────────────────────
#  GUI
# ─────────────────────────────────────────────
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("CSI Collector — ESP32")
        self.configure(bg=BG)
        self.resizable(False, False)
        self._build_ui()
        self.bind("<Escape>", lambda e: self._quit())
        self.protocol("WM_DELETE_WINDOW", self._quit)
        self._tick()

    # ── UI ──────────────────────────────────
    def _build_ui(self):
        W = 820

        # Header
        hdr = tk.Frame(self, bg=PANEL_BG, pady=10)
        hdr.pack(fill="x")
        tk.Label(hdr, text="ESP32  CSI  COLLECTOR",
                 font=("Courier New", 14, "bold"),
                 fg=TEXT_DIM, bg=PANEL_BG).pack()

        # Status bar — pakiety
        self.var_csi = tk.StringVar(value="Czekam na pierwsze dane CSI...")
        tk.Label(self, textvariable=self.var_csi,
                 font=FONT_SMALL, fg=ACCENT_WAIT, bg=BG).pack(pady=(10, 0))

        # Separator
        tk.Frame(self, bg=TEXT_DIM, height=1, width=W).pack(pady=8)

        # Faza
        self.var_phase = tk.StringVar(value="⏳  OCZEKIWANIE")
        self.lbl_phase = tk.Label(self, textvariable=self.var_phase,
                                  font=FONT_PHASE, fg=ACCENT_WAIT, bg=BG)
        self.lbl_phase.pack(pady=(10, 4))

        # Timer — duży licznik
        self.var_timer = tk.StringVar(value="--")
        self.lbl_timer = tk.Label(self, textvariable=self.var_timer,
                                  font=FONT_TIMER, fg=TEXT_BRIGHT, bg=BG,
                                  width=4, anchor="center")
        self.lbl_timer.pack()

        # Pasek postępu fazy (canvas)
        self.bar_canvas = tk.Canvas(self, width=W - 60, height=18,
                                    bg=PANEL_BG, highlightthickness=0)
        self.bar_canvas.pack(pady=(4, 2))
        self.bar_fill = self.bar_canvas.create_rectangle(
            0, 0, 0, 18, fill=ACCENT_WAIT, outline="")

        tk.Label(self, text="pozostało w fazie",
                 font=FONT_SMALL, fg=TEXT_DIM, bg=BG).pack()

        # Separator
        tk.Frame(self, bg=TEXT_DIM, height=1, width=W).pack(pady=8)

        # Instrukcja
        self.var_inst = tk.StringVar(value="")
        self.lbl_inst = tk.Label(self, textvariable=self.var_inst,
                                 font=FONT_INST, fg=TEXT_MID, bg=BG,
                                 justify="center")
        self.lbl_inst.pack(pady=8)

        # Separator
        tk.Frame(self, bg=TEXT_DIM, height=1, width=W).pack(pady=8)

        # Pasek postępu całości
        total_frame = tk.Frame(self, bg=BG)
        total_frame.pack(fill="x", padx=30, pady=(0, 6))
        tk.Label(total_frame, text="POSTĘP SESJI",
                 font=FONT_SMALL, fg=TEXT_DIM, bg=BG).pack(anchor="w")
        self.total_canvas = tk.Canvas(total_frame, width=W - 60, height=12,
                                      bg=PANEL_BG, highlightthickness=0)
        self.total_canvas.pack(fill="x")
        self.total_fill = self.total_canvas.create_rectangle(
            0, 0, 0, 12, fill=TEXT_DIM, outline="")
        self.var_total = tk.StringVar(value="0 / 0 s")
        tk.Label(total_frame, textvariable=self.var_total,
                 font=FONT_SMALL, fg=TEXT_DIM, bg=BG).pack(anchor="e")

        # Plan faz po prawej / tabela
        plan_frame = tk.Frame(self, bg=PANEL_BG, padx=14, pady=10)
        plan_frame.pack(fill="x", padx=30, pady=(0, 14))
        tk.Label(plan_frame, text="PLAN SESJI",
                 font=FONT_LABEL, fg=TEXT_DIM, bg=PANEL_BG).pack(anchor="w")
        self.phase_labels = []
        for i, (name, dur, col, _) in enumerate(SEQUENCE):
            row = tk.Frame(plan_frame, bg=PANEL_BG)
            row.pack(anchor="w", fill="x")
            dot = tk.Label(row, text="  ○ ", font=FONT_SMALL,
                           fg=TEXT_DIM, bg=PANEL_BG)
            dot.pack(side="left")
            lbl = tk.Label(row,
                           text=f"{name:<28} {dur:>3}s",
                           font=FONT_SMALL, fg=TEXT_DIM, bg=PANEL_BG,
                           anchor="w")
            lbl.pack(side="left")
            self.phase_labels.append((dot, lbl, col))

        # ESC hint
        tk.Label(self, text="[ESC] zakończ nagrywanie",
                 font=FONT_SMALL, fg=TEXT_DIM, bg=BG).pack(pady=(0, 8))

        self.geometry(f"{W}x{self._needed_height()}")

    def _needed_height(self):
        self.update_idletasks()
        return self.winfo_reqheight()

    # ── TICK (co 100ms) ─────────────────────
    def _tick(self):
        if not state["running"]:
            return

        with state_lock:
            first = state["first_csi"]
            count = state["csi_count"]
            idx   = state["phase_idx"]

        bar_w = self.bar_canvas.winfo_width() or 760
        tot_w = self.total_canvas.winfo_width() or 760

        # ── Jeszcze nie ma CSI ──────────────
        if not first:
            self.var_csi.set(f"Czekam na pierwsze dane CSI…  ({count} pkt)")
            self.var_phase.set("⏳  OCZEKIWANIE")
            self.var_timer.set("--")
            self.var_inst.set("Uruchom idf.py monitor i\nupewnij się że ESP32 wysyła dane.")
            self.after(100, self._tick)
            return

        # ── Pierwsze CSI — zainicjuj sekwencję ──
        if idx == -1:
            with state_lock:
                state["phase_idx"] = 0
                state["phase_start"] = time.time()
            self._announce_phase(0)
            self.after(100, self._tick)
            return

        # ── Bieżąca faza ────────────────────
        name, dur, col, inst = SEQUENCE[idx]
        elapsed = time.time() - state["phase_start"]
        remaining = max(0.0, dur - elapsed)

        self.var_csi.set(
            f"CSI: {count} pkt  |  faza {idx+1}/{len(SEQUENCE)}"
            f"  |  czas całkowity: {self._total_elapsed():.0f}s")
        self.var_phase.set(name)
        self.lbl_phase.config(fg=col)
        self.var_timer.set(f"{int(remaining)+1:02d}")
        self.lbl_timer.config(fg=col)
        self.var_inst.set(inst)

        # Pasek fazy
        frac = max(0.0, min(1.0, remaining / dur))
        self.bar_canvas.coords(self.bar_fill, 0, 0, bar_w * frac, 18)
        self.bar_canvas.itemconfig(self.bar_fill, fill=col)

        # Pasek całości
        total_elapsed = self._total_elapsed()
        total_frac = min(1.0, total_elapsed / TOTAL_SECS)
        self.total_canvas.coords(self.total_fill,
                                 0, 0, tot_w * total_frac, 12)
        self.var_total.set(f"{total_elapsed:.0f} / {TOTAL_SECS} s")

        # Podświetl aktualną fazę w planie
        for i, (dot, lbl, c) in enumerate(self.phase_labels):
            if i < idx:
                dot.config(text="  ✓ ", fg=TEXT_DIM)
                lbl.config(fg=TEXT_DIM)
            elif i == idx:
                dot.config(text="  ▶ ", fg=col)
                lbl.config(fg=col)
            else:
                dot.config(text="  ○ ", fg=TEXT_DIM)
                lbl.config(fg=TEXT_DIM)

        # Przejście do następnej fazy
        if elapsed >= dur:
            next_idx = idx + 1
            if next_idx < len(SEQUENCE):
                with state_lock:
                    state["phase_idx"] = next_idx
                    state["phase_start"] = time.time()
                self._announce_phase(next_idx)
            else:
                self._finish()
                return

        self.after(100, self._tick)

    # ── HELPERS ─────────────────────────────
    def _total_elapsed(self):
        if state["phase_start"] is None:
            return 0
        done = sum(SEQUENCE[i][1] for i in range(state["phase_idx"]))
        cur  = time.time() - state["phase_start"]
        return done + cur

    def _announce_phase(self, idx):
        name, _, _, _ = SEQUENCE[idx]
        marker(name.split("[")[0].strip().replace(" ", "_"))

    def _finish(self):
        marker("RECORDING_STOP")
        self.var_phase.set("✓  ZAKOŃCZONO")
        self.lbl_phase.config(fg=ACCENT_DONE)
        self.var_timer.set("00")
        self.lbl_timer.config(fg=ACCENT_DONE)
        self.var_inst.set("Nagrywanie zakończone.\nMożesz zatrzymać skrypt (Ctrl+C lub ESC).")
        self.bar_canvas.coords(self.bar_fill, 0, 0, 0, 18)
        tot_w = self.total_canvas.winfo_width() or 760
        self.total_canvas.coords(self.total_fill, 0, 0, tot_w, 12)
        self.total_canvas.itemconfig(self.total_fill, fill=ACCENT_DONE)
        self.after(5000, self._quit)

    def _quit(self):
        state["running"] = False
        marker("RECORDING_STOP")
        self.destroy()


# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────
if __name__ == "__main__":
    # Wątek stdin — czyta dane z idf.py monitor
    t = threading.Thread(target=stdin_reader, daemon=True)
    t.start()

    app = App()
    app.mainloop()

    state["running"] = False
    sys.exit(0)