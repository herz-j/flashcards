# flashcards

A tiny flashcard app written in Tkinter.

## Running

```sh
uv run flashcards            # opens the deck picker
uv run flashcards deck.csv   # jumps straight into a deck
```

`uv sync` on first run creates the environment.

## Deck format

A CSV with two columns for the front and back sides.
tabs:

```csv
"What is the gradient of $f$?","$\nabla f = (\partial_x f, \partial_y f)$"
"Multi-line\nquestion","Answer"
```

Text wrapped in `$...$` is typeset as inline math and `$$...$$` as display math. Escape sequences are left alone inside math, so LaTeX commands such as `\nabla`, `\neq` and `\tau` should work.

## Studying

| Key | Action |
| --- | --- |
| `Space` / `Enter` / click | Reveal the back of the card |
| `y` | Got it — the card leaves the queue |
| `n` | Again — the card returns 5–10 cards later |
| `Esc` | Back to the deck picker |

Decks can be taken in file order or shuffled.

## Progress

The remaining queue is saved after every answer, so you can resume closed sessions. Finishing a deck clears its saved progress. State lives in a single JSON file:

- macOS — `~/Library/Application Support/flashcards/progress.json`
- Linux — `$XDG_DATA_HOME/flashcards/progress.json`
- Windows — `%APPDATA%\flashcards\progress.json`

## Drag and drop

Dropping a CSV on the picker needs the `tkdnd` Tcl extension, which `tkinterdnd2` ships as a prebuilt binary per platform *and per Tcl major version*, so it might not work on your machine. File menu should be fine though.

## Requirements

Python 3.12+ with Tkinter

> Note: uv's standalone Python 3.14 builds ship no Tkinter at all, so use 3.12 or 3.13.
