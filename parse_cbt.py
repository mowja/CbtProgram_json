# parse_cbt.py (가변 보기·복수정답·ID범위 저장)
# 입력 : output/part1_clean.txt, output/part2_clean.txt  ← clean_lines.py로 정리된 파일
# 출력 : C:\Users\mowja\CBT_Parser\Que\Q1~Q100.json, Q101~Q200.json ... (ID 범위 100단위)
#
# 기능 요약
# - Q블록 파싱(같은 줄에 제목 이어짐 허용)
# - 보기 라벨: A..Z / 1) 1. / ①..⑳ / 가.나.다. 전부 지원 (보기 개수 무제한, 최대 26까지)
# - 정답 라벨: Answer/Answers/정답/답: 뒤에서 A,C / 1,3 / ①③ / 가,다 / AC / A/C 등 모두 파싱
# - 최종 출력: choices=[텍스트...] (2~N), answers=["A","C","E"...] (보기 개수만큼 A..Z 부여)
# - ID 정규화: part2 Q100~119 → 1000~1019, part2 Q1~99 → 1020~1118
# - 저장: ID 범위별 100단위 파일(Q1~Q100.json 등). 빈 구간은 생략

from pathlib import Path
import re, json, unicodedata
from typing import List, Dict

ROOT = Path(__file__).parent
IN   = ROOT / "output"
OUT  = Path(r"C:\Users\mowja\CBT_Parser\Que")   # 필요시 변경

PARTS = [
    ("part1_clean.txt", "part1"),
    ("part2_clean.txt", "part2"),
]

# ---------- 패턴 ----------
RE_QLINE = re.compile(r"^\s*Q\s*(\d{1,4})\s*(.*)$", re.M)
RE_LINK  = re.compile(r"^https?://", re.I)
RE_ANS   = re.compile(r"^(?:Answer|Answers|정답|답)\s*[:：]\s*(.+)$", re.I)
RE_EXPL  = re.compile(r"^설명\d*\s*[:：]\s*(.*)$")

# 보기 라벨(머리) 인식: A. / A) / 1. / 1) / ① / 가.
RE_CHOICE_ALPHA = re.compile(r"^([A-Z])[\.\)]\s+(.*)$")
RE_CHOICE_NUM   = re.compile(r"^(\d+)[\.\)]\s+(.*)$")
RE_CHOICE_CIRC  = re.compile(r"^([①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳])\s*(.*)$")
RE_CHOICE_KOR   = re.compile(r"^([가나다라마바사아자차카타파하])\.[ \t]+(.*)$")

CIRC_MAP = {ch:i+1 for i,ch in enumerate(list("①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳"))}
KOR_SEQ  = list("가나다라마바사아자차카타파하")  # 필요시 확장
KOR_MAP  = {ch:i+1 for i,ch in enumerate(KOR_SEQ)}

LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
SPLIT_TOK = re.compile(r"[\s,/&;·･|｜、，／＆]+")

# ---------- 유틸 ----------

def _to_ascii(s: str) -> str:
    try:
        return unicodedata.normalize("NFKC", s)
    except Exception:
        return s

def _normalize_id(group: str, qnum: int) -> int:
    if group == "part2":
        if 100 <= qnum <= 119:  # Q100~Q119 → Q1000~Q1019
            return qnum + 900
        if 1 <= qnum <= 99:     # Q1~Q99   → Q1020~Q1118
            return 1019 + qnum
    return qnum

# 토큰을 보기 순번(1-based)으로 매핑

def token_to_pos(tok: str):
    t = tok.strip().upper()
    if not t:
        return None
    # A..Z
    if len(t) == 1 and 'A' <= t <= 'Z':
        return ord(t) - ord('A') + 1
    # 숫자
    if t.isdigit():
        v = int(t)
        return v if v >= 1 else None
    # 동그라미 숫자
    if t in CIRC_MAP:
        return CIRC_MAP[t]
    # 한글 가~하
    if t in KOR_MAP:
        return KOR_MAP[t]
    return None

# 정답 포지션 파싱: AC / A,C / 1,3 / ①③ / 가나다 / A/C 등 모두 대응

def parse_answer_positions(raw: str) -> List[int]:
    s = _to_ascii((raw or "").strip())
    if not s:
        return []
    # 괄호/대괄호의 주석 제거 (예: (복수정답))
    s = re.sub(r"[\(\[（【].*?[\)\]）】]", "", s)
    # 한글 접속사 정규화
    s = s.replace("그리고", ",").replace("및", ",").replace("와", ",").replace("또는", ",").replace("or", ",")

    parts = [p for p in SPLIT_TOK.split(s) if p]
    poses: List[int] = []
    for p in parts:
        if p.isdigit():
            # 숫자 묶음은 개별 숫자 분해 (예: 135 → 1,3,5)
            for ch in p:
                pos = token_to_pos(ch)
                if pos: poses.append(pos)
            continue
        # 문자/기호 혼합은 한 글자씩 분해 (예: AC, ①③⑤, 가나다)
        for ch in p:
            pos = token_to_pos(ch)
            if pos:
                poses.append(pos)
    return sorted(set(poses))

