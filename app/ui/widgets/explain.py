# app/ui/widgets/explain.py
import tkinter as tk, webbrowser
FONT_TEXT = ("Segoe UI", 12, "bold")

class ExplainWin(tk.Toplevel):
    def __init__(self, master, get_current_q):
        super().__init__(master)
        self.title("설명 미리보기")
        self.geometry("700x400")
        self.get_current_q = get_current_q

        self.text = tk.Text(self, wrap=tk.WORD)
        self.text.pack(fill=tk.BOTH, expand=True)

        self.refresh()

    def refresh(self):
        q = self.get_current_q()
        self.text.config(state=tk.NORMAL)
        self.text.delete("1.0", tk.END)

        ans = ",".join(q.get("answers", [])) or "-"
        self.text.insert(tk.END, f"정답: {ans}\n", ("answer",))

        expl = (q.get("explain") or "").strip()
        self.text.insert(tk.END, "\n" + (expl if expl else "설명 없음") + "\n")

        link = q.get("link")
        if link:
            self.text.insert(tk.END, f"\n링크: {link}", ("link",))
            self.text.tag_config("link", foreground="#0b66d0", underline=True, font=FONT_TEXT)
            self.text.tag_bind("link", "<Button-1>", lambda e, url=link: webbrowser.open(url))
            self.text.tag_bind("answer", "<Button-1>", lambda e, url=link: webbrowser.open(url))

        self.text.tag_config("answer", font=FONT_TEXT, foreground="#111111")
        self.text.config(state=tk.DISABLED)
