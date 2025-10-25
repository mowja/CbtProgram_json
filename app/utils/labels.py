# app/utils/labels.py
LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

def labels_for_choices(n: int) -> list[str]:
    """보기 개수에 맞는 A,B,C,... 라벨 생성"""
    n = max(0, min(n, 26))
    return [chr(ord("A") + i) for i in range(n)]

def normalize_user_answer(s: str, max_labels: int) -> list[str]:
    """사용자 입력을 ['A','C'] 형태로 정규화"""
    if not s:
        return []
    s = s.strip().upper()
    for ch in [" ", ",", "/", "&", ";", "|"]:
        s = s.replace(ch, "")
    out = []
    map_num = {str(i): LETTERS[i-1] for i in range(1, 27)}
    allowed = set(LETTERS[:max_labels])
    for ch in s:
        if ch in allowed:
            out.append(ch)
        elif ch in map_num and map_num[ch] in allowed:
            out.append(map_num[ch])
    return sorted(set(out), key=lambda x: LETTERS.index(x))
