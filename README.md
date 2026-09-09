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

Text wrapped in `$...$` is typeset as inline math and `$$...$$` as display math. 

## Studying

| Key | Action |
| --- | --- |
| `Space` / `Enter` / click | Reveals the back of the card |
| `y` | Removes the card from the session deck |
| `n` | Adds the card back to the queue |
| `Esc` | Back to the deck picker |

Decks can be taken in file order or shuffled.

## Progress

The remaining queue is saved after every answer, so you can resume closed sessions. Finishing a deck clears its saved progress. State lives in a single JSON file:

- macOS — `~/Library/Application Support/flashcards/progress.json`
- Linux — `$XDG_DATA_HOME/flashcards/progress.json`
- Windows — `%APPDATA%\flashcards\progress.json`

## Requirements

Python 3.12+ with Tkinter
 
For some reason uv's standalone Python 3.14 builds ship no Tkinter at all, so use 3.12 or 3.13.
