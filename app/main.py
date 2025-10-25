# =========================
# app/main.py
# =========================
import tkinter as tk
from app.ui.app_window import QuizApp
#from app.gui import QuizApp

def run():
    app = QuizApp()
    app.mainloop()

if __name__ == "__main__":
    run()
