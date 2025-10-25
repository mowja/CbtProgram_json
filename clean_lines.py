# clean_lines.py (URL 초강화 병합판)
# 목적: PDF 추출 텍스트에서 불필요한 줄바꿈을 복원하고, 보기/정답/설명/링크 경계를 보존/보강
# - 보기 라벨: A~Z, 숫자(1)·1., ①~⑳, 한글(가. 나. 다. …) 모두 허용
# - 보기 이어지는 줄은 같은 보기로 합침
# - 문장(지문)은 종결부호 전까지 이어붙임
# - URL 줄바꿈/띄어쓰기 깨짐 보정 (단어 중간 분리, 빈 줄 포함, 숫자 시작 조각까지 전부 병합)
# - 출력: output/part1_clean.txt, output/part2_clean.txt (원본 파일명을 그대로 사용)

from pathlib import Path
import re

ROOT = Path(__file__).parent
IN  = ROOT / "output"
OUT = ROOT / "output"

INPUTS = [
    ("part1.txt", "part1_clean.txt"),
    ("part2.txt", "part2_clean.txt"),
]

# --- 경계/라벨 패턴 ---
RE_Q       = re.compile(r"^Q\d+\s*$")
RE_ANSWER  = re.compile(r"^(?:Answer|Answers|정답|답)\s*[:：]\s*", re.I)
RE_EXPL    = re.compile(r"^설명\d*\s*[:：]\s*", re.I)
RE_LINK    = re.compile(r"^https?://", re.I)

# 보기 라벨 (가변)
RE_CHOICE_ALPHA = re.compile(r"^[A-Z][\.\)]\s+")            # A.  A)
RE_CHOICE_NUM   = re.compile(r"^\d+[\.\)]\s+")             # 1.  1)
RE_CHOICE_CIRC  = re.compile(r"^[①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳]\s*")
RE_CHOICE_KOR   = re.compile(r"^[가-힣]\.[ \t]+")            # 가. 나. 다. (필요시 확장)

# 문장 종결 힌트 (한국어/영문)
ENDMARK = (
    ".", "?", "!", "…", ".”", "?”", "!”", ").", "다.", "요.", "니다.", "습니다.", "함.", "함?"
)

# URL-safe 문자 집합 (RFC3986 기반 + 일반적으로 쓰이는 몇 가지 추가)
_URL_SAFE = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~:/?#@!$&'()*+,;=%")

RE_DOMAIN_PIECE = re.compile(r"^[A-Za-z0-9.-]+\.[A-Za-z]{2,}(/|$)")

# URL 이어붙이기 판단 (단어 중간 분리, 빈 줄, 숫자 시작 조각까지 허용)
def _looks_like_url_continuation(s: str) -> bool:
    if s is None:
        return False
    s = s.strip()
    if s == "":
        # 빈 줄도 URL 중간 끊김으로 간주하여 이어붙임 허용
        return True
    # URL-safe 문자만으로 구성되어 있으면 이어붙임 (하이픈 분해 등 포함)
    if all((ch in _URL_SAFE) for ch in s):
        return True
    # 도메인/경로 조각
    if RE_DOMAIN_PIECE.match(s):
        return True
    # 선행 기호로 시작하면 이어붙임
    if s.startswith(("/", "?", "&", "#", ".", "-", "_")):
        return True
    # 숫자로 시작(예: 84973-...)도 examtopics 패턴에서 흔함
    if re.match(r"^\d", s):
        return True
    # 알파뉴메릭 단어(예: rchitect, sol, utions 등)도 이어붙임
    if re.match(r"^[A-Za-z0-9-]+$", s):
        return True
    return False

# URL 줄바꿈/띄어쓰기 보정 (공격적으로 병합)
def _merge_url_wraps(lines: list[str]) -> list[str]:
    out = []
    i = 0
    N = len(lines)
    while i < N:
        cur = lines[i].rstrip("\n")
        if RE_LINK.match(cur.strip()):
            # 현재 줄에서 공백/개행 제거
            buf = cur.replace(" ", "").replace("\t", "").replace("\u00A0", "").strip()
            j = i + 1
            while j < N:
                nxt_raw = lines[j]
                nxt = (nxt_raw or "").strip()

                # 경계(새 Q/정답/설명/새 URL/보기 머리)면 중단
                if RE_Q.match(nxt) or RE_ANSWER.match(nxt) or RE_EXPL.match(nxt) or RE_LINK.match(nxt) \
                   or RE_CHOICE_ALPHA.match(nxt) or RE_CHOICE_NUM.match(nxt) or RE_CHOICE_CIRC.match(nxt) or RE_CHOICE_KOR.match(nxt):
                    break

                # 이어붙일지 판정 (빈 줄 포함 허용)
                if _looks_like_url_continuation(nxt):
                    nxt_clean = nxt.replace(" ", "").replace("\t", "").replace("\u00A0", "")
                    buf += nxt_clean  # 하이픈 유무에 관계없이 그대로 연결
                    j += 1
                    continue
                else:
                    break

            out.append(buf)
            i = j
        else:
            out.append(cur)
            i += 1
    return out

