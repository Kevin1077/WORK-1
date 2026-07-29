"""
ui/progress.py — Progress tracking view with charts for Revenue and Order Count
Provides Day, Week, Month, Year filter views using matplotlib embedded in Tkinter.
"""
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

from ui.theme import COLORS, FONTS
from ui.widgets import make_btn
import database as db

try:
    import matplotlib
    matplotlib.use("TkAgg")
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    HAS_MPL = True
except ImportError:
    HAS_MPL = False


class ProgressFrame(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=COLORS["bg"])
        self.app = app
        self._current_period = "month"  # "day" | "week" | "month" | "year"
        self._canvas = None
        self._build()

    def _build(self):
        # Header
        hdr = tk.Frame(self, bg=COLORS["card_bg"])
        hdr.pack(fill="x")
        tk.Label(hdr, text="Progress & Analytics", bg=COLORS["card_bg"],
                 fg=COLORS["accent"], font=FONTS["title"]).pack(side="left", padx=20, pady=14)
        tk.Frame(self, bg=COLORS["border"], height=1).pack(fill="x")

        body = tk.Frame(self, bg=COLORS["bg"])
        body.pack(fill="both", expand=True, padx=24, pady=20)

        # Period selector bar
        bar = tk.Frame(body, bg=COLORS["card_bg"], padx=16, pady=12)
        bar.pack(fill="x", pady=(0, 16))

        tk.Label(bar, text="View Progress By:", bg=COLORS["card_bg"],
                 fg=COLORS["text_dim"], font=FONTS["bold"]).pack(side="left", padx=(0, 16))

        self._btn_day = make_btn(bar, "Day", lambda: self._set_period("day"), "neutral")
        self._btn_day.pack(side="left", padx=(0, 8))

        self._btn_week = make_btn(bar, "Week (12 Weeks)", lambda: self._set_period("week"), "neutral")
        self._btn_week.pack(side="left", padx=(0, 8))

        self._btn_month = make_btn(bar, "Month", lambda: self._set_period("month"), "primary")
        self._btn_month.pack(side="left", padx=(0, 8))

        self._btn_year = make_btn(bar, "Year", lambda: self._set_period("year"), "neutral")
        self._btn_year.pack(side="left", padx=(0, 8))

        make_btn(bar, "🔄 Refresh", self.refresh, "neutral").pack(side="right")

        # Container for graphs
        self._graph_container = tk.Frame(body, bg=COLORS["card_bg"], padx=10, pady=10)
        self._graph_container.pack(fill="both", expand=True)

        if not HAS_MPL:
            tk.Label(
                self._graph_container,
                text="Matplotlib is not installed. Please install matplotlib using:\npip install matplotlib",
                bg=COLORS["card_bg"], fg=COLORS["danger_fg"], font=FONTS["large"],
                justify="center"
            ).pack(expand=True)

    def _set_period(self, period: str):
        self._current_period = period
        # Highlight active button
        btn_map = {
            "day": self._btn_day,
            "week": self._btn_week,
            "month": self._btn_month,
            "year": self._btn_year,
        }
        for p, b in btn_map.items():
            if p == period:
                b.config(bg=COLORS["accent"], fg=COLORS["bg"])
            else:
                b.config(bg=COLORS["btn_neutral"], fg=COLORS["btn_neutral_fg"])
        self.refresh()

    def refresh(self):
        if not HAS_MPL:
            return

        # Fetch data based on current period
        if self._current_period == "day":
            data = db.get_daily_stats(days=30)
            title_suffix = "Last 30 Days"
        elif self._current_period == "week":
            data = db.get_weekly_stats(weeks=12)
            title_suffix = "Last 12 Weeks"
        elif self._current_period == "month":
            data = db.get_monthly_stats(months=12)
            title_suffix = "Last 12 Months"
        else:
            data = db.get_yearly_stats()
            title_suffix = "Yearly"

        self._draw_charts(data, title_suffix)

    def _draw_charts(self, data, title_suffix):
        # Clear existing canvas widget
        if self._canvas:
            self._canvas.get_tk_widget().destroy()
            self._canvas = None

        if not data:
            lbl = tk.Label(
                self._graph_container,
                text=f"No order records available for {title_suffix}.",
                bg=COLORS["card_bg"], fg=COLORS["text_muted"], font=FONTS["large"]
            )
            lbl.pack(expand=True)
            return

        periods = [d["period"] for d in data]
        revenues = [d["revenue"] for d in data]
        counts = [d["order_count"] for d in data]

        fig = Figure(figsize=(10, 5), dpi=100, facecolor=COLORS["card_bg"])

        # Subplot 1: Revenue (Line Chart)
        ax1 = fig.add_subplot(211)
        ax1.set_facecolor(COLORS["card_bg"])
        ax1.plot(periods, revenues, marker="o", color="#080707", linewidth=2, label="Revenue (₹)")
        ax1.set_title(f"Revenue Trend ({title_suffix})", fontsize=11, fontweight="bold", color="#080707")
        ax1.set_ylabel("Revenue (₹)", fontsize=9, color="#080707")
        ax1.grid(True, linestyle="--", alpha=0.5)
        ax1.tick_params(colors="#080707", labelsize=8)
        if len(periods) > 10:
            ax1.set_xticks(range(0, len(periods), max(1, len(periods) // 10)))
        fig.tight_layout()

        # Subplot 2: Order Count (Bar Chart)
        ax2 = fig.add_subplot(212)
        ax2.set_facecolor(COLORS["card_bg"])
        bars = ax2.bar(periods, counts, color="#444444", width=0.5, label="Orders Count")
        ax2.set_title(f"Number of Orders ({title_suffix})", fontsize=11, fontweight="bold", color="#080707")
        ax2.set_xlabel("Time Period", fontsize=9, color="#080707")
        ax2.set_ylabel("Orders Count", fontsize=9, color="#080707")
        ax2.grid(True, linestyle="--", alpha=0.5)
        ax2.tick_params(colors="#080707", labelsize=8)
        if len(periods) > 10:
            ax2.set_xticks(range(0, len(periods), max(1, len(periods) // 10)))

        fig.tight_layout()

        # Embed into Tkinter canvas
        canvas = FigureCanvasTkAgg(fig, master=self._graph_container)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
        self._canvas = canvas
