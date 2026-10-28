"""Draw numbered boxes for unresolved books on shelf photos and build a PDF.

Inputs: items.csv, boxes_*.json (full-resolution coordinates), jpg/<photo>_full.jpg
Outputs: marks/out/<photo>_marked.jpg and marks/out/books_to_check.pdf
"""
import csv
import glob
import json
import os
import textwrap

from PIL import Image, ImageDraw, ImageFont

ROOT = '/root/books'
MARKS = f'{ROOT}/marks'
OUT = f'{MARKS}/out'
os.makedirs(OUT, exist_ok=True)

LOCATION = {
    ('IMG_0492', '1'): 'Bookcase 1, column 1, shelf 1',
    ('IMG_0492', '2'): 'Bookcase 1, column 1, shelf 2',
    ('IMG_0492', '3'): 'Bookcase 1, column 1, shelf 3',
    ('IMG_0496', '2'): 'Bookcase 1, column 1, shelf 6',
    ('IMG_0500', '2'): 'Bookcase 1, column 1, shelf 10 (bottom)',
    ('IMG_0501', '1'): 'Bookcase 1, column 2, shelf 1',
    ('IMG_0502', '1'): 'Bookcase 1, column 2, shelf 2',
    ('IMG_0501', '3'): 'Bookcase 1, column 2, shelf 3',
    ('IMG_0502', '3'): 'Bookcase 1, column 2, shelf 4',
    ('IMG_0504', '1'): 'Bookcase 1, column 3, shelf 1',
    ('IMG_0504', '2'): 'Bookcase 1, column 3, shelf 2',
    ('IMG_0505', '2'): 'Bookcase 1, column 3, shelf 3',
    ('IMG_0505', '3'): 'Bookcase 1, column 3, shelf 4',
    ('IMG_0507', '1'): 'Bookcase 1, column 4, shelf 1',
    ('IMG_0507', '2'): 'Bookcase 1, column 4, shelf 2',
    ('IMG_0508', '2'): 'Bookcase 1, column 4, shelf 3',
    ('IMG_0511', '1'): 'Bookcase 1, column 4, shelf 6',
    ('IMG_0513', '1'): 'Bookcase 1, column 4, shelf 8 (bottom)',
    ('IMG_0514', '2'): 'Bookcase 2, right column, shelf 3',
    ('IMG_0516', '2'): 'Bookcase 2, left column, shelf 4',
    ('IMG_0520', 'top-right'): 'Bookcase 2, right column, shelf 1 (top)',
}

BOOK_COL = (230, 20, 20)
SHELF_COL = (255, 140, 0)
FONT_B = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
FONT_R = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'

items = {r['id']: r for r in csv.DictReader(open(f'{MARKS}/items.csv', encoding='utf-8'))}
boxes = {}
for f in glob.glob(f'{MARKS}/boxes_*.json'):
    for b in json.load(open(f, encoding='utf-8')):
        if str(b["id"]) in items: boxes[str(b["id"])] = b
missing = sorted(set(items) - set(boxes))
if missing:
    print('WARNING: no box for items', missing)


def sort_key(i):
    return (0, int(i)) if i.isdigit() else (1, i)


photos = {}
for i in sorted(boxes, key=sort_key):
    photos.setdefault(items[i]['photo'], []).append(i)

PAGE_W = 2000
pages = []
for photo in sorted(photos):
    ids = photos[photo]
    im = Image.open(f'{ROOT}/jpg/{photo}_full.jpg').convert('RGB')
    d = ImageDraw.Draw(im)
    lab_font = ImageFont.truetype(FONT_B, 90)
    for i in ids:
        b = boxes[i]
        shelf = items[i]['kind'] == 'shelf'
        col = SHELF_COL if shelf else BOOK_COL
        d.rectangle([b['x0'], b['y0'], b['x1'], b['y1']], outline=col, width=16 if shelf else 12)
        label = i
        tw, th = d.textbbox((0, 0), label, font=lab_font)[2:]
        # label above the box, or inside the top if no room
        lx = max(0, min(b['x0'], im.width - tw - 30))
        ly = b['y0'] - th - 40 if b['y0'] - th - 40 > 0 else b['y0'] + 10
        d.rectangle([lx, ly, lx + tw + 30, ly + th + 30], fill=col)
        d.text((lx + 15, ly + 5), label, fill='white', font=lab_font)
    im.thumbnail((PAGE_W, PAGE_W))
    im.save(f'{OUT}/{photo}_marked.jpg', quality=88)

    # legend panel beneath the photo
    f_h = ImageFont.truetype(FONT_B, 40)
    f_t = ImageFont.truetype(FONT_R, 30)
    f_tb = ImageFont.truetype(FONT_B, 30)
    lines = []
    for i in ids:
        r = items[i]
        loc = LOCATION.get((photo, r['shelf']), f"{photo}, shelf {r['shelf']}")
        if r['kind'] == 'shelf':
            lines.append(('b', f"{i}.  {r['what']}  ({loc})"))
        else:
            lines.append(('b', f"{i}.  {loc}: {r['what']}"))
            lines.append(('r', f"     between  {r['left_neighbour']}  and  {r['right_neighbour']}"))
            if b := boxes[i].get('note'):
                lines.append(('r', f"     note: {b}"))
            lines.append(('r', '     Author: ____________________   Title: ______________________________'))
        lines.append(('r', ''))
    wrapped = []
    for kind, s in lines:
        for w in (textwrap.wrap(s, 110, subsequent_indent='     ') or ['']):
            wrapped.append((kind, w))
    legend_h = 90 + 42 * len(wrapped)
    page = Image.new('RGB', (PAGE_W, im.height + legend_h + 40), 'white')
    page.paste(im, ((PAGE_W - im.width) // 2, 0))
    pd = ImageDraw.Draw(page)
    y = im.height + 25
    pd.text((40, y), f'Photo {photo}', fill='black', font=f_h)
    y += 65
    for kind, s in wrapped:
        pd.text((40, y), s, fill='black', font=f_tb if kind == 'b' else f_t)
        y += 42
    pages.append(page)

pages[0].save(f'{OUT}/books_to_check.pdf', save_all=True, append_images=pages[1:], resolution=150)
print('pages:', len(pages), 'items drawn:', len(boxes))
