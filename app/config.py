# =========================
# app/config.py
# =========================
from pathlib import Path

# JSON 세트는 App 폴더 내부로 고정
JSON_DIR = Path(__file__).resolve().parent / "Quiz_Set"

# 시험 설정
NUM_QUESTIONS = 65
PASS_CUTOFF, SAFE_CUTOFF, PERF_CUTOFF = 52, 55, 58
DEFAULT_TIMER_MIN = 100  # 분 (None이면 타이머 끔)