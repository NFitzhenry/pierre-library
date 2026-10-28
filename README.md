# La bibliothèque de Pierre / Pierre's library

A catalogue of the 1,034 books on Pierre's two bookcases, read from photographs taken on 28 October 2026.

**Open the catalogue:** https://nfitzhenry.github.io/pierre-library/

The page draws both bookcases shelf by shelf. Hovering over or tapping a spine shows its catalogue card: author, title, series and number, publisher and year from the BnF catalogue, a cover where one was found, and the book's place on the shelf. The page has five views: the shelves, a sortable list, an index of authors, summary figures, and a description of the collection. It opens in French; an EN/FR switch sits on the catalogue card.

## Contents

| Path | What it is |
|---|---|
| `index.html` | The catalogue page. Self-contained: data, covers and images are built into the file. |
| `data/catalogue.csv`, `data/catalogue.json` | One row per book: bookcase, column, shelf, position from the left, author, title, publisher or series, series number, how legible the spine was, notes, and the photo it was read from. |
| `data/bnf_matches.json` | The matching record in the catalogue of the Bibliothèque nationale de France for each book: publisher, year, pages, ISBN, ARK identifier and match confidence (`edition` = the copy on the shelf identified; `work` = the work identified but not the edition). |
| `data/cover_source.json` | For each book, whether its cover image is of the same edition (`isbn`), of another edition (`title`), or not found (`none`). Covers come from Open Library. |
| `data/transcripts/` | The spine transcriptions made from each photograph, before overlapping photos were merged. |
| `data/corrections/` | Corrections made from the close-up photographs and by hand. |
| `scripts/` | The scripts that build the catalogue and the page (see below). |
| `assets/` | The sofa cut out of a photograph, the framed portrait, and the marked-up PDF of books that were checked on the shelves. |

## Rebuilding

The scripts expect the working layout used when the catalogue was made (`/root/books/...`); adjust the paths at the top of each script to rebuild elsewhere.

1. `merge.py` merges the per-photo transcripts into one row per physical book.
2. `apply_fixes.py` applies the corrections, joins the BnF matches and covers, and writes `index.html` from `shelves_template.html`.
3. `match_bnf.py` queries the BnF SRU API for each book (responses are cached).
4. `fetch_covers.py` fetches cover thumbnails from Open Library.

## Sources

- Bibliothèque nationale de France, catalogue général, SRU API: https://catalogue.bnf.fr/api
- Open Library covers: https://openlibrary.org/dev/docs/api/covers
- *Girl with a Pearl Earring*, Johannes Vermeer, c. 1665, Mauritshuis, The Hague; public-domain image via Wikimedia Commons.