# ---------- 파싱 ----------

def parse_one(raw_text: str, group: str) -> List[Dict]:
    lines = [ln.rstrip() for ln in raw_text.splitlines()]
    joined = "\n".join(lines)
    matches = list(RE_QLINE.finditer(joined))
    if not matches:
        return []

    items: List[Dict] = []
    for idx, m in enumerate(matches):
        qn = int(m.group(1))
        inline = m.group(2).strip()
        start = m.end()
        end   = matches[idx+1].start() if idx+1 < len(matches) else len(joined)

        body: List[str] = []
        if inline:
            body.append(inline)
        if start < end:
            body += joined[start:end].splitlines()

        title = ""; context: List[str] = []
        choices: List[str] = []
        ans_pos: List[int] = []
        links: List[str] = []
        explain: List[str] = []

        for ln in body:
            s = ln.strip()
            if not s:
                continue

            ma = RE_ANS.match(s)
            if ma:
                ans_pos += parse_answer_positions(ma.group(1))
                continue

            me = RE_EXPL.match(s)
            if me:
                ex = me.group(1).strip()
                if ex:
                    explain.append(ex)
                continue

            if RE_LINK.match(s):
                # clean_lines.py에서 이미 1줄 URL로 복구됨
                links.append(s)
                # 설명에도 링크 포함될 수 있어 보조로 추가
                if explain and not explain[-1].endswith(s):
                    explain.append(s)
                continue

            mc = (RE_CHOICE_ALPHA.match(s) or RE_CHOICE_NUM.match(s) or
                  RE_CHOICE_CIRC.match(s)  or RE_CHOICE_KOR.match(s))
            if mc:
                text = mc.groups()[-1].strip()
                if text:
                    choices.append(text)
                continue

            # 일반 문장 (제목/지문)
            if not title:
                title = s
            else:
                context.append(s)

        # 유효성: 보기 2+ & 정답 1+
        if len(choices) < 2 or len(ans_pos) < 1:
            continue

        # 포지션 → A..Z (choices 길이 초과/26 초과는 제거)
        ans_letters: List[str] = []
        for pos in ans_pos:
            if 1 <= pos <= len(choices) and pos <= 26:
                ans_letters.append(LETTERS[pos-1])
        ans_letters = sorted(set(ans_letters), key=lambda x: LETTERS.index(x))
        if not ans_letters:
            continue

        obj = {
            "id": _normalize_id(group, qn),
            "group": ("new" if (group == "part2" and 1 <= qn <= 99) else group),
            "title": title.strip(),
            "context": " ".join(context).strip(),
            "choices": choices,         # 2~N개 (N<=26)
            "answers": ans_letters,     # ["A"..]
        }
        if links:
            obj["link"]  = links[0]
            obj["links"] = links
        if explain:
            obj["explain"] = "\n".join(explain)

        items.append(obj)

    return items

# ---------- 저장 ----------

def save_split_by_id_range(items: List[Dict]):
    if not items:
        print("[WARN] 결과 0건"); return
    items.sort(key=lambda x: x["id"])  
    OUT.mkdir(parents=True, exist_ok=True)

    min_id = min(x["id"] for x in items)
    max_id = max(x["id"] for x in items)
    start_id = ((min_id - 1)//100)*100 + 1
    nfiles = 0
    while start_id <= max_id:
        end_id = start_id + 99
        chunk = [x for x in items if start_id <= x["id"] <= end_id]
        if chunk:
            fname = f"Q{start_id}~Q{end_id}.json"
            (OUT / fname).write_text(json.dumps(chunk, ensure_ascii=False, indent=2), encoding="utf-8")
            nfiles += 1
        start_id += 100
    print(f"[OK] ID 범위 분할 저장 완료: {nfiles}개 파일 | 총 문항={len(items)} | 경로={OUT}")

# ---------- 실행 ----------

def main():
    all_items: List[Dict] = []
    seen = set()
    for fname, group in PARTS:
        p = IN / fname
        if not p.exists():
            print(f"[WARN] 없음: {p}")
            continue
        raw = p.read_text(encoding="utf-8", errors="ignore")
        all_items.extend(parse_one(raw, group))

    # ID 중복 회피
    for q in all_items:
        while q["id"] in seen:
            q["id"] += 1
        seen.add(q["id"]) 

    save_split_by_id_range(all_items)

if __name__ == "__main__":
    main()
