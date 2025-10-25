# app/ui/widgets/qgrid.py
import tkinter as tk

COLOR_CURR  = "#1565c0"
COLOR_WRONG = "#c62828"
COLOR_BASE  = "#3f6aa8"
FONT_TEXT   = ("Segoe UI", 12, "bold")

class QGrid(tk.Frame):
    def __init__(self, master, total, on_goto, cols=4, **kwargs):
        super().__init__(master, **kwargs)
        self.total = total
        self.on_goto = on_goto
        self.cols = cols
        self.btns = []
        wrap = tk.Frame(self, bg=self["bg"])
        wrap.pack()
        for i in range(total):
            b = tk.Button(wrap, text=str(i+1), width=4, font=FONT_TEXT,
                          bg=COLOR_BASE, fg="white",
                          command=lambda idx=i: self.on_goto(idx))
            r, c = divmod(i, cols)
            b.grid(row=r, column=c, padx=2, pady=2, sticky="nsew")
            self.btns.append(b)

    def paint(self, current_index: int, wrong_ids: set[int], run_ids: list[int]):
        for i, b in enumerate(self.btns):
            bg = COLOR_BASE
            if i == current_index:
                bg = COLOR_CURR
            if i < len(run_ids) and run_ids[i] in wrong_ids:
                bg = COLOR_WRONG
            b.configure(bg=bg)
