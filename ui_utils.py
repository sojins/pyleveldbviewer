# from tkinter import ttk
import ttkbootstrap as ttk

class AutoScrollbar(ttk.Scrollbar):
    """내용이 넘칠 때만 나타나는 스크롤바"""
    def set(self, lo, hi):
        if float(lo) <= 0.0 and float(hi) >= 1.0:
            self.grid_remove()
        else:
            self.grid()
        super().set(lo, hi)
