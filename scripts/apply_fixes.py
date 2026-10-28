"""Apply corrections from the close-up photos (fix/fixes_*.csv) to the merged catalogue.

Input: catalogue.json (from merge.py), /root/books/fix/fixes_*.csv
Output: catalogue_final.json / catalogue_final.csv, and shelves.html rebuilt from the template.
"""
import csv
import os
import glob
import json

C = '/root/books/catalogue'
cat = json.load(open(f'{C}/catalogue.json', encoding='utf-8'))
loc = lambda r: (r['bookcase'], r['column'], int(r['shelf']), int(r['position']))
index = {loc(o): o for o in cat}

fixes = []
for f in sorted(glob.glob('/root/books/fix/fixes_*.csv')):
    fixes += list(csv.DictReader(open(f, encoding='utf-8')))

applied, missing, inserts, deletes = 0, [], [], set()
for fx in fixes:
    k = loc(fx)
    kind = fx['kind'].strip()
    if kind == 'insert_after':
        inserts.append(fx)
        continue
    if k not in index:
        missing.append(fx)
        continue
    if kind == 'delete':
        deletes.add(k)
        continue
    o = index[k]
    for fld in ('author', 'title', 'publisher_series', 'series_number', 'legibility'):
        v = (fx.get(fld) or '').strip()
        if v:
            o[fld] = v
    note = (fx.get('notes') or '').strip()
    if note:
        o['notes'] = note
    if fx.get('photo'):
        o['source_photo'] = fx['photo'].strip()
    applied += 1

out = []
for o in cat:
    if loc(o) in deletes:
        continue
    out.append(o)
    for fx in inserts:
        if loc(fx) == loc(o):
            out.append({'bookcase': o['bookcase'], 'column': o['column'], 'shelf': o['shelf'], 'position': 0,
                        'author': fx['author'].strip(), 'title': fx['title'].strip(),
                        'publisher_series': fx['publisher_series'].strip(), 'series_number': fx['series_number'].strip(),
                        'legibility': fx['legibility'].strip() or 'certain', 'notes': fx['notes'].strip(),
                        'source_photo': fx['photo'].strip()})
# renumber positions within each shelf
pos = {}
for o in out:
    s = (o['bookcase'], o['column'], o['shelf'])
    pos[s] = pos.get(s, 0) + 1
    o['position'] = pos[s]
# Author names: tidy spacing and Unicode, and expand a bare surname ("Duras") to the full name
# used elsewhere in the catalogue ("Marguerite Duras") when exactly one full name has that surname.
import unicodedata
def _n(s):
    return ' '.join(unicodedata.normalize('NFC', s or '').split())
full = {}
for o in out:
    o['author'] = _n(o['author'])
    w = o['author'].split()
    if len(w) > 1 and not any(c in o['author'] for c in ';/&'):
        full.setdefault(w[-1].lower(), set()).add(o['author'])
for o in out:
    w = o['author'].split()
    if len(w) == 1 and len(full.get(w[0].lower(), ())) == 1:
        o['author'] = next(iter(full[w[0].lower()]))
# BnF matches are keyed on the final location; the build is deterministic, so the key is stable
for o in out:
    o['match_key'] = f"{o['bookcase']}|{o['column']}|{o['shelf']}|{o['position']}"

json.dump(out, open(f'{C}/catalogue_final.json', 'w', encoding='utf-8'), ensure_ascii=False)
with open(f'{C}/catalogue_final.csv', 'w', newline='', encoding='utf-8') as fh:
    w = csv.DictWriter(fh, list(out[0]))
    w.writeheader()
    w.writerows(out)

# BnF matches and covers, when available
BNF = '/root/books/enrich/bnf_matches.json'
COV = '/root/books/enrich/covers.json'
bnf = json.load(open(BNF, encoding='utf-8')) if os.path.exists(BNF) else {}
covers_by_key = json.load(open(COV, encoding='utf-8')) if os.path.exists(COV) else {}
CSRC = '/root/books/enrich/cover_source.json'
cover_src = json.load(open(CSRC, encoding='utf-8')) if os.path.exists(CSRC) else {}
data, covers = [], {}
for i, o in enumerate(out):
    d = {'c': o['bookcase'], 'o': o['column'], 's': o['shelf'], 'i': o['position'], 'a': o['author'], 't': o['title'],
         'p': o['publisher_series'], 'k': o['series_number'], 'l': o['legibility'], 'n': o['notes']}
    m = bnf.get(o.get('match_key', ''), {})
    conf = m.get('confidence')
    if conf == 'work' and not o['author']:
        conf = 'weak'  # without an author, a title-only match is too often a different book
    if conf == 'edition':
        d.update({'cf': conf, 'y': m.get('year'), 'pb': ' '.join((m.get('publisher') or '').split()),
                  'pg': m.get('pages', ''), 'isbn': m.get('isbn', ''), 'ark': m.get('ark', '')})
    elif conf == 'work':
        # the earliest matching record: a first-publication date for the work, not the date of this copy
        d.update({'cf': conf, 'fy': m.get('year'), 'ark': m.get('ark', '')})
    elif m:
        d['cf'] = conf
    if o.get('match_key') in covers_by_key:
        covers[i] = covers_by_key[o['match_key']]
        if cover_src.get(o['match_key']) == 'title' or conf != 'edition':
            d['cs'] = 'title'
    data.append(d)
tpl = open(f'{C}/shelves_template.html', encoding='utf-8').read()
js = lambda v: json.dumps(v, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
open(f'{C}/shelves.html', 'w', encoding='utf-8').write(tpl.replace('__DATA__', js(data)).replace('__COVERS__', js(covers)))

still = [o for o in out if o['legibility'] == 'illegible' or not o['title']]
print(f'fixes read {len(fixes)}, applied {applied}, inserted {len(inserts)}, deleted {len(deletes)}, '
      f'unmatched {len(missing)}; books {len(out)}; still unresolved {len(still)}')
for m in missing:
    print('UNMATCHED', m['kind'], loc(m), m['author'], m['title'])
for o in still:
    print('STILL', o['bookcase'], o['column'], o['shelf'], o['position'], o['author'], '|', o['notes'][:70])
