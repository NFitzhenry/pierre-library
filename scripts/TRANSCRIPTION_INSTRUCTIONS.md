# Spine transcription instructions

Context: photos of a private library of mostly French books (paperbacks such as Folio, Livre de Poche, J'ai lu, Points, 10/18, Pocket; grand-format Gallimard nrf, Grasset, Seuil, Minuit, Albin Michel; some guidebooks). Goal: a catalogue with one row per visible book spine.

Images (already rotated correctly, 4032 x 3024):
- Full resolution: /root/books/jpg/IMG_XXXX_full.jpg
- 1600 px preview: /root/books/jpg/IMG_XXXX.jpg

## Method
1. Read the preview to identify the shelves. Number shelves from the top, counting only shelves whose spines are mostly visible (ignore the cut-off bottom edge of the shelf above at the very top of the frame, unless titles are legible there; if so, call it shelf 0).
2. For each shelf, crop the FULL-resolution image with Python/PIL into segments no wider than about 1000 px of original width, with about 100 px overlap between segments, and Read each crop. Save crops in /root/books/crops/ (create it). Zoom further (smaller crop) wherever text is small or faint. Do not rely on the preview for titles.
3. Record every book left to right, one row each. At segment overlaps make sure each spine is listed once.
4. Do not guess. If you can read the author but not the title, give the author and leave the title blank. Use your knowledge of French literature only to resolve a partly legible word when the reading is clear (e.g. "Le rocher de Tan..." on a Maalouf spine), and then mark legibility "probable".
5. Objects (candle holders, vases, routers) are not rows. Books lying flat or with the back cover outward ARE rows (legibility "illegible" if nothing can be read, note "reversed").

## Output
Write one CSV per photo to /root/books/transcripts/IMG_XXXX.csv (UTF-8, header row, quote fields with commas) with columns:

photo,shelf,position,author,title,publisher_series,series_number,legibility,notes

- author: as printed, normalised to "Firstname Lastname" (e.g. spine "Beauvoir" -> "Simone de Beauvoir" only if certain; otherwise exactly as printed).
- title: as printed, with French capitalisation (first word and proper nouns capitalised).
- publisher_series: e.g. Folio, Le Livre de Poche, J'ai lu, Points, 10/18, Pocket, Gallimard (nrf), Grasset, Seuil, Minuit, Albin Michel, Actes Sud. Blank if not visible.
- series_number: the collection number printed on the spine if visible (e.g. 1750), else blank.
- legibility: certain / probable / illegible.
- notes: e.g. "reversed", "partly hidden by cable", "glare", "volume II", "inscription visible", "leaning, cut off", "lying flat".

Also write /root/books/transcripts/IMG_XXXX_shelves.txt with, for each shelf, the number of books and the first three and last three titles, so overlapping photos can be matched later.

Finish by replying with a short summary: photos done, row count per shelf, number of illegible rows, and anything odd (handwriting, duplicates, damage).
