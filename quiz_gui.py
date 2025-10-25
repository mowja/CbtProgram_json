# quiz_gui.py (Tkinter GUI, AWS SAA-C03 Dump)
# - JSON 폴더(Que)의 Q*~Q*.json에서 문제 로드 → 65문제 랜덤 출제
# - 보기 개수 가변(A..Z), 복수정답 입력 검증(개수 미노출)
# - 결과 요약 + 오답 전체 리뷰(설명/링크)
# - 타이머(옵션), 마킹, 이전/다음/제출
# - PyInstaller --onefile --noconsole 빌드 권장

import json, random, webbrowser, sys, time
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

# ===== 설정 =====
JSON_DIR = Path(r"C:\Users\mowja\CBT_Parser\Que")
NUM_QUESTIONS = 65
PASS_CUTOFF, SAFE_CUTOFF, PERF_CUTOFF = 52, 55, 58
DEFAULT_TIMER_MIN = 100  # 분 단위(100분). None이면 타이머 비활성

LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

# ===== 유틸 =====

def load_bank(json_dir: Path):
    files = sorted(json_dir.glob("Q*~Q*.json"))
    bank = []
    for f in files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            if isinstance(data, list):
                for q in data:
                    if q.get("choices") and q.get("answers"):
                        bank.append(q)
        except Exception as e:
            print(f"[WARN] {f}: {e}")
    return bank


def normalize_user_answer(s: str, max_labels: int):
    if not s: return []
    s = s.strip().upper()
    for ch in [" ", ",", "/", "&", ";", "|", "｜", "、", "，", "／", "＆"]:
        s = s.replace(ch, "")
    out = []
    map_num = {str(i): LETTERS[i-1] for i in range(1, 27)}
    allowed = set(LETTERS[:max_labels])
    for ch in s:
        if ch in allowed:
            out.append(ch)
        elif ch in map_num and map_num[ch] in allowed:
            out.append(map_num[ch])
    # 중복 제거 + 라벨 순서 정렬
    return sorted(set(out), key=lambda x: LETTERS.index(x))


