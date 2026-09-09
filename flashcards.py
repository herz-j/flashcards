#!/usr/bin/env python3
"""flashcards — a tiny Tkinter deck runner.

Loads a two-column CSV of flashcards. Cards you miss get re-inserted a few positions later. Progress is saved for each deck based on filename.

Math wrapped in $...$ / $$...$$ is typeset with matplotlib.

Usage:
    uv run flashcards [deck.csv]      # inside this project
    python3 flashcards.py [deck.csv]  # stdlib only
"""

from __future__ import annotations

import csv
import io
import json
import os
import random
import re
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

MIN_GAP = 5
MAX_GAP = 10

BG = "#1a1a1a"
FG = "#e8e8e8"
MUTED = "#888888"
CARD_BG = "#262626"
BORDER = "#3a3a3a"
ACCENT = "#6ab0f3"
YES = "#6ec47e"
NO = "#d77c7c"

UI_FONT = "SF Pro Text" if sys.platform == "darwin" else "Segoe UI"
CARD_SIZE = 17

MATH_RE = re.compile(r"(\$\$[\s\S]*?\$\$|\$[^$]*?\$)")


# TKinderDND fuckery
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
except Exception:
    DND_FILES = None
    TkinterDnD = None


def enable_dnd(root) -> bool:
    """Load the tkdnd Tcl extension into an existing root.

    Returns False when tkinterdnd2 is missing or doesn't ship a binary for the platform
    """
    if TkinterDnD is None:
        return False
    try:
        root.TkdndVersion = TkinterDnD._require(root)
        return True
    except Exception:
        return False

def parse_csv(path: Path) -> list[dict[str, str]]:
    """Read a deck. Rows need at least two columns; blank rows are dropped."""
    with open(path, newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.reader(fh))
    cards = []
    for row in rows:
        if len(row) < 2:
            continue
        front, back = row[0].strip(), row[1].strip()
        if not front and not back:
            continue
        cards.append({"front": unescape(front), "back": unescape(back)})
    return cards


def unescape(text: str) -> str:
    """Turn \\n / \\t into real characters, leaving math regions alone so that
    LaTeX commands like \\nabla, \\neq and \\tau survive."""
    parts = MATH_RE.split(text)
    for i, part in enumerate(parts):
        if i % 2 == 0:
            parts[i] = part.replace("\\n", "\n").replace("\\t", "\t")
    return "".join(parts)


def segments(text: str):
    """Yield (kind, value, display) tuples, kind in {"text", "math"}."""
    for i, part in enumerate(MATH_RE.split(text)):
        if i % 2 == 1:
            display = part.startswith("$$")
            yield "math", part.strip("$").strip(), display
        elif part:
            yield "text", part, False



_math_cache: dict[tuple[str, bool], object] = {}
_mathtext = None          # for matplotlib
_math_available: bool | None = None


def _load_mathtext():
    """Import matplotlib and return None if it isn't installed."""
    global _mathtext, _math_available
    if _math_available is not None:
        return _mathtext
    try:
        import matplotlib
        matplotlib.use("Agg")
        from matplotlib import mathtext
        from matplotlib.font_manager import FontProperties
    except Exception:
        _math_available = False
        return None
    _mathtext = (mathtext, FontProperties)
    _math_available = True
    return _mathtext


def render_math(latex: str, display: bool):
    """Render a math fragment to a PhotoImage.

    Returns None when matplotlib is missing or the fragment won't parse, whereupon the caller falls back to showing the literal source. 
    """
    loaded = _load_mathtext()
    if loaded is None:
        return None
    key = (latex, display)
    if key in _math_cache:
        return _math_cache[key]
    mathtext, FontProperties = loaded
    try:
        buf = io.BytesIO()
        mathtext.math_to_image(
            f"${latex}$",
            buf,
            prop=FontProperties(size=CARD_SIZE + (3 if display else 0)),
            dpi=100,
            format="png",
            color=FG,
        )
        image = tk.PhotoImage(data=buf.getvalue())
    except Exception:
        return None
    _math_cache[key] = image
    return image

def store_path() -> Path:
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / "flashcards"
    elif os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home())) / "flashcards"
    else:
        xdg = os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share"
        base = Path(xdg) / "flashcards"
    return base / "progress.json"


