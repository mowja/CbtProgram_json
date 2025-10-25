import tkinter as tk
from tkinter import messagebox
import webbrowser

from app.config import (
    JSON_DIR,
    NUM_QUESTIONS,
    PASS_CUTOFF,
    SAFE_CUTOFF,
    PERF_CUTOFF,
    DEFAULT_TIMER_MIN,
)
from app.services.loader import load_bank, sample_questions
from app.services.grader import grade, multi_required
from app.utils.labels import LETTERS, labels_for_choices


# ===== 공통 스타일 =====
FONT_BTN    = ("Malgun Gothic", 12, "bold")
FONT_TEXT   = ("Malgun Gothic", 12, "bold")
FONT_TITLE  = ("Malgun Gothic", 14, "bold")
FONT_HEAD16 = ("Malgun Gothic", 16, "bold")
FONT_HEAD18 = ("Malgun Gothic", 18, "bold")
COLOR_TEXT  = "#111111"

HEADER_BG   = "#1f4f80"   # 파란 헤더 배경
HEADER_FG   = "white"

PANEL_BG     = "#ffffff"
PANEL_BORDER = "#1c2a44"

BTN_BG      = "#1e3a5f"
BTN_FG      = "white"

# 번호패널 색들
NUM_BASE_BG   = "#3f6aa8"   # 기본 파랑 배경
NUM_WRONG_BG  = "#c62828"   # 틀린 문제 빨강 배경
NUM_FG        = "white"     # 기본 글자색
NUM_MARK_FG   = "#ffd900"   # 마크된 문제 글자색(노란색)


