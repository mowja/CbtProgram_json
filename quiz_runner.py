# quiz_runner.py
# 콘솔형 CBT 러너: JSON(분할 파일들)을 읽어 65문제 1회 시험 진행
# - 복수 정답 지원 (answers: ["A","C"])
# - 합격/안정권/퍼펙트 기준: 52 / 55 / 58 문항 이상 정답
# - Windows 콘솔 UTF-8 대응(가능하면 pwsh 권장)

from __future__ import annotations
import json, random, sys
from pathlib import Path

# === 설정 ===
JSON_DIR = Path(r"C:\Users\mowja\CBT_Parser\Que")  # 분할 JSON 폴더
NUM_QUESTIONS = 65
PASS_CUTOFF   = 52  # 합격
SAFE_CUTOFF   = 55  # 안정권
PERF_CUTOFF   = 58  # 퍼펙토

# === 유틸 ===
MAP_1to4 = {"1":"A","2":"B","3":"C","4":"D"}
VALID = set("ABCD")

def normalize_user_answer(s: str) -> list[str]:
    # 입력 예: a,c / AC / 1,3 / 1 3 / a c
    s = (s or "").strip().upper()
    s = s.replace(" ", "").replace(",", "").replace("/", "").replace("&", "")
    letters = []
    for ch in s:
        if ch in VALID:
            letters.append(ch)
        elif ch in MAP_1to4:
            letters.append(MAP_1to4[ch])
    # 중복 제거 + 정렬(A..D)
    return sorted(set(letters), key=lambda x: "ABCD".index(x))


def load_bank(json_dir: Path) -> list[dict]:
    files = sorted(json_dir.glob("Q*~Q*.json"))
    bank = []
    for f in files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            if isinstance(data, list):
                # 유효 항목만
                for q in data:
                    if isinstance(q, dict) and q.get("choices") and q.get("answers"):
                        bank.append(q)
        except Exception as e:
            print(f"[WARN] {f.name} 읽기 실패: {e}")
    return bank


def grade(run: list[dict]) -> tuple[int, list[dict]]:
    correct = 0
    review = []
    for q in run:
        ua = q.get("user_answers", [])
        ca = q.get("answers", [])
        ok = set(ua) == set(ca)
        if ok:
            correct += 1
        review.append({
            "id": q.get("id"),
            "title": q.get("title", "").strip(),
            "correct": ok,
            "user": ua,
            "answer": ca,
        })
    return correct, review


def print_status(correct: int):
    print("\n=== 결과 요약 ===")
    print(f"정답 수: {correct}/{NUM_QUESTIONS}")
    if correct >= PERF_CUTOFF:
        print("상태: PERFCTO ✅ (퍼펙토)")
    elif correct >= SAFE_CUTOFF:
        print("상태: 안정권 ✅")
    elif correct >= PASS_CUTOFF:
        print("상태: 합격권 ✅")
    else:
        print("상태: 미달 ❌")


def ask_question(i: int, q: dict):
    print("\n" + "-"*70)
    print(f"Q{i}. (ID {q.get('id')})")
    title = q.get("title", "").strip()
    context = q.get("context", "").strip()
    if title:
        print(title)
    if context:
        print(context)
    # 보기
    choices = q.get("choices", [])
    labels = ["A","B","C","D"]
    for idx, text in enumerate(choices):
        if idx < 4:
            print(f" {labels[idx]}. {text}")
    # 입력
    while True:
        raw = input("정답(예: A, AC, 1 3) > ")
        ua = normalize_user_answer(raw)
        if ua:
            q["user_answers"] = ua
            break
        print("입력이 올바르지 않습니다. (예: A 또는 AC 또는 1 3)")


def main():
    if not JSON_DIR.exists():
        print(f"JSON 폴더가 없습니다: {JSON_DIR}")
        sys.exit(1)
    bank = load_bank(JSON_DIR)
    if len(bank) < NUM_QUESTIONS:
        print(f"문항 풀이용 은행이 부족합니다. ({len(bank)}개)")
        sys.exit(1)

    # 시험 세트 생성
    random.seed()
    run = random.sample(bank, NUM_QUESTIONS)

    print("AWS SAA-C03 모의시험 (콘솔)")
    print(f"총 {NUM_QUESTIONS}문제 / 합격 {PASS_CUTOFF}+ / 안정권 {SAFE_CUTOFF}+ / 퍼펙토 {PERF_CUTOFF}+")

    for i, q in enumerate(run, 1):
        ask_question(i, q)

    correct, review = grade(run)
    print_status(correct)

    # === 오답 전부 리뷰 ===
    wrong = [r for r in review if not r["correct"]]
    print(f"\n=== 오답 리뷰 (총 {len(wrong)}문항) ===")
    for r in wrong:
        print("-" * 70)
        print(f"ID {r['id']} | 정답: {','.join(r['answer'])} | 내 답: {','.join(r['user'])}")
        print(r["title"])
        # 설명/링크는 원본 문항에서 꺼냄
        q = next((qq for qq in run if qq.get("id") == r["id"]), None)
        if q and q.get("explain"):
            print("설명:")
            print(q["explain"])
        if q and q.get("link"):
            print(f"링크: {q['link']}")

    # 세션 기록 저장(선택)
    out = JSON_DIR / "last_session_result.json"
    payload = {"correct": correct, "total": NUM_QUESTIONS, "review": review}
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n세션 결과 저장: {out}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n중단됨.")
    except Exception as e:
        # 에러가 나도 메시지 보고 창이 닫히지 않도록
        import traceback
        print("\n[오류] 예기치 못한 에러가 발생했습니다:")
        traceback.print_exc()
    finally:
        try:
            input("\n종료하려면 Enter 키를 누르세요...")
        except Exception:
            pass
