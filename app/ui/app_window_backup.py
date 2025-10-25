# app/ui/app_window.py
import tkinter as tk
from tkinter import ttk, messagebox

from app.config import JSON_DIR, NUM_QUESTIONS, PASS_CUTOFF, SAFE_CUTOFF, PERF_CUTOFF, DEFAULT_TIMER_MIN
from app.services.loader import load_bank, sample_questions
from app.services.grader import grade, status_from_score, multi_required
from app.utils.labels import LETTERS

from app.ui.views.exam_view import ExamView
from app.ui.widgets.qgrid import QGrid
from app.ui.widgets.explain import ExplainWin

COLOR_BG      = "#e6eff7"
COLOR_PRIMARY = "#2b6aa0"
FONT_HEADER   = ("Segoe UI", 16, "bold")
FONT_TEXT     = ("Segoe UI", 12, "bold")

class QuizApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AWS SAA-C03 Dump")
        self.geometry("1200x700")
        self.minsize(1000, 600)
        self.configure(bg=COLOR_BG)

        # 데이터
        self.bank = load_bank(JSON_DIR)
        if len(self.bank) < NUM_QUESTIONS:
            messagebox.showerror("오류", f"문제은행이 부족합니다. ({len(self.bank)}개)")
            self.destroy(); return
        self.run = sample_questions(self.bank, NUM_QUESTIONS)

        # 상태
        self.index = 0
        self.selected = {q["id"]: set() for q in self.run}
        self.marked   = set()
        self.wrong_ids = set()

        # 타이머
        self.total_seconds = None if DEFAULT_TIMER_MIN is None else int(DEFAULT_TIMER_MIN) * 60

        self._build_ui()
        self._render()
        if self.total_seconds: self._start_timer()

    # ---------- UI 조립 ----------
    def _build_ui(self):
        # 헤더
        header = tk.Frame(self, bg=COLOR_PRIMARY)
        header.pack(fill=tk.X, padx=10, pady=(8,4))
        tk.Label(header, text="[AWS SAA-C03 Dump]", font=("Segoe UI", 18, "bold"),
                 fg="white", bg=COLOR_PRIMARY).pack(side=tk.LEFT)
        self.header_right = tk.Label(header, text="", font=FONT_HEADER, fg="white", bg=COLOR_PRIMARY)
        self.header_right.pack(side=tk.RIGHT)

        root = tk.Frame(self, bg=COLOR_BG)
        root.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)

        # 좌측: 번호 그리드 + 종료
        left = tk.Frame(root, bg=COLOR_BG)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0,10))
        self.qgrid = QGrid(left, total=NUM_QUESTIONS, on_goto=self._goto, cols=4, bg=COLOR_BG)
        self.qgrid.pack()
        tk.Button(left, text="종료", font=FONT_TEXT, bg="#1e3a5f", fg="white",
                  command=self._quit_confirm).pack(pady=(8,0), fill=tk.X)

        # 우측: 문제/보기 뷰
        right = tk.Frame(root, bg=COLOR_BG)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.view = ExamView(right, get_q=self._get_q, get_selected_set=self._get_selected_set,
                             on_select_change=self._on_select_change)
        self.view.pack(fill=tk.BOTH, expand=True)

        # 하단 바
        bottom = tk.Frame(self, bg=COLOR_BG)
        bottom.pack(fill=tk.X, padx=20, pady=(0,10))
        ttk.Button(bottom, text="설명 미리보기", command=self._toggle_explain).pack(side=tk.LEFT)
        nav = tk.Frame(bottom, bg=COLOR_BG); nav.pack(side=tk.RIGHT)
        ttk.Button(nav, text="이전", command=self._prev).pack(side=tk.LEFT, padx=5)
        ttk.Button(nav, text="마크", command=self._toggle_mark).pack(side=tk.LEFT, padx=5)
        ttk.Button(nav, text="다음", command=self._next).pack(side=tk.LEFT, padx=5)
        ttk.Button(nav, text="제출", command=self._submit).pack(side=tk.LEFT, padx=5)

        # 설명창 핸들
        self.exp_win = None

        # 단축키
        self.bind("<Left>",  lambda e: self._prev())
        self.bind("<Right>", lambda e: self._next())
        self.bind("<Return>",lambda e: self._next())

    # ---------- 상태 helpers ----------
    def _get_q(self, idx: int) -> dict: return self.run[idx]
    def _get_selected_set(self, qid: int) -> set[str]: return self.selected[qid]

    # ---------- 렌더 ----------
    def _render(self):
        self.view.render(self.index)
        self._render_header()
        self.qgrid.paint(self.index, self.wrong_ids, [q["id"] for q in self.run])

    def _render_header(self):
        cur = self.index + 1
        timer = ""
        if self.total_seconds is not None:
            m, s = divmod(self.total_seconds, 60)
            timer = f" , {m:02d}:{s:02d}"
        mark = " ★" if self.run[self.index]["id"] in self.marked else ""
        self.header_right.config(text=f"[{cur}/{NUM_QUESTIONS}]{timer}{mark}")

    # ---------- 타이머 ----------
    def _start_timer(self):
        self.after(1000, self._tick)

    def _tick(self):
        if self.total_seconds is None: return
        self.total_seconds -= 1
        if self.total_seconds <= 0:
            self.total_seconds = 0
            self._render_header()
            messagebox.showinfo("시간 종료", "시험 시간이 종료되었습니다. 제출합니다.")
            self._submit(); return
        self._render_header()
        self.after(1000, self._tick)

    # ---------- 이벤트 ----------
    def _on_select_change(self, qid: int, label: str, checked: bool):
        s = self.selected[qid]
        if checked: s.add(label)
        else: s.discard(label)

    def _goto(self, idx: int):
        if 0 <= idx < len(self.run):
            self.index = idx
            self._render()

    def _prev(self):
        if self.index > 0:
            self.index -= 1
            self._render()

    def _next(self):
        q = self.run[self.index]
        picked = self.selected[q["id"]]
        if multi_required(q) and len(picked) == 1:
            messagebox.showwarning("안내", "복수 정답 문제입니다. 다시 선택해주세요.")
            return
        if self.index < len(self.run) - 1:
            self.index += 1
            self._render()

    def _toggle_mark(self):
        qid = self.run[self.index]["id"]
        if qid in self.marked: self.marked.remove(qid)
        else: self.marked.add(qid)
        self._render_header()

    def _toggle_explain(self):
        if self.exp_win and tk.Toplevel.winfo_exists(self.exp_win):
            self.exp_win.destroy(); self.exp_win = None
        else:
            self.exp_win = ExplainWin(self, get_current_q=lambda: self.run[self.index])

    def _quit_confirm(self):
        if messagebox.askyesno("종료", "시험을 종료할까요?"):
            self.destroy()

    # ----------  ----------

    

    # ---------- 제출 ----------
    def _submit(self):
        # 1개만 체크된 복수문항 경고
        pending = [q["id"] for q in self.run if multi_required(q) and len(self.selected[q["id"]]) == 1]
        if pending:
            if not messagebox.askyesno("확인", f"복수정답인데 1개만 선택한 문항이 있습니다. 그래도 제출할까요?\n{pending[:10]}{' ...' if len(pending)>10 else ''}"):
                return

        correct, review = grade(self.run, self.selected)
        self._show_result(correct, review)
        
        '''
        self.wrong_ids = {r["id"] for r in review if not r["correct"]}
        self._render()  # 그리드 색 갱신

        # 결과창 간단 표시
        win = tk.Toplevel(self); win.title("결과"); win.geometry("500x200")
        status = status_from_score(correct, len(self.run), (PASS_CUTOFF, SAFE_CUTOFF, PERF_CUTOFF))
        tk.Label(win, text=f"정답: {correct}/{len(self.run)}  |  {status}",
                 font=("Segoe UI", 14, "bold")).pack(pady=20)
        ttk.Button(win, text="닫기", command=win.destroy).pack()
        '''
    # ----------  ----------
    def _show_result(self, correct, review):
        import tkinter as tk, webbrowser
        from tkinter import ttk

        # self.wrong_ids = {틀린 문제의 id들}
        wrong = [r for r in review if not r["correct"]]
        self.wrong_ids = {r["id"] for r in wrong}

        # 결과(검토) 창
        win = tk.Toplevel(self)
        win.title("검토 화면")
        win.geometry("1200x700")

        # 상단 상태바
        status = (
            "PERFECTO ✅" if correct >= 58 else
            "안정권 ✅"   if correct >= 55 else
            "합격권 ✅"   if correct >= 52 else
            "미달 ❌"
        )

        topbar = tk.Frame(win)
        topbar.pack(fill=tk.X, padx=10, pady=(8,6))

        tk.Label(
            topbar,
            text="[AWS SAA-C03 Dump]",
            font=("Segoe UI", 18, "bold")
        ).pack(side=tk.LEFT)

        tk.Label(
            topbar,
            text=f"  맞힌 문제 수: {correct}   합불 여부: {status}   검토 화면, 응시 시간:[타이머]",
            font=("Segoe UI", 16, "bold")
        ).pack(side=tk.LEFT, padx=10)

        # 본문 전체 프레임
        body = tk.Frame(win)
        body.pack(fill=tk.BOTH, expand=True, padx=14, pady=8)

        # ─────────────────────────
        # 1) 왼쪽: 문제 번호 영역
        # ─────────────────────────
        left = tk.Frame(body)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0,12))

        tk.Label(
            left,
            text="문제영역",
            font=("Segoe UI", 14, "bold")
        ).pack(pady=(0,6))

        grid = tk.Frame(left)
        grid.pack()

        btns = []
        COLOR_BASE  = "#3f6aa8"   # 기본 파란 계열
        COLOR_CURR  = "#1565c0"   # 현재 선택된 문제
        COLOR_WRONG = "#c62828"   # 틀린 문제
        FONT_BTN    = ("Segoe UI", 12, "bold")

        # 현재 몇 번 문제를 보고 있는지
        curr_index = 0

        def paint_buttons(current_idx=None):
            run_ids = [q["id"] for q in self.run]  # 시험에 출제된 문제 id들 순서
            for i, b in enumerate(btns):
                bg = COLOR_BASE
                # 현재 보고 있는 문제면 파랑
                if i == current_idx:
                    bg = COLOR_CURR
                # 틀린 문제면 빨강으로 override
                if i < len(run_ids) and run_ids[i] in self.wrong_ids:
                    bg = COLOR_WRONG
                b.configure(bg=bg)

        def goto_review(idx: int):
            nonlocal curr_index
            curr_index = idx
            render_review_question()
            paint_buttons(curr_index)

        # 버튼(문제 번호들) 생성: 4열 그리드
        cols = 4
        for i in range(len(self.run)):
            b = tk.Button(
                grid,
                text=str(i+1),
                width=4,
                font=FONT_BTN,
                fg="white",
                bg=COLOR_BASE,
                command=lambda k=i: goto_review(k)
            )
            r, c = divmod(i, cols)
            b.grid(row=r, column=c, padx=2, pady=2, sticky="nsew")
            btns.append(b)

        # 종료 버튼 (검토창 닫기)
        tk.Button(
            left,
            text="종료",
            font=FONT_BTN,
            bg="#1e3a5f",
            fg="white",
            command=win.destroy
        ).pack(pady=(8,0), fill=tk.X)

        # ─────────────────────────
        # 2) 오른쪽: 문제 / 해설 영역
        # ─────────────────────────
        right = tk.Frame(body)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 문제 박스
        qbox = tk.Frame(right, bd=1, relief=tk.SOLID, bg="white")
        qbox.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0,6))

        qtitle = tk.Label(
            qbox,
            text="Q1 [id: ]",
            anchor="w",
            font=("Segoe UI", 14, "bold"),
            bg="white",
            fg="#111111"
        )
        qtitle.pack(fill=tk.X, padx=8, pady=(8,6))

        qtext = tk.Text(
            qbox,
            wrap=tk.WORD,
            height=10,
            font=("Segoe UI", 12, "bold"),
            bg="white",
            fg="#111111",
            relief=tk.FLAT
        )
        qtext.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0,8))
        qtext.config(state=tk.DISABLED)

        # 해설 박스
        ebox = tk.Frame(right, bd=1, relief=tk.SOLID, bg="white")
        ebox.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0,6))

        etext = tk.Text(
            ebox,
            wrap=tk.WORD,
            height=10,
            font=("Segoe UI", 12, "bold"),
            bg="white",
            fg="#111111",
            relief=tk.FLAT,
            cursor="arrow"
        )
        etext.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        etext.config(state=tk.DISABLED)

        # ─────────────────────────
        # 3) 현재 선택된 문제 내용을 우측에 뿌리는 함수
        # ─────────────────────────
        def render_review_question():
            q = self.run[curr_index]

            # 문제 부분 채우기
            qtitle.config(text=f"Q{curr_index+1} [id: {q.get('id')}]")

            qtext.config(state=tk.NORMAL)
            qtext.delete("1.0", tk.END)

            title = (q.get("title") or "").strip()
            ctx   = (q.get("context") or "").strip()

            if title:
                qtext.insert(tk.END, title + "\n\n")
            if ctx:
                qtext.insert(tk.END, ctx)

            qtext.config(state=tk.DISABLED)

            # 해설 부분 채우기
            etext.config(state=tk.NORMAL)
            etext.delete("1.0", tk.END)

            my_answers = review[curr_index]["user"]     # 내가 고른 선택지들 (["A","C"] 등)
            correct_ans = review[curr_index]["answer"]  # 정답 선택지들

            ansline = (
                f"정답: {','.join(correct_ans) or '-'}"
                f"   |   제출한 답변: {','.join(my_answers) or '-'}\n"
            )
            etext.insert(tk.END, ansline, ("answer",))

            expl = (q.get("explain") or "").strip()
            etext.insert(
                tk.END,
                "\n" + (expl if expl else "설명 없음") + "\n"
            )

            link = q.get("link")
            if link:
                etext.insert(tk.END, f"\n링크: {link}", ("link",))

                # 파란 하이퍼링크 스타일
                etext.tag_config("link", foreground="#0b66d0", underline=True)

                # 링크 클릭 => 브라우저 열기
                etext.tag_bind(
                    "link", "<Button-1>",
                    lambda e, url=link: webbrowser.open(url)
                )

                # "정답:" 줄(answer 태그) 눌러도 링크로 가게
                etext.tag_bind(
                    "answer", "<Button-1>",
                    lambda e, url=link: webbrowser.open(url)
                )

            etext.tag_config("answer",
                font=("Segoe UI", 12, "bold"),
                foreground="#111111"
            )

            etext.config(state=tk.DISABLED)

        # 초기 상태 표시 + 버튼 색칠
        render_review_question()
        paint_buttons(curr_index)

