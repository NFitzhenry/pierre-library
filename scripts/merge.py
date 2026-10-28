"""Merge per-photo transcripts into one catalogue, one record per physical book.

Each physical shelf is taken from the single photo where it is clearest; overlapping
photos are used only through the transcribers' gap-filling. Edge spines belonging to
an adjacent column are dropped (they are catalogued from their own column).
"""
import csv, json, re
T = '/root/books/transcripts'
def rows(photo, shelf, file=None):
    return [r for r in csv.DictReader(open(f'{T}/{file or photo}.csv', encoding='utf-8')) if r['shelf'] == shelf]

S = []  # (bookcase, column, shelf, rows)
def add(bc, col, sh, rs): S.append((bc, col, sh, rs))

# Bookcase 1, column 1 (10 shelves)
for n, (p, s) in enumerate([('IMG_0492','1'),('IMG_0492','2'),('IMG_0492','3'),('IMG_0495','2'),('IMG_0496','1'),
                            ('IMG_0496','2'),('IMG_0498','1'),('IMG_0498','2'),('IMG_0499','2'),('IMG_0500','2')], 1):
    add('Bookcase 1', 'Column 1', n, rows(p, s))
# column 2
for n, (p, s) in enumerate([('IMG_0501','1'),('IMG_0502','1'),('IMG_0502','2'),('IMG_0502','3')], 1):
    add('Bookcase 1', 'Column 2', n, rows(p, s))
# column 3
for n, (p, s) in enumerate([('IMG_0504','1'),('IMG_0504','2'),('IMG_0505','2'),('IMG_0505','3')], 1):
    add('Bookcase 1', 'Column 3', n, rows(p, s))
# column 4: drop spines of the adjacent column at the left edge
def drop_adjacent(rs): return [r for r in rs if 'adjacent bookcase section' not in r['notes']]
c4 = [('IMG_0507','1'),('IMG_0507','2'),('IMG_0508','2'),('IMG_0509','2'),('IMG_0510','2'),('IMG_0511','1'),('IMG_0511','2')]
for n, (p, s) in enumerate(c4, 1):
    add('Bookcase 1', 'Column 4', n, drop_adjacent(rows(p, s)))
r12, r13 = rows('IMG_0512','1'), rows('IMG_0513','1')
add('Bookcase 1', 'Column 4', 8, r12[:23] + r13[12:])   # 0513 pos 13 onward continues after Harry Potter III
# Bookcase 2, left column (shelf 2 holds only flasks)
add('Bookcase 2', 'Left column', 1, rows('IMG_0521','1'))
add('Bookcase 2', 'Left column', 2, [])
add('Bookcase 2', 'Left column', 3, rows('IMG_0516','1'))
add('Bookcase 2', 'Left column', 4, [r for r in rows('IMG_0516','2') if 'adjacent bay' not in r['notes']])
# Bookcase 2, right column
# the 'stack' beside the toy cars is a picture of books, not books (confirmed by Nick)
add('Bookcase 2', 'Right column', 1, [r for r in rows('IMG_0520','1', file='IMG_0519_topright') if 'lying flat' not in r['notes']])
add('Bookcase 2', 'Right column', 2, rows('IMG_0514','1'))
# position 9 'behind the vase' is the edge of the jug, not a book (confirmed by Nick)
add('Bookcase 2', 'Right column', 3, [r for r in rows('IMG_0514','2') if 'adjacent bay' not in r['notes'] and r['position'] != '9'])
add('Bookcase 2', 'Right column', 4, [r for r in rows('IMG_0514','3') if 'adjacent bay' not in r['notes']])

out = []
for bc, col, sh, rs in S:
    for i, r in enumerate(rs, 1):
        out.append({'bookcase': bc, 'column': col, 'shelf': sh, 'position': i,
                    'author': r['author'].strip(), 'title': r['title'].strip(),
                    'publisher_series': r['publisher_series'].strip(), 'series_number': r['series_number'].strip(),
                    'legibility': r['legibility'].strip(), 'notes': r['notes'].strip(), 'source_photo': r['photo']})
cols = list(out[0])
with open('/root/books/catalogue/catalogue.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, cols); w.writeheader(); w.writerows(out)
json.dump(out, open('/root/books/catalogue/catalogue.json', 'w', encoding='utf-8'), ensure_ascii=False)
from collections import Counter
c = Counter((o['bookcase'], o['column'], o['shelf']) for o in out)
for k in sorted(c): print(k, c[k])
print('TOTAL', len(out), 'illegible', sum(o['legibility']=='illegible' for o in out))
