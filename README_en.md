CBT Parser & Quiz App (Tkinter)

Overview
- Lightweight CBT practice app using Python + Tkinter.
- Loads question banks from JSON files you provide (not included in this repo).
- Works as a module (`python -m app.main`) or a bundled Windows exe via PyInstaller.

Folder Layout
- Code: `app/`
- Question banks (user-provided): `app/Quiz_Set/` (ignored by git)
- Sample to copy: `samples/Quiz_Set/Q_SAMPLE.json`

Run (no data bundled)
1) Create your own question set(s) under `app/Quiz_Set/` as described below.
2) From the repo root: `python -m app.main`

Quick start with sample
- Copy `samples/Quiz_Set/Q_SAMPLE.json` to `app/Quiz_Set/Q1~Q100.json` (or any name matching `Q*~Q*.json`).
- Edit the file to add more questions following the same structure.

Question Bank Format
- Place one or more JSON files under `app/Quiz_Set/`.
- Filename pattern is flexible (e.g., `Q1~Q100.json`, `Q101~Q200.json`), the app loads all files matching `Q*~Q*.json`.
- Each file contains a list of question objects. Required and optional fields are:

```
[
  {
    "id": 101,                 // unique per question (string or number)
    "title": "Question title", // optional; shown above the context
    "context": "Full question text.",
    "choices": [               // 2–26 choices, ordered; labeled A, B, C ...
      "Option A",
      "Option B",
      "Option C",
      "Option D"
    ],
    "answers": ["B", "D"],     // correct answers by letter; single- or multi-select
    "explain": "Why the answer is correct.", // optional
    "link": "https://docs.example.com/..."   // optional; click opens in browser
  }
]
```

Notes
- `answers` must reference labels by letter (e.g., `"A"`, `"C"`). For single-answer questions, use a one-element list (e.g., `["C"]`).
- Up to 26 choices are supported (A–Z).
- The app samples `NUM_QUESTIONS` from the combined bank. You can change this in `app/config.py`.

Build a Windows EXE (optional)
- Requires PyInstaller: `pip install pyinstaller`
- One-file, no-console build with icon and data mapping:

```
pyinstaller --onefile --windowed --name CBT_Quiz \
  --icon AWS-SAA-C03.ico \
  --add-data "app/Quiz_set;app/Quiz_Set" \
  app/main.py
```

- The produced executable will be in `dist/`.
- For variant builds (e.g., v2/v3/v4), update `--name` accordingly or use the provided `.spec` files (if included locally).

Why `app/Quiz_Set/` is empty here
- The question files are not distributed to avoid copyright issues.
- Add your own JSON files in that folder following the format above.

License
- Code in this repository is provided without bundled question content. Ensure you have the right to use any question data you add.
