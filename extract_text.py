# extract_text.py
import pdfplumber, sys, pathlib
from tqdm import tqdm

ROOT = pathlib.Path(__file__).parent
IN  = ROOT / "input"
OUT = ROOT / "output"

FILES = [
    ("SAA-C03_KOR(1).pdf", "part1.txt"),
    ("SAA-C03_KOR(2).pdf", "part2.txt"),
]

def dump_pdf(src, dst):
    with pdfplumber.open(src) as pdf:
        lines = []
        for page in tqdm(pdf.pages, desc=src.name):
            text = page.extract_text() or ""
            lines.append(text + "\n")
    dst.write_text("".join(lines), encoding="utf-8")

def main():
    for src_name, out_name in FILES:
        src = IN / src_name
        dst = OUT / out_name
        if not src.exists():
            print(f"[WARN] 파일 없음: {src}")
            continue
        dump_pdf(src, dst)
        print(f"[OK] {dst} 저장")

if __name__ == "__main__":
    main()
