# Resolving unread spines from the new close-up photos

Nick re-photographed the spots where spines could not be read. Your job: read the unresolved books from the new photos and record corrections.

Inputs:
- /root/books/fix/unresolved.csv : unresolved catalogue rows with bookcase, column, shelf, position (position = index from the left in /root/books/catalogue/catalogue.csv), the current reading, and the left and right neighbours.
- /root/books/catalogue/catalogue.csv : the full catalogue, for context on each shelf.
- New photos: /root/books/jpg/IMG_05NN_full.jpg (4032x3024) and 1600 px previews IMG_05NN.jpg.

Method:
1. Look at the preview of each photo assigned to you, decide which shelf it shows by matching titles to catalogue.csv.
2. For each unresolved row on that shelf, crop the full-resolution image with PIL (uniquely named script in your own scratch area; crops in /root/books/fix/work/ prefixed with your group name), find the neighbours, and read the target spine. Zoom as needed.
3. Do not guess. Use your knowledge of French literature only to complete a partly legible word whose reading is clear, and mark it "probable".
4. While you are on a shelf, if a new photo plainly shows that another row in catalogue.csv is wrong (wrong title, a book missing from the catalogue, a book listed that is not there), record that too, as kind "other".

Output: /root/books/fix/fixes_<group>.csv with columns:
kind,bookcase,column,shelf,position,author,title,publisher_series,series_number,legibility,notes,photo
- kind: "resolve" for rows from unresolved.csv; "other" for further corrections; "insert_after" when a book is missing (position = the catalogue position it follows); "delete" when a listed row is not a book.
- legibility: certain / probable / illegible (still unreadable).
- notes: short, e.g. "read from IMG_0535; was hidden behind Assouline".

Reply briefly: how many resolved, how many still unreadable, any "other" corrections.
