# app/services/loader.py
from pathlib import Path
import json, random

def load_bank(json_dir: Path) -> list[dict]:
    """폴더 내 JSON 파일을 읽어 문제은행 생성"""
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
            print(f"[WARN] {f.name} 읽기 실패: {e}")
    return bank

def sample_questions(bank: list[dict], n: int, seed=None) -> list[dict]:
    """무작위로 n개 문항 선택"""
    rng = random.Random(seed)
    if len(bank) < n:
        raise ValueError(f"문제은행 부족: {len(bank)}개 (요청 {n})")
    return rng.sample(bank, n)