# ===== 메인 앱 =====
class QuizApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AWS SAA-C03 Dump")
        self.geometry("1200x700")
        self.minsize(1000, 600)
        self.configure(bg="#2b6aa0")  # 상단 그라데이션 느낌은 생략, 배경만

        self.json_dir = JSON_DIR
        self.bank = load_bank(self.json_dir)
        if len(self.bank) < NUM_QUESTIONS:
            messagebox.showerror("오류", f"문제은행이 부족합니다. ({len(self.bank)}개)")
            self.destroy(); return

        random.seed()
        self.run = random.sample(self.bank, NUM_QUESTIONS)
        # 사용자 상태
        self.index = 0
        self.selected = {q["id"]: set() for q in self.run}
        self.marked = set()

        # 타이머
        self.total_seconds = None if DEFAULT_TIMER_MIN is None else DEFAULT_TIMER_MIN * 60
        self._timer_running = False

        self._build_ui()
        self._render_question()
        if self.total_seconds:
            self._start_timer()

    # ===== UI 빌드 =====
    def _build_ui(self):
        # 전체 배경
        self.configure(bg="#e6eff7")
        # 헤더
        header = tk.Frame(self, bg="#2b6aa0")
        header.pack(fill=tk.X, padx=10, pady=(8,4))
        tk.Label(header, text="[AWS SAA-C03 Dump]", font=("Segoe UI", 18, "bold"), fg="white", bg="#2b6aa0").pack(side=tk.LEFT)
        self.header_right = tk.Label(header, text="", font=("Segoe UI", 16, "bold"), fg="white", bg="#2b6aa0")
        self.header_right.pack(side=tk.RIGHT)

        # 메인 카드(흰 바탕 + 테두리)
        card = tk.Frame(self, bg="#e6eff7")
        card.pack(fill=tk.BOTH, expand=True, padx=20, pady=6)

        box_style = dict(bd=1, relief=tk.SOLID, bg="#ffffff")

        # 문제 영역
        top = tk.Frame(card, **box_style)
        top.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)

        self.qtitle = tk.Label(top, text="Q1 [id: ]", anchor="w", font=("Segoe UI", 14, "bold"), fg="#0f265c", bg="#ffffff")
        self.qtitle.pack(fill=tk.X, pady=(8,6), padx=8)

        self.qtext = tk.Text(top, height=10, wrap=tk.WORD, font=("Segoe UI", 12), bg="#ffffff", fg="#111111", relief=tk.FLAT)
        self.qtext.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0,8))
        self.qtext.config(state=tk.DISABLED)

        # 보기 영역
        mid = tk.Frame(card, **box_style)
        mid.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0,6))

        self.choices_frame = tk.Frame(mid, bg="#ffffff")
        self.choices_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # 하단 버튼 바
        bottom = tk.Frame(self, bg="#e6eff7")
        bottom.pack(fill=tk.X, padx=20, pady=(0,10))

        self.btn_explain = ttk.Button(bottom, text="설명 미리보기", command=self._toggle_explain)
        self.btn_explain.pack(side=tk.LEFT)

        nav = tk.Frame(bottom, bg="#e6eff7")
        nav.pack(side=tk.RIGHT)
        ttk.Button(nav, text="이전", command=self._prev).pack(side=tk.LEFT, padx=5)
        ttk.Button(nav, text="마크", command=self._toggle_mark).pack(side=tk.LEFT, padx=5)
        ttk.Button(nav, text="다음", command=self._next).pack(side=tk.LEFT, padx=5)
        ttk.Button(nav, text="제출", command=self._submit).pack(side=tk.LEFT, padx=5)

        # 설명 패널(토글)
        self.explain_win = None

        # 키 바인딩
        self.bind("<Left>", lambda e: self._prev())
        self.bind("<Right>", lambda e: self._next())
        self.bind("<Return>", lambda e: self._next())

    # ===== 렌더 =====

    def _render_header(self):
        cur = self.index + 1
        timer = ""
        if self.total_seconds is not None:
            m, s = divmod(self.total_seconds, 60)
            timer = f" , {m:02d}:{s:02d}"
        mark = " ★" if self.run[self.index]["id"] in self.marked else ""
        self.header_right.config(text=f"[{cur}/{NUM_QUESTIONS}] {timer}{mark}")

    def _render_question(self):
        q = self.run[self.index]
        # 제목/지문
        self.qtitle.config(text=f"Q{self.index+1} [id: {q.get('id')}]")
        self.qtext.config(state=tk.NORMAL)
        self.qtext.delete("1.0", tk.END)
        title = (q.get("title") or "").strip()
        context = (q.get("context") or "").strip()
        if title:
            self.qtext.insert(tk.END, title + "\n\n")
        if context:
            self.qtext.insert(tk.END, context)
        self.qtext.config(state=tk.DISABLED)

        # 보기 체크박스 재생성
        for w in list(self.choices_frame.children.values()):
            w.destroy()
        choices = q.get("choices", [])
        self.choice_vars = []
        labels = [LETTERS[i] for i in range(len(choices))]
        for i, txt in enumerate(choices):
            var = tk.BooleanVar(value=(LETTERS[i] in self.selected[q["id"]]))
            cb = ttk.Checkbutton(self.choices_frame, text=f" {labels[i]}. {txt}", variable=var, command=self._on_choice_change)
            cb.pack(anchor="w", pady=2)
            self.choice_vars.append((labels[i], var))

        self._render_header()

        # 설명창 열려있으면 갱신
        if self.explain_win and tk.Toplevel.winfo_exists(self.explain_win):
            self._refresh_explain()

    def _on_choice_change(self):
        q = self.run[self.index]
        picked = {lbl for lbl, v in self.choice_vars if v.get()}
        # 허용 라벨 범위 내에서 저장
        self.selected[q["id"]] = set(sorted(picked, key=lambda x: LETTERS.index(x)))

    # ===== 타이머 =====
    def _start_timer(self):
        if self._timer_running:
            return
        self._timer_running = True
        self.after(1000, self._tick)

    def _tick(self):
        if self.total_seconds is None:
            return
        self.total_seconds -= 1
        if self.total_seconds <= 0:
            self.total_seconds = 0
            self._render_header()
            messagebox.showinfo("시간 종료", "시험 시간이 종료되었습니다. 제출합니다.")
            self._submit()
            return
        self._render_header()
        self.after(1000, self._tick)

    # ===== 네비 =====
    def _prev(self):
        if self.index > 0:
            self.index -= 1
            self._render_question()

    def _next(self):
        # 복수정답인데 '한 개만' 체크 시에만 진행 차단(0개는 허용)
        q = self.run[self.index]
        need_multi = len(set(q.get("answers", []))) >= 2
        picked = self.selected[q["id"]]
        if need_multi and len(picked) == 1:
            messagebox.showwarning("안내", "복수 정답 문제입니다. 다시 선택해주세요.")
            return
        if self.index < NUM_QUESTIONS - 1:
            self.index += 1
            self._render_question()

    def _toggle_mark(self):
        qid = self.run[self.index]["id"]
        if qid in self.marked:
            self.marked.remove(qid)
        else:
            self.marked.add(qid)
        self._render_header()

    # ===== 설명/링크 =====
    def _toggle_explain(self):
        if self.explain_win and tk.Toplevel.winfo_exists(self.explain_win):
            self.explain_win.destroy(); self.explain_win = None
        else:
            self._open_explain()

    def _open_explain(self):
        self.explain_win = tk.Toplevel(self)
        self.explain_win.title("설명 미리보기")
        self.explain_win.geometry("700x400")

        self.exp_text = tk.Text(self.explain_win, wrap=tk.WORD)
        self.exp_text.pack(fill=tk.BOTH, expand=True)

        btns = tk.Frame(self.explain_win)
        btns.pack(fill=tk.X)
        ttk.Button(btns, text="링크 열기", command=self._open_link).pack(side=tk.RIGHT, padx=5, pady=4)
        self._refresh_explain()

    def _refresh_explain(self):
        q = self.run[self.index]
        self.exp_text.config(state=tk.NORMAL)
        self.exp_text.delete("1.0", tk.END)
        expl = (q.get("explain") or "").strip()
        if expl:
            self.exp_text.insert(tk.END, expl)
        else:
            self.exp_text.insert(tk.END, "설명 없음")
        if q.get("link"):
            self.exp_text.insert(tk.END, f"링크: {q['link']}")
        self.exp_text.config(state=tk.DISABLED)

    def _open_link(self):
        q = self.run[self.index]
        if q.get("link"):
            webbrowser.open(q["link"]) 

    # ===== 채점/제출 =====
    def _submit(self):
        # 남은 문항 검사: 복수정답인데 한 개만 선택된 문항
        pending = []
        for q in self.run:
            need_multi = len(set(q.get("answers", []))) >= 2
            picked = self.selected[q["id"]]
            if need_multi and len(picked) < 2:
                pending.append(q["id"])
        if pending:
            if not messagebox.askyesno("확인", f"복수정답인데 1개만 선택한 문항이 있습니다. 그래도 제출할까요?\n{pending[:10]}{' ...' if len(pending)>10 else ''}"):
                return

        correct = 0
        review = []
        for q in self.run:
            ca = set(q.get("answers", []))
            ua = set(self.selected[q["id"]])
            ok = (ua == ca)
            if ok: correct += 1
            review.append({
                "id": q.get("id"),
                "title": q.get("title", "").strip(),
                "correct": ok,
                "user": sorted(list(ua), key=lambda x: LETTERS.index(x)),
                "answer": sorted(list(ca), key=lambda x: LETTERS.index(x)),
            })

        # 결과 창
        self._show_result(correct, review)

    def _show_result(self, correct, review):
        win = tk.Toplevel(self)
        win.title("결과")
        win.geometry("900x600")

        # 요약
        summary = tk.Frame(win)
        summary.pack(fill=tk.X, padx=10, pady=6)
        status = "미달 ❌"
        if correct >= PERF_CUTOFF: status = "PERFECTO ✅"
        elif correct >= SAFE_CUTOFF: status = "안정권 ✅"
        elif correct >= PASS_CUTOFF: status = "합격권 ✅"
        tk.Label(summary, text=f"정답: {correct}/{NUM_QUESTIONS}  |  {status}", font=("Segoe UI", 14, "bold")).pack(side=tk.LEFT)

        # 오답 리스트 + 상세
        body = tk.PanedWindow(win, sashrelief=tk.RAISED, sashwidth=6)
        body.pack(fill=tk.BOTH, expand=True)

        wrong = [r for r in review if not r["correct"]]
        left = tk.Frame(body)
        right = tk.Frame(body)
        body.add(left, width=350)
        body.add(right)

        cols = ("id", "user", "answer")
        tree = ttk.Treeview(left, columns=cols, show="headings")
        for c in cols:
            tree.heading(c, text=c)
        tree.pack(fill=tk.BOTH, expand=True)
        for r in wrong:
            tree.insert("", tk.END, values=(r["id"], ",".join(r["user"]), ",".join(r["answer"])))

        detail = tk.Text(right, wrap=tk.WORD)
        detail.pack(fill=tk.BOTH, expand=True)

        def on_sel(evt=None):
            sel = tree.selection()
            if not sel:
                return
            vals = tree.item(sel[0], "values")
            qid = int(vals[0])
            qobj = next((q for q in self.run if q.get("id") == qid), None)
            if not qobj: return
            detail.config(state=tk.NORMAL)
            detail.delete("1.0", tk.END)
            detail.insert(tk.END, f"ID {qobj['id']}\n\n")
            detail.insert(tk.END, (qobj.get("title") or "") + "\n\n")
            if qobj.get("context"):
                detail.insert(tk.END, qobj["context"] + "\n\n")
            detail.insert(tk.END, f"정답: {','.join(qobj.get('answers', []))}\n")
            picked = self.selected[qobj['id']]
            detail.insert(tk.END, f"내 답: {','.join(sorted(list(picked), key=lambda x: LETTERS.index(x)))}\n\n")
            if qobj.get("explain"):
                detail.insert(tk.END, "설명:\n" + qobj["explain"] + "\n\n")
            if qobj.get("link"):
                detail.insert(tk.END, f"링크: {qobj['link']}")
            detail.config(state=tk.DISABLED)
        tree.bind("<<TreeviewSelect>>", on_sel)
        if wrong:
            tree.selection_set(tree.get_children()[0]); on_sel()

        # 저장 버튼
        btns = tk.Frame(win)
        btns.pack(fill=tk.X)
        def save_session():
            out = self.json_dir / "last_session_result.json"
            payload = {
                "correct": correct,
                "total": NUM_QUESTIONS,
                "review": review,
            }
            out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            messagebox.showinfo("저장", f"세션 결과 저장: {out}")
        ttk.Button(btns, text="세션 저장", command=save_session).pack(side=tk.RIGHT, padx=8, pady=6)


if __name__ == "__main__":
    try:
        app = QuizApp()
        app.mainloop()
    except Exception as e:
        import traceback
        traceback.print_exc()
        messagebox.showerror("오류", str(e))