# 보기 라인인지 판별
def is_choice_head(s: str) -> bool:
    return bool(RE_CHOICE_ALPHA.match(s) or RE_CHOICE_NUM.match(s) or RE_CHOICE_CIRC.match(s) or RE_CHOICE_KOR.match(s))

# 경계(새 블록 시작) 라인인지
def is_border_line(s: str) -> bool:
    if not s.strip():
        return False
    return bool(
        RE_Q.match(s) or
        is_choice_head(s) or
        RE_ANSWER.match(s) or
        RE_EXPL.match(s) or
        RE_LINK.match(s)
    )


def join_lines(raw: str) -> str:
    # 1) 1차 라인화 + URL 보정
    lines = [ln.rstrip() for ln in raw.splitlines()]
    lines = _merge_url_wraps(lines)

    out: list[str] = []
    buf = ""  # 지문/문장 버퍼

    def flush_buf():
        nonlocal buf
        if buf.strip():
            out.append(buf.strip())
        buf = ""

    for ln in lines:
        s = ln.strip()
        if not s:
            # 빈 줄은 문단 경계 → 지문 버퍼 확정
            flush_buf()
            continue

        # 경계 라인은 그대로 출력 (보기/정답/설명/링크/Q)
        if is_border_line(s):
            flush_buf()
            out.append(s)
            continue

        # 직전에 추가된 라인이 보기 머리였으면 → 같은 보기로 붙임
        if out and is_choice_head(out[-1]):
            out[-1] = (out[-1] + " " + s).strip()
            continue

        # 일반 지문: 문장 종결 전까지 결합
        if not buf:
            buf = s
        else:
            if not buf.endswith(ENDMARK):
                buf += " " + s
            else:
                flush_buf()
                buf = s

    flush_buf()
    return "\n".join(out) + "\n"


def main():
    for src, dst in INPUTS:
        in_path  = IN / src
        out_path = OUT / dst
        if not in_path.exists():
            print(f"[WARN] 입력 없음: {in_path}")
            continue
        raw = in_path.read_text(encoding="utf-8", errors="ignore")
        fixed = join_lines(raw)
        out_path.write_text(fixed, encoding="utf-8")
        print(f"[OK] 저장: {out_path}")

if __name__ == "__main__":
    main()

'''
# clean_lines.py
# 목적: PDF에서 추출한 텍스트의 줄바꿈을 문장/항목 단위로 재결합
# - Q번호/보기(A.~D.)/Answer:/설명:/링크(http) 라인 = 경계로 유지
# - 그 외 줄은 문장 종결 부호가 나오기 전까지 이어붙임
# - 보기(A.~D.) 바로 다음 줄이 이어지는 내용이면, 같은 보기 라인에 붙여서 1줄로 만듦

from pathlib import Path
import re

ROOT = Path(__file__).parent
IN  = ROOT / "output"
OUT = ROOT / "output"

INPUTS = [
    ("part1.txt", "part1_clean.txt"),
    ("part2.txt", "part2_clean.txt"),
]

# 경계 패턴: 아래 조건에 해당하는 줄은 '새 문단 시작'으로 간주
BORDER = re.compile(r"""
    ^Q\d+\s*$|          # Q번호 (예: Q123)
    ^[A-D]\.\s+|        # 보기 A. / B. / C. / D.
    ^Answer:\s*|        # 정답 표시
    ^설명:\s*|          # 설명
    ^https?://          # 링크
""", re.X)

# 문장 종료 힌트(한국어/영문)
ENDMARK = (
    ".", "?", "!", "…",
    ".”", "?”", "!”", ").",
    "다.", "요.", "니다.", "습니다.", "하지.", "한다."
)

# 보기 시작 라인 패턴
CHOICE_HEAD = re.compile(r"^[A-D]\.\s+")

def join_lines(raw: str) -> str:
    lines = [ln.rstrip() for ln in raw.splitlines()]
    out = []
    buf = ""

    def flush_buf():
        nonlocal buf
        if buf.strip():
            out.append(buf.strip())
        buf = ""

    for ln in lines:
        if not ln.strip():
            # 빈 줄은 문단 경계로 처리
            flush_buf()
            continue

        # 경계 라인(Q/보기/Answer/설명/링크)은 그대로 출력
        if BORDER.search(ln):
            flush_buf()
            out.append(ln.strip())
            continue

        # 직전 출력 라인이 '보기 시작(A.~D.)'인 경우: 현재 줄을 그 보기에 붙이기
        if out and CHOICE_HEAD.match(out[-1]) and not BORDER.search(ln):
            out[-1] = out[-1] + " " + ln.strip()
            continue

        # 일반 문장 결합 로직
        if not buf:
            buf = ln.strip()
        else:
            if not buf.endswith(ENDMARK):
                buf += " " + ln.strip()
            else:
                flush_buf()
                buf = ln.strip()

    flush_buf()
    return "\n".join(out) + "\n"

def main():
    for src, dst in INPUTS:
        in_path  = IN / src
        out_path = OUT / dst
        if not in_path.exists():
            print(f"[WARN] 입력 없음: {in_path}")
            continue
        raw   = in_path.read_text(encoding="utf-8", errors="ignore")
        fixed = join_lines(raw)
        out_path.write_text(fixed, encoding="utf-8")
        print(f"[OK] 저장: {out_path}")

if __name__ == "__main__":
    main()

'''