def load_store() -> dict:
    try:
        with open(store_path(), encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_progress(deck: str, queue: list[dict[str, str]]) -> None:
    data = load_store()
    if queue:
        data[deck] = queue
    else:
        data.pop(deck, None)
    path = store_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(data, fh)
        tmp.replace(path)
    except OSError:
        pass  # progress saving is a convenience, never fatal


def load_progress(deck: str) -> list[dict[str, str]]:
    saved = load_store().get(deck)
    if not isinstance(saved, list):
        return []
    return [c for c in saved if isinstance(c, dict) and "front" in c and "back" in c]



class Button(tk.Frame):

    def __init__(self, master, text, command, colour=FG, border=BORDER, pad=(14, 8)):
        super().__init__(master, bg=CARD_BG, highlightthickness=1,
                         highlightbackground=border, highlightcolor=border)
        self.command = command
        self.colour = colour
        self.border = border
        self.enabled = True
        self.label = tk.Label(self, text=text, bg=CARD_BG, fg=colour,
                              font=(UI_FONT, 13), padx=pad[0], pady=pad[1])
        self.label.pack(fill="both", expand=True)
        for widget in (self, self.label):
            widget.bind("<Button-1>", self._click)
            widget.bind("<Enter>", self._enter)
            widget.bind("<Leave>", self._leave)
        self._leave()

    def _click(self, _event=None):
        if self.enabled:
            self.command()

    def _enter(self, _event=None):
        if not self.enabled:
            return
        self.configure(highlightbackground=self.colour, highlightcolor=self.colour)
        self.label.configure(bg=self.colour, fg=BG)
        self.configure(bg=self.colour, cursor="pointinghand" if sys.platform == "darwin" else "hand2")

    def _leave(self, _event=None):
        fg = self.colour if self.enabled else MUTED
        border = self.border if self.enabled else BORDER
        self.configure(highlightbackground=border, highlightcolor=border, bg=CARD_BG, cursor="")
        self.label.configure(bg=CARD_BG, fg=fg)

    def set_enabled(self, enabled: bool):
        self.enabled = enabled
        self._leave()


class Toggle(tk.Frame):

    def __init__(self, master, options, on_change=None):
        super().__init__(master, bg=BG)
        self.value = options[0][0]
        self.on_change = on_change
        self.buttons = {}
        for i, (value, text) in enumerate(options):
            btn = Button(self, text, lambda v=value: self.select(v), pad=(12, 6))
            btn.grid(row=0, column=i, padx=4)
            self.buttons[value] = btn
        self._paint()

    def select(self, value):
        self.value = value
        self._paint()
        if self.on_change:
            self.on_change(value)

    def _paint(self):
        for value, btn in self.buttons.items():
            active = value == self.value
            btn.colour = ACCENT if active else MUTED
            btn.border = ACCENT if active else BORDER
            btn._leave()



class App(tk.Tk):
    def __init__(self, initial: Path | None = None):
        super().__init__()
        self.title("flashcards")
        self.configure(bg=BG)
        self.geometry("760x620")
        self.minsize(520, 480)

        self.dnd = enable_dnd(self)
        self.queue: list[dict[str, str]] = []
        self.deck = ""
        self.revealed = False
        self._images: list[object] = []

        container = tk.Frame(self, bg=BG)
        container.pack(fill="both", expand=True, padx=32, pady=32)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.screens = {}
        for name, build in (("start", self._build_start),
                            ("study", self._build_study),
                            ("done", self._build_done)):
            frame = tk.Frame(container, bg=BG)
            frame.grid(row=0, column=0, sticky="nsew")
            build(frame)
            self.screens[name] = frame

        self.bind("<Key>", self._on_key)
        self.show("start")

        if initial:
            self.after(50, lambda: self.open_deck(initial))

    def show(self, name):
        self.current = name
        self.screens[name].tkraise()

    def _build_start(self, root):
        root.grid_rowconfigure(0, weight=1)
        root.grid_rowconfigure(5, weight=1)
        root.grid_columnconfigure(0, weight=1)

        tk.Label(root, text="f l a s h c a r d s", bg=BG, fg=FG,
                 font=(UI_FONT, 24)).grid(row=1, column=0, pady=(0, 28))

        picker = tk.Frame(root, bg=BG, highlightthickness=2,
                          highlightbackground=BORDER, highlightcolor=BORDER)
        picker.grid(row=2, column=0, sticky="ew")
        inner = tk.Frame(picker, bg=BG)
        inner.pack(pady=42)
        prompt = ("Click or drop a CSV file" if self.dnd
                  else "Click to choose a CSV file")
        tk.Label(inner, text=prompt, bg=BG, fg=FG, font=(UI_FONT, 14)).pack()
        tk.Label(inner, text="Two columns: front, back.   Wrap math in $...$",
                 bg=BG, fg=MUTED, font=(UI_FONT, 11)).pack(pady=(8, 0))

        self._picker = picker
        targets = (picker, inner, *inner.winfo_children())
        for widget in targets:
            widget.bind("<Button-1>", lambda _e: self.choose_file())
            widget.bind("<Enter>", self._picker_lit)
            widget.bind("<Leave>", self._picker_dim)

        if self.dnd:
            for widget in targets:
                widget.drop_target_register(DND_FILES)
                widget.dnd_bind("<<DropEnter>>", self._picker_lit)
                widget.dnd_bind("<<DropLeave>>", self._picker_dim)
                widget.dnd_bind("<<Drop>>", self._on_drop)

        self.order = Toggle(root, [("ordered", "In file order"),
                                   ("shuffled", "Shuffled")])
        self.order.grid(row=3, column=0, pady=16)

        self.resume = tk.Frame(root, bg=CARD_BG)
        self.resume.grid(row=4, column=0, sticky="ew")
        self.resume.grid_remove()

    def _build_study(self, root):
        root.grid_rowconfigure(1, weight=1)
        root.grid_columnconfigure(0, weight=1)

        self.progress = tk.Label(root, text="", bg=BG, fg=MUTED, font=(UI_FONT, 11))
        self.progress.grid(row=0, column=0, pady=(0, 12))

        card = tk.Frame(root, bg=CARD_BG)
        card.grid(row=1, column=0, sticky="nsew")
        card.grid_rowconfigure(0, weight=1)
        card.grid_columnconfigure(0, weight=1)

        self.text = tk.Text(card, wrap="word", bd=0, highlightthickness=0,
                            bg=CARD_BG, fg=FG, font=(UI_FONT, CARD_SIZE),
                            padx=32, pady=32, spacing1=2, spacing3=6,
                            state="disabled", cursor="arrow",
                            selectbackground=CARD_BG, inactiveselectbackground=CARD_BG)
        self.text.grid(row=0, column=0, sticky="nsew")
        self.text.tag_configure("body", justify="center")
        self.text.tag_configure("hint", justify="center", foreground=MUTED,
                                font=(UI_FONT, 11), spacing1=24)
        self.text.tag_configure("rule", justify="center", foreground=BORDER,
                                spacing1=20, spacing3=20)
        for widget in (card, self.text):
            widget.bind("<Button-1>", lambda _e: self.reveal())

        controls = tk.Frame(root, bg=BG)
        controls.grid(row=2, column=0, pady=(20, 0))
        self.btn_no = Button(controls, "✗  Again  (n)", lambda: self.answer(False),
                             colour=NO, border=NO, pad=(28, 12))
        self.btn_no.grid(row=0, column=0, padx=8)
        self.btn_yes = Button(controls, "✓  Got it  (y)", lambda: self.answer(True),
                              colour=YES, border=YES, pad=(28, 12))
        self.btn_yes.grid(row=0, column=1, padx=8)

    def _build_done(self, root):
        root.grid_rowconfigure(0, weight=1)
        root.grid_rowconfigure(3, weight=1)
        root.grid_columnconfigure(0, weight=1)
        tk.Label(root, text="Session complete", bg=BG, fg=FG,
                 font=(UI_FONT, 22)).grid(row=1, column=0, pady=(0, 24))
        Button(root, "Load another deck", self.back_to_start).grid(row=2, column=0)

    def _picker_lit(self, _event=None):
        self._picker.configure(highlightbackground=ACCENT, highlightcolor=ACCENT)

    def _picker_dim(self, _event=None):
        self._picker.configure(highlightbackground=BORDER, highlightcolor=BORDER)

    def _on_drop(self, event):
        """Handle a file dropped on the picker."""
        self._picker_dim()
        paths = self.tk.splitlist(event.data)
        if paths:
            self.open_deck(Path(paths[0]))

    def choose_file(self):
        path = filedialog.askopenfilename(
            title="Choose a deck",
            filetypes=[("CSV files", "*.csv"), ("Text files", "*.txt"), ("All files", "*")],
        )
        if path:
            self.open_deck(Path(path))

    def open_deck(self, path: Path):
        try:
            cards = parse_csv(path)
        except OSError as exc:
            messagebox.showerror("flashcards", f"Could not read {path.name}:\n{exc}")
            return
        if not cards:
            messagebox.showwarning("flashcards", "No cards found in that file.")
            return
        if self.order.value == "shuffled":
            random.shuffle(cards)
        saved = load_progress(path.name)
        if saved:
            self.ask_resume(path.name, saved, cards)
        else:
            self.start(cards, path.name)

    def ask_resume(self, deck, saved, fresh):
        for child in self.resume.winfo_children():
            child.destroy()
        n = len(saved)
        tk.Label(self.resume, bg=CARD_BG, fg=FG, font=(UI_FONT, 13),
                 text=f"Resume {deck} — {n} card{'' if n == 1 else 's'} left?"
                 ).pack(pady=(16, 12))
        row = tk.Frame(self.resume, bg=CARD_BG)
        row.pack(pady=(0, 16))
        Button(row, "Resume", lambda: self._pick(saved, deck)).grid(row=0, column=0, padx=6)
        Button(row, "Start fresh", lambda: self._pick(fresh, deck)).grid(row=0, column=1, padx=6)
        self.resume.grid()

    def _pick(self, cards, deck):
        self.resume.grid_remove()
        self.start(cards, deck)

    def start(self, cards, deck):
        self.queue = cards
        self.deck = deck
        save_progress(self.deck, self.queue)
        self.show("study")
        self.render()

    def back_to_start(self):
        self.resume.grid_remove()
        self.show("start")

    def render(self):
        if not self.queue:
            save_progress(self.deck, [])
            self.show("done")
            return
        card = self.queue[0]
        self.revealed = False
        self._images.clear()
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self._insert(card["front"])
        self.text.insert("end", "\n\nClick or press Space to reveal", "hint")
        self.text.configure(state="disabled")
        self.btn_yes.set_enabled(False)
        self.btn_no.set_enabled(False)
        n = len(self.queue)
        self.progress.configure(text=f"{n} card{'' if n == 1 else 's'} left")

    def reveal(self):
        if self.revealed or not self.queue:
            return
        self.revealed = True
        self.text.configure(state="normal")
        # show the "press Space" hint, then append the back of the card
        hint = self.text.tag_ranges("hint")
        if hint:
            self.text.delete(hint[0], hint[1])
        self.text.insert("end", "\n" + "─" * 24 + "\n", "rule")
        self._insert(self.queue[0]["back"])
        self.text.configure(state="disabled")
        self.text.see("end")
        self.btn_yes.set_enabled(True)
        self.btn_no.set_enabled(True)

    def _insert(self, raw: str):
        for kind, value, display in segments(raw):
            if kind == "text":
                self.text.insert("end", value, "body")
                continue
            image = render_math(value, display)
            if image is None:
                self.text.insert("end", f"${value}$", "body")
            else:
                self._images.append(image)
                if display:
                    self.text.insert("end", "\n", "body")
                self.text.image_create("end", image=image, align="center", padx=2)
                if display:
                    self.text.insert("end", "\n", "body")

    def answer(self, correct: bool):
        if not self.revealed or not self.queue:
            return
        card = self.queue.pop(0)
        if not correct:
            gap = random.randint(MIN_GAP, MAX_GAP)
            self.queue.insert(min(gap, len(self.queue)), card)
        save_progress(self.deck, self.queue)
        self.render()

    def _on_key(self, event):
        if self.current != "study":
            return
        if event.keysym in ("space", "Return"):
            self.reveal()
        elif event.char in ("y", "Y"):
            self.answer(True)
        elif event.char in ("n", "N"):
            self.answer(False)
        elif event.keysym == "Escape":
            self.back_to_start()


def main():
    initial = None
    if len(sys.argv) > 1:
        initial = Path(sys.argv[1])
        if not initial.exists():
            sys.exit(f"No such file: {initial}")
    App(initial).mainloop()


if __name__ == "__main__":
    main()
