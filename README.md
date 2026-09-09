# flashcards

A tiny flashcard deck runner. Load a two-column CSV, drill it, and pick up
where you left off.

## Running

```sh
uv run flashcards            # opens the deck picker
uv run flashcards deck.csv   # jumps straight into a deck
```

`uv sync` on first run creates the environment; no other setup is needed.

Decks can also be dragged onto the picker from Finder — see *Drag and drop*
below for when that is available.

## Deck format

A CSV with two columns — front, back. Quoted fields, embedded commas and
doubled `""` quotes are handled, and `\n` / `\t` become real line breaks and
tabs:

```csv
"What is the gradient of $f$?","$\nabla f = (\partial_x f, \partial_y f)$"
"Multi-line\nquestion","Answer"
```

Text wrapped in `$...$` is typeset as inline math and `$$...$$` as display
math. Escape sequences are left alone inside math, so LaTeX commands such as
`\nabla`, `\neq` and `\tau` survive intact. A formula that will not parse falls
back to showing its source rather than failing the card.

## Studying

| Key | Action |
| --- | --- |
| `Space` / `Enter` / click | Reveal the back of the card |
| `y` | Got it — the card leaves the queue |
| `n` | Again — the card returns 5–10 cards later |
| `Esc` | Back to the deck picker |

Decks can be taken in file order or shuffled.

## Progress

The remaining queue is saved after every answer, keyed by deck filename, so
closing mid-session and reopening the same file offers to resume. Finishing a
deck clears its saved progress. State lives in a single JSON file:

- macOS — `~/Library/Application Support/flashcards/progress.json`
- Linux — `$XDG_DATA_HOME/flashcards/progress.json`
- Windows — `%APPDATA%\flashcards\progress.json`

## Drag and drop

Dropping a CSV on the picker needs the `tkdnd` Tcl extension, which
`tkinterdnd2` ships as a prebuilt binary per platform *and per Tcl major
version*. Two facts collide here:

- every uv-managed Python ships Tk 9.0.3;
- `tkinterdnd2` bundles Tcl 9 builds for every platform **except** Intel macOS.

So on an Intel Mac a uv-managed interpreter cannot load `tkdnd` at all.
`.python-version` therefore points at a python.org interpreter, which carries
Tk 8.6 and does have a matching binary. Apple Silicon has an `osx-arm64-tcl9`
build and needs none of this.

The pin is an absolute path, so it is specific to this machine. On another
machine, point it at a Tk 8.6 interpreter or delete it — deleting it falls back
to a managed Python, and the app runs fine without drop support: the picker
stays clickable and its wording changes to match.

## Requirements

Python 3.12+ with Tkinter. Both extras degrade rather than break — without
matplotlib, formulas show as literal source; without a loadable `tkdnd`, the
picker is click-only.

> Note: uv's standalone Python 3.14 builds ship no Tkinter at all, so a managed
> 3.14 cannot run this app. 3.12 and 3.13 are fine.
