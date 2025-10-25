import re
import json
from pathlib import Path
from collections import defaultdict

# CBT Parser v02 - 복수 정답 지원
# -------------------------------------------------
# 경로 설정
# -------------------------------------------------
BASE_DIR = Path(r"C:\Users\mowja\CBT_Parser")
PART1_FILE = BASE_DIR / r"output\part1_clean.txt"
PART2_FILE = BASE_DIR / r"output\part2_clean.txt"

# 개별 범위 JSON들을 저장할 디렉터리
QUE_DIR = BASE_DIR / r"Que"
QUE_DIR.mkdir(parents=True, exist_ok=True)


# -------------------------------------------------
# part2 ID 매핑 규칙
# -------------------------------------------------
def map_part2_id(original_qnum: int) -> int:
    """
    part2 전용 번호 재할당 규칙:
    - 501~999  -> 그대로
    - 100~119  -> +900 (100 ->1000 ... 119 ->1019)
    - 1~99     -> 1019 + num (1->1020 ... 99->1118)
    """
    if 501 <= original_qnum <= 999:
        return original_qnum
    elif 100 <= original_qnum <= 119:
        return original_qnum + 900
    elif 1 <= original_qnum <= 99:
        return 1019 + original_qnum
    else:
        print(f"[WARN] part2에서 예상 밖 번호 Q{original_qnum}, 그대로 사용합니다.")
        return original_qnum


# -------------------------------------------------
# TXT 파싱 함수
# -------------------------------------------------
def parse_file(path: Path, group_name: str, is_part2: bool = False):
    """
    주어진 txt 파일을 읽어서 문제 dict 리스트로 반환.
    group_name: "part1" 또는 "part2"
    is_part2: True이면 ID 매핑(map_part2_id) 적용
    """
    text = path.read_text(encoding="utf-8").strip()

    # Q123 으로 시작하는 문제 블록별로 전체를 분리
    pattern = re.compile(
        r"^Q(\d+)\s*(.*?)(?=^Q\d+|\Z)",
        re.DOTALL | re.MULTILINE
    )

    questions = []

    for match in pattern.finditer(text):
        qnum_str = match.group(1)
        body = match.group(2).strip()
        qnum = int(qnum_str)

        final_id = map_part2_id(qnum) if is_part2 else qnum

        # 라인 단위 분해 후 빈 줄 제거
        raw_lines = [line.strip() for line in body.splitlines()]
        lines = [ln for ln in raw_lines if ln != ""]

        # 선택지 시작 위치 찾기 (A. / B. / ...)
        choice_start_idx = None
        for i, line in enumerate(lines):
            if re.match(r"^[A-Z]\.\s", line):  # A.~Z. 까지 허용
                choice_start_idx = i
                break

        if choice_start_idx is None:
            pre_choice_lines = lines[:]
            choice_lines = []
            post_choice_lines = []
        else:
            pre_choice_lines = lines[:choice_start_idx]

            # Answer: 위치 찾기
            answer_idx = None
            for j in range(choice_start_idx, len(lines)):
                if re.match(r"^Answer\s*:", lines[j], re.IGNORECASE):
                    answer_idx = j
                    break

            if answer_idx is None:
                choice_lines = lines[choice_start_idx:]
                post_choice_lines = []
            else:
                choice_lines = lines[choice_start_idx:answer_idx]
                post_choice_lines = lines[answer_idx:]

        # title / context 분리
        if len(pre_choice_lines) > 0:
            title = pre_choice_lines[0]
            context = " ".join(pre_choice_lines[1:]).strip()
        else:
            title = ""
            context = ""

        # choices 파싱 (A,B,C,D,E,F...)
        choices_dict = {}
        last_key = None
        for cl in choice_lines:
            m = re.match(r"^([A-Z])\.\s*(.*)$", cl)
            if m:
                label = m.group(1)
                text_choice = m.group(2).strip()
                choices_dict[label] = text_choice
                last_key = label
            else:
                if last_key is not None:
                    choices_dict[last_key] += " " + cl.strip()
        ordered_choices = [choices_dict[k] for k in sorted(choices_dict.keys())]

        # post_choice_lines에서 Answer / 링크 / 해설 추출
        answer_letters = []   # <- 복수 정답 지원
        links = []
        explain_lines = []
        mode_explain = False

        for pl in post_choice_lines:
            # Answer 처리
            ans_m = re.match(r"^Answer\s*:\s*(.+)$", pl, re.IGNORECASE)
            if ans_m:
                raw_ans = ans_m.group(1).strip()
                # 예: "A, B" 또는 "A,B" 또는 "A / B" 등 -> ['A','B']
                parts = re.split(r"[,/]|\s+", raw_ans)
                cleaned = []
                for p in parts:
                    p2 = p.strip().upper()
                    if re.match(r"^[A-Z]$", p2):
                        cleaned.append(p2)
                if not cleaned and raw_ans:
                    # 만약 위에서 못 나눴으면 전체를 하나로라도 넣는다
                    cleaned = [raw_ans]
                answer_letters.extend(cleaned)
                continue

            # 링크
            if re.match(r"^https?://", pl):
                links.append(pl.strip())
                if mode_explain:
                    explain_lines.append(pl.strip())
                continue

            # 설명 시작
            if pl.startswith("설명"):
                mode_explain = True
                explain_lines.append(pl)
                continue

            # 설명 중
            if mode_explain:
                explain_lines.append(pl)
            else:
                # '설명' 이라는 단어가 본문 중간에만 나온 경우까지 커버
                if "설명" in pl:
                    mode_explain = True
                    explain_lines.append(pl)

        primary_link = links[0] if links else ""
        explain_text = "\n".join(explain_lines).strip()

        question_dict = {
            "id": final_id,
            "group": group_name,
            "title": title,
            "context": context,
            "choices": ordered_choices,
            "answers": answer_letters,
            "link": primary_link,
            "links": links,
            "explain": explain_text
        }

        questions.append(question_dict)

    return questions


# -------------------------------------------------
# ID 범위 계산 / 버킷 저장
# -------------------------------------------------
def range_for_id(qid: int):
    start = ((qid - 1) // 100) * 100 + 1
    end = start + 99
    return start, end


def bucket_by_range(questions):
    buckets = defaultdict(list)
    for q in questions:
        qid = q["id"]
        start, end = range_for_id(qid)
        buckets[(start, end)].append(q)
    return buckets


def save_buckets_to_files(buckets):
    for (start, end), qlist in buckets.items():
        qlist_sorted = sorted(qlist, key=lambda x: x["id"])
        filename = f"Q{start}~Q{end}.json"
        file_path = QUE_DIR / filename
        file_path.write_text(
            json.dumps(qlist_sorted, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        print(f"생성: {file_path}  ({len(qlist_sorted)}문항)")


def main():
    part1_questions = parse_file(PART1_FILE, group_name="part1", is_part2=False)
    part2_questions = parse_file(PART2_FILE, group_name="part2", is_part2=True)

    merged = part1_questions + part2_questions
    merged.sort(key=lambda q: q["id"])

    buckets = bucket_by_range(merged)
    save_buckets_to_files(buckets)

    print("완료되었습니다.")


if __name__ == "__main__":
    main()
