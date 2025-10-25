# app/services/grader.py
from app.utils.labels import LETTERS

def multi_required(q: dict) -> bool:
    """문항이 복수정답인지 여부"""
    return len(set(q.get("answers", []))) >= 2

def grade(run: list[dict], selected: dict[int, set[str]]) -> tuple[int, list[dict]]:
    """채점 및 리뷰 생성"""
    correct = 0
    review = []
    for q in run:
        qid = q.get("id")
        ua = set(selected.get(qid, set()))
        ca = set(q.get("answers", []))
        ok = ua == ca
        if ok:
            correct += 1
        review.append({
            "id": qid,
            "title": (q.get("title") or "").strip(),
            "correct": ok,
            "user": sorted(list(ua), key=lambda x: LETTERS.index(x)),
            "answer": sorted(list(ca), key=lambda x: LETTERS.index(x)),
        })
    return correct, review

def status_from_score(score: int, total: int, cutoffs=(52,55,58)) -> str:
    """점수에 따른 상태 문구"""
    PASS_CUTOFF, SAFE_CUTOFF, PERF_CUTOFF = cutoffs
    if score >= PERF_CUTOFF: return "PERFECTO ✅"
    if score >= SAFE_CUTOFF: return "안정권 ✅"
    if score >= PASS_CUTOFF: return "합격권 ✅"
    return "미달 ❌"
