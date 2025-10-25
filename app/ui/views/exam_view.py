# app/ui/views/exam_view.py
import tkinter as tk
from tkinter import ttk

from app.utils.labels import LETTERS, labels_for_choices
FONT_TITLE = ("Segoe UI", 14, "bold")
FONT_TEXT  = ("Segoe UI", 12, "bold")
COLOR_TEXT = "#111111"
COLOR_BG   = "#e6eff7"
COLOR_CARD = "#ffffff"

class ExamView(tk.Frame):
    """문제/보기/헤더를 렌더하는 뷰. 상태는 상위(QuizApp)가 들고 있고,
       콜백을 통해 선택 변경/이동을 알림."""
    def __init__(self, master, get_q, get_selected_set, on_select_change):
        super().__init__(master, bg=COLOR_BG)
        self.get_q = get_q
        self.get_selected_set = get_selected_set
        self.on_select_change = on_select_change

        box_style = dict(bd=1, relief=tk.SOLID, bg=COLOR_CARD)

        # 문제 영역
        top = tk.Frame(self, **box_style)
        top.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)
        self.qtitle = tk.Label(top, text="Q1 [id: ]", anchor="w", font=FONT_TITLE, fg=COLOR_TEXT, bg=COLOR_CARD)
        self.qtitle.pack(fill=tk.X, pady=(8,6), padx=8)
        self.qtext = tk.Text(top, height=10, wrap=tk.WORD, font=FONT_TEXT, bg=COLOR_CARD, fg=COLOR_TEXT, relief=tk.FLAT)
        self.qtext.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0,8))
        self.qtext.config(state=tk.DISABLED)

        # 보기 영역
        mid = tk.Frame(self, **box_style)
        mid.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0,6))
        self.choices_frame = tk.Frame(mid, bg=COLOR_CARD)
        self.choices_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # 하단 버튼 바는 상위에서 구성

    def render(self, index: int):
        q = self.get_q(index)
        # 제목/지문
        self.qtitle.config(text=f"Q{index+1} [id: {q.get('id')}]")
        self.qtext.config(state=tk.NORMAL)
        self.qtext.delete("1.0", tk.END)
        title = (q.get("title") or "").strip()
        ctx   = (q.get("context") or "").strip()
        if title: self.qtext.insert(tk.END, title + "\n\n")
        if ctx:   self.qtext.insert(tk.END, ctx)
        self.qtext.config(state=tk.DISABLED)

        # 보기
        for w in list(self.choices_frame.children.values()):
            w.destroy()
        choices = q.get("choices", [])
        labels  = labels_for_choices(len(choices))
        self.choice_vars = []
        picked_set = self.get_selected_set(q["id"])

        for i, txt in enumerate(choices):
            var = tk.BooleanVar(value=(LETTERS[i] in picked_set))
            cb = ttk.Checkbutton(self.choices_frame, text=f" {labels[i]}. {txt}", variable=var,
                                 command=lambda L=labels[i], V=var, QID=q["id"]: self.on_select_change(QID, L, V.get()))
            cb.pack(anchor="w", pady=2)
            self.choice_vars.append((labels[i], var))