class QuizApp(tk.Tk):
    def __init__(self):
        super().__init__()

        # ------------------------
        # 윈도우 기본 세팅
        # ------------------------
        self.title("AWS SAA-C03 Dump")
        self.geometry("1600x900")
        self.minsize(1300, 730)
        self.configure(bg="#dbe7f5")  # 연한 블루/그레이 톤 배경

        # ------------------------
        # 데이터 로딩
        # ------------------------
        self.bank = load_bank(JSON_DIR)
        if len(self.bank) < NUM_QUESTIONS:
            messagebox.showerror("오류", f"문제은행이 부족합니다. ({len(self.bank)}개)")
            self.destroy()
            return
        self.run = sample_questions(self.bank, NUM_QUESTIONS)

        # ------------------------
        # 상태값
        # ------------------------
        self.index = 0  # 현재 문제 idx
        self.selected = {q["id"]: set() for q in self.run}  # 사용자가 고른 보기들
        self.marked = set()     # 마크(★)된 문제 id
        self.wrong_ids = set()  # 제출 후 틀린 문제 id
        self.review_win = None  # 제출 후 검토창 핸들

        # 타이머 (카운트다운)
        self.start_total_seconds = (
            int(DEFAULT_TIMER_MIN) * 60 if DEFAULT_TIMER_MIN is not None else None
        )
        self.total_seconds = self.start_total_seconds

        # ------------------------
        # UI 구성
        # ------------------------
        self._build_ui()
        self._render_question()

        if self.total_seconds is not None:
            self._start_timer()

    # ------------------------------------------------------------------
    # UI 빌드 (시험 진행 화면)
    # ------------------------------------------------------------------
    def _build_ui(self):
        # 헤더 바 (상단 파란 띠)
        header = tk.Frame(self, bg=HEADER_BG)
        header.pack(fill=tk.X, padx=10, pady=(8,4))

        tk.Label(
            header,
            text="[AWS SAA-C03 Dump]",
            font=FONT_HEAD18,
            fg=HEADER_FG,
            bg=HEADER_BG,
        ).pack(side=tk.LEFT)

        self.header_right = tk.Label(
            header,
            text="",
            font=FONT_HEAD16,
            fg=HEADER_FG,
            bg=HEADER_BG,
        )
        self.header_right.pack(side=tk.RIGHT)

        # 메인 카드 영역 (문제/보기)
        card = tk.Frame(self, bg="#dbe7f5")
        card.pack(fill=tk.BOTH, expand=True, padx=20, pady=6)

        # 문제 영역(위쪽 흰 패널)
        self.qpanel = tk.Frame(
            card,
            bg=PANEL_BG,
            bd=2,
            relief=tk.GROOVE,
            highlightthickness=2,
            highlightbackground=PANEL_BORDER,
            highlightcolor=PANEL_BORDER,
        )
        self.qpanel.pack(fill=tk.BOTH, expand=False, padx=8, pady=6)

        self.qtitle = tk.Label(
            self.qpanel,
            text="Q1 [id: ]",
            anchor="w",
            font=FONT_TITLE,
            fg=COLOR_TEXT,
            bg=PANEL_BG,
        )
        self.qtitle.pack(fill=tk.X, padx=8, pady=(8,4))

        self.qtext = tk.Text(
            self.qpanel,
            wrap=tk.WORD,
            height=10,
            font=FONT_TEXT,
            bg=PANEL_BG,
            fg=COLOR_TEXT,
            relief=tk.FLAT,
        )
        self.qtext.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0,8))
        self.qtext.config(state=tk.DISABLED)

        # 보기 영역(아래쪽 흰 패널)
        self.cho_panel = tk.Frame(
            card,
            bg=PANEL_BG,
            bd=2,
            relief=tk.GROOVE,
            highlightthickness=2,
            highlightbackground=PANEL_BORDER,
            highlightcolor=PANEL_BORDER,
        )
        self.cho_panel.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0,6))

        # 보기들 담을 frame
        self.choices_frame = tk.Frame(self.cho_panel, bg=PANEL_BG)
        self.choices_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # 하단 네비게이션 바
        footer = tk.Frame(self, bg="#dbe7f5")
        footer.pack(fill=tk.X, padx=20, pady=(0,10))

        # 좌측: 설명 미리보기
        self.btn_explain = tk.Button(
            footer,
            text="설명 미리보기",
            font=FONT_BTN,
            bg=BTN_BG,
            fg=BTN_FG,
            command=self._toggle_explain,
        )
        self.btn_explain.pack(side=tk.LEFT)

        # 우측: 이전/마크/다음/제출
        nav = tk.Frame(footer, bg="#dbe7f5")
        nav.pack(side=tk.RIGHT)

        tk.Button(
            nav,
            text="이전",
            font=FONT_BTN,
            bg=BTN_BG,
            fg=BTN_FG,
            width=6,
            command=self._prev,
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            nav,
            text="마크",
            font=FONT_BTN,
            bg=BTN_BG,
            fg=BTN_FG,
            width=6,
            command=self._toggle_mark,
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            nav,
            text="다음",
            font=FONT_BTN,
            bg=BTN_BG,
            fg=BTN_FG,
            width=6,
            command=self._next,
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            nav,
            text="제출",
            font=FONT_BTN,
            bg=BTN_BG,
            fg=BTN_FG,
            width=6,
            command=self._submit,
        ).pack(side=tk.LEFT, padx=5)

        # 설명창 핸들
        self.explain_win = None

        # 단축키: ← → Enter
        self.bind("<Left>",  lambda e: self._prev())
        self.bind("<Right>", lambda e: self._next())
        self.bind("<Return>",lambda e: self._next())

    # ------------------------------------------------------------------
    # 현재 문제 화면 렌더
    # ------------------------------------------------------------------
    def _render_header(self):
        cur = self.index + 1
        timer_text = ""
        if self.total_seconds is not None:
            m, s = divmod(self.total_seconds, 60)
            timer_text = f", {m:02d}:{s:02d}"
        mark = " ★" if (self.run[self.index]["id"] in self.marked) else ""
        self.header_right.config(
            text=f"[{cur}/{NUM_QUESTIONS}]{timer_text}{mark}"
        )

    def _render_question(self):
        q = self.run[self.index]

        # 제목/본문
        self.qtitle.config(text=f"Q{self.index+1} [id: {q.get('id')}]")
        self.qtext.config(state=tk.NORMAL)
        self.qtext.delete("1.0", tk.END)
        title   = (q.get("title") or "").strip()
        context = (q.get("context") or "").strip()
        if title:
            self.qtext.insert(tk.END, title + "\n\n")
        if context:
            self.qtext.insert(tk.END, context)
        self.qtext.config(state=tk.DISABLED)

        # 보기 다시 그림
        for w in list(self.choices_frame.children.values()):
            w.destroy()

        self.choice_vars = []
        choices = q.get("choices", [])
        labels  = labels_for_choices(len(choices))

        for i, txt in enumerate(choices):
            row = tk.Frame(self.choices_frame, bg=PANEL_BG)
            row.pack(fill=tk.X, anchor="w", pady=4)

            var = tk.BooleanVar(
                value=(LETTERS[i] in self.selected[q["id"]])
            )
            self.choice_vars.append((labels[i], var))

            cb = tk.Checkbutton(
                row,
                bg=PANEL_BG,
                activebackground=PANEL_BG,
                variable=var,
                command=self._on_choice_change,
            )
            cb.pack(side=tk.LEFT, anchor="n", padx=(0,6))

            # 긴 보기 줄바꿈 라벨
            lbl = tk.Label(
                row,
                text=f"{labels[i]}. {txt}",
                font=FONT_TEXT,
                fg=COLOR_TEXT,
                bg=PANEL_BG,
                justify="left",
                anchor="w",
                wraplength=1000,
            )
            lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self._render_header()

        # 설명창 열려있으면 내용도 갱신
        if self.explain_win and tk.Toplevel.winfo_exists(self.explain_win):
            self._refresh_explain()

    def _on_choice_change(self):
        q = self.run[self.index]
        picked = {
            lbl for (lbl, v) in self.choice_vars if v.get()
        }
        # 정렬 유지 (A,B,C...)
        self.selected[q["id"]] = set(
            sorted(picked, key=lambda x: LETTERS.index(x))
        )

    # ------------------------------------------------------------------
    # 타이머
    # ------------------------------------------------------------------
    def _start_timer(self):
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

    # ------------------------------------------------------------------
    # 네비게이션
    # ------------------------------------------------------------------
    def _prev(self):
        if self.index > 0:
            self.index -= 1
            self._render_question()

    def _next(self):
        q = self.run[self.index]
        picked = self.selected[q["id"]]

        # 복수 정답 문제인데 1개만 찍은 상태로 넘어가려 하면 막기
        if multi_required(q) and len(picked) == 1:
            messagebox.showwarning(
                "안내", "복수 정답 문제입니다. 다시 선택해주세요."
            )
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

    # ------------------------------------------------------------------
    # 설명 미리보기
    # ------------------------------------------------------------------
    def _toggle_explain(self):
        if self.explain_win and tk.Toplevel.winfo_exists(self.explain_win):
            self.explain_win.destroy()
            self.explain_win = None
        else:
            self._open_explain()

    def _open_explain(self):
        self.explain_win = tk.Toplevel(self)
        self.explain_win.title("설명 미리보기")
        self.explain_win.geometry("1600x900")

        self.exp_text = tk.Text(
            self.explain_win,
            wrap=tk.WORD,
            font=FONT_TEXT,
            fg=COLOR_TEXT,
            bg="white",
        )
        self.exp_text.pack(fill=tk.BOTH, expand=True)

        btns = tk.Frame(self.explain_win)
        btns.pack(fill=tk.X)

        tk.Button(
            btns,
            text="링크 열기",
            font=FONT_BTN,
            bg=BTN_BG,
            fg=BTN_FG,
            command=self._open_link,
        ).pack(side=tk.RIGHT, padx=5, pady=4)

        self._refresh_explain()

    def _refresh_explain(self):
        q = self.run[self.index]
        self.exp_text.config(state=tk.NORMAL)
        self.exp_text.delete("1.0", tk.END)

        # 보기 맵 (A → 해당 보기 텍스트)
        choices = q.get("choices", [])
        labels  = labels_for_choices(len(choices))  # ["A","B","C","D",...]
        choice_map = {labels[i]: choices[i] for i in range(len(choices))}

        # 정답 리스트 (예: ["A","C"])
        answers = q.get("answers", [])

        # 1) 정답 섹션
        if answers:
            self.exp_text.insert(tk.END, "정답:\n", "answer_head")
            for letter in answers:
                body = choice_map.get(letter, "")
                # "A. <보기 전체>" 형태로 줄단위 출력
                self.exp_text.insert(tk.END, f"{letter}. {body}\n", "answer_body")
            self.exp_text.insert(tk.END, "\n")
        else:
            self.exp_text.insert(tk.END, "정답: (정보 없음)\n\n", "answer_head")

        # 2) 해설(설명)
        expl = (q.get("explain") or "").strip()
        if expl:
            self.exp_text.insert(tk.END, "설명:\n", "answer_head")
            self.exp_text.insert(tk.END, expl + "\n")
        else:
            self.exp_text.insert(tk.END, "설명:\n설명 없음\n")

        # 3) 링크 (단순 표시만, 클릭 없음)
        link = q.get("link")
        if link:
            self.exp_text.insert(tk.END, "\n링크: " + link)

        # 태그 스타일(굵게/색 등)은 여기서 필요한 만큼만
        self.exp_text.tag_config(
            "answer_head",
            font=FONT_TEXT,
            foreground=COLOR_TEXT,
        )
        self.exp_text.tag_config(
            "answer_body",
            font=FONT_TEXT,
            foreground=COLOR_TEXT,
        )

        self.exp_text.config(state=tk.DISABLED)


    def _open_link(self):
        q = self.run[self.index]
        if q.get("link"):
            webbrowser.open(q["link"])

    # ------------------------------------------------------------------
    # 제출 & 검토 화면
    # ------------------------------------------------------------------
    def _submit(self):
        # 복수정답인데 1개만 찍은 문제들 경고
        pending = []
        for q in self.run:
            if multi_required(q) and len(self.selected[q["id"]]) == 1:
                pending.append(q["id"])
        if pending:
            ok = messagebox.askyesno(
                "확인",
                "복수정답인데 1개만 선택한 문항이 있습니다. "
                "그래도 제출할까요?\n"
                f"{pending[:10]}{' ...' if len(pending)>10 else ''}"
            )
            if not ok:
                return

        correct, review = grade(self.run, self.selected)

        # 응시 시간 계산
        if self.start_total_seconds is None:
            used_display = "N/A"
        else:
            used = self.start_total_seconds - self.total_seconds
            if used < 0:
                used = 0
            m, s = divmod(used, 60)
            used_display = f"{m}분 {s:02d}초"

        self._show_result(correct, review, used_display)

    def _show_result(self, correct, review, used_time_text):
        """
        제출 후 뜨는 '검토 화면'.
        - 창 크기 기본 1300x800
        - 상단바에 응시 시간 표시
        - 왼쪽 번호: 마크된 문제는 숫자만 노란색, 틀린 문제는 빨강 배경
        - '현재 보고중인 문제' 색 강조 없음
        - 종료 버튼 누르면 시험도 같이 종료
        - 해설 텍스트에 '정답: A. ... / 제출한 답변: ...' 출력
        - 링크 클릭 제거
        """
        # 틀린 문제 id 추출
        wrong = [r for r in review if not r["correct"]]
        self.wrong_ids = {r["id"] for r in wrong}
        if self.review_win is not None and tk.Toplevel.winfo_exists(self.review_win):
            try:
                self.review_win.destroy()
            except:
                pass
            self.review_win = None

        win = tk.Toplevel(self)
        self.review_win = win

        win.title("검토 화면")
        win.geometry("1600x900")
        win.minsize(1300, 730)

        status_text = (
            "PERFECTO ✅" if correct >= PERF_CUTOFF else
            "안정권 ✅"   if correct >= SAFE_CUTOFF else
            "합격권 ✅"   if correct >= PASS_CUTOFF else
            "미달 ❌"
        )

        # 종료(시험 전체 종료) 함수
        def _quit_all():
            # 현재 열려 있는 review_win 정리
            try:
                if self.review_win is not None and tk.Toplevel.winfo_exists(self.review_win):
                    self.review_win.destroy()
            except:
                pass
            
            # 메인 시험창 종료
            self.destroy()

        # 상단 바
        topbar = tk.Frame(win)
        topbar.pack(fill=tk.X, padx=10, pady=(8,6))

        tk.Label(
            topbar,
            text="[AWS SAA-C03 Dump]",
            font=FONT_HEAD18,
        ).pack(side=tk.LEFT)

        tk.Label(
            topbar,
            text=(
                f"  맞힌 문제 수: {correct}   "
                f"합불 여부: {status_text}   "
                f"검토 화면, 응시 시간:{used_time_text}"
            ),
            font=FONT_HEAD16,
        ).pack(side=tk.LEFT, padx=10)

        # 전체 본문: 왼쪽 번호패널 / 오른쪽 문제+해설
        body = tk.Frame(win)
        body.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)

        # -------------------------
        # 왼쪽 번호 패널
        # -------------------------
        left = tk.Frame(body, bg="#efefef")
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0,12))

        tk.Label(
            left,
            text="문제영역",
            font=FONT_TITLE,
            bg="#efefef",
        ).pack(pady=(0,6))

        btns = []
        curr_index = 0  # 현재 표시 중인 문제 인덱스

        # 버튼 색칠 로직 (마크: 글자만 노란색 / 틀린문제: 배경 빨강)
        def paint_buttons():
            for i, b in enumerate(btns):
                qid = self.run[i]["id"]

                bg = NUM_BASE_BG   # 기본 파랑 배경
                fg = NUM_FG       # 기본 흰 글씨

                # 틀린 문제는 빨강 배경 우선
                if qid in self.wrong_ids:
                    bg = NUM_WRONG_BG
                    fg = NUM_FG  # 흰색 유지

                # 마크된 문제는 글자를 노란색으로
                if qid in self.marked:
                    fg = NUM_MARK_FG

                # 현재 문제 강조는 안함 (요청사항)

                b.config(bg=bg, fg=fg)

        def goto_review(idx):
            nonlocal curr_index
            curr_index = idx
            render_review_question()
            paint_buttons()

        cols = 4
        grid_frame = tk.Frame(left, bg="#efefef")
        grid_frame.pack()

        for i in range(len(self.run)):
            b = tk.Button(
                grid_frame,
                text=str(i+1),
                width=4,
                font=FONT_BTN,
                bg=NUM_BASE_BG,
                fg=NUM_FG,
                command=lambda k=i: goto_review(k),
            )
            r, c = divmod(i, cols)
            b.grid(row=r, column=c, padx=2, pady=2, sticky="nsew")
            btns.append(b)

        # 종료 버튼: 검토창+시험창 모두 종료
        tk.Button(
            left,
            text="종료",
            font=FONT_BTN,
            bg=BTN_BG,
            fg=BTN_FG,
            command=_quit_all,
        ).pack(pady=(8,0), fill=tk.X)

        # -------------------------
        # 오른쪽 문제 / 해설 영역
        # -------------------------
        right = tk.Frame(body)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 문제 영역 박스
        qbox = tk.Frame(right, bg="white", bd=1, relief=tk.SOLID)
        qbox.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0,6))

        qtitle = tk.Label(
            qbox,
            text="Q1 [id: ]",
            anchor="w",
            font=FONT_TITLE,
            bg="white",
            fg=COLOR_TEXT,
        )
        qtitle.pack(fill=tk.X, padx=8, pady=(8,6))

        qtext = tk.Text(
            qbox,
            wrap=tk.WORD,
            height=10,
            font=FONT_TEXT,
            bg="white",
            fg=COLOR_TEXT,
            relief=tk.FLAT,
        )
        qtext.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0,8))
        qtext.config(state=tk.DISABLED)

        # 해설 영역 박스
        ebox = tk.Frame(right, bg="white", bd=1, relief=tk.SOLID)
        ebox.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0,6))

        etext = tk.Text(
            ebox,
            wrap=tk.WORD,
            height=12,
            font=FONT_TEXT,
            bg="white",
            fg=COLOR_TEXT,
            relief=tk.FLAT,
        )
        etext.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        etext.config(state=tk.DISABLED)

        def render_review_question():
            q = self.run[curr_index]
            q_id = q.get("id")

            # 문제 본문
            qtitle.config(text=f"Q{curr_index+1} [id: {q_id}]")
            qtext.config(state=tk.NORMAL)
            qtext.delete("1.0", tk.END)

            t_title = (q.get("title") or "").strip()
            t_ctx   = (q.get("context") or "").strip()
            if t_title:
                qtext.insert(tk.END, t_title + "\n\n")
            if t_ctx:
                qtext.insert(tk.END, t_ctx)
            qtext.config(state=tk.DISABLED)

            # 해설 부분
            etext.config(state=tk.NORMAL)
            etext.delete("1.0", tk.END)

            # 정답 / 내가 제출한 답
            correct_letters = review[curr_index]["answer"]  # ["A","D",...]
            user_letters    = review[curr_index]["user"]    # ["B","C",...]

            # 보기 맵핑 { "A": "보기텍스트 전체", ... }
            choice_map = {}
            chs = q.get("choices", [])
            lab = labels_for_choices(len(chs))  # ["A","B","C","D",...]
            for idx, choice_text in enumerate(chs):
                choice_map[lab[idx]] = choice_text

            # 정답 라인 구성
            ans_chunks = []
            for letter in correct_letters:
                body = choice_map.get(letter, "")
                ans_chunks.append(f"{letter}. {body}")
            full_correct_text = " | ".join(ans_chunks) if ans_chunks else "-"

            # 제출한 답 라인 구성
            user_chunks = []
            for letter in user_letters:
                body = choice_map.get(letter, "")
                if body:
                    user_chunks.append(f"{letter}. {body}")
                else:
                    user_chunks.append(letter)
            full_user_text = " | ".join(user_chunks) if user_chunks else "-"

            etext.insert(
                tk.END,
                f"정답: {full_correct_text}\n"
                f"제출한 답변: {full_user_text}\n\n",
                ("answer",),
            )

            expl = (q.get("explain") or "").strip()
            if expl:
                etext.insert(tk.END, "설명:\n", ("answer",))
                etext.insert(tk.END, expl + "\n")
            else:
                etext.insert(tk.END, "설명:\n설명 없음\n")

            etext.tag_config(
                "answer",
                font=FONT_TEXT,
                foreground=COLOR_TEXT,
            )
            etext.config(state=tk.DISABLED)

        # 초기 렌더 + 버튼 색칠
        render_review_question()
        paint_buttons()
