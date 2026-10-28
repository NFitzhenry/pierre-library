"""Match each catalogue row to a BnF bibliographic record (SRU API, UNIMARC).

Input:  /root/books/catalogue/catalogue_final.json
Output: /root/books/enrich/bnf_matches.json  (one entry per catalogue row, keyed by bookcase|column|shelf|position)
        raw responses cached in /root/books/enrich/raw/<hash>.xml so reruns do not re-query

Strategy per book:
  1. title words + author surname, printed text only;
  2. if nothing, title words only.
Each candidate record is scored on title similarity, author match, collection match and collection
number match. Confidence:
  edition  - collection and number both match (the copy on the shelf is identified)
  work     - title and author match, edition not determined (earliest matching record kept for the year)
  weak     - best candidate only partly matches; for manual checking
  none     - no candidate
"""
import concurrent.futures as cf
import hashlib
import html
import json
import os
import re
import time
import unicodedata
import urllib.parse
import urllib.request

CAT = '/root/books/catalogue/catalogue_final.json'
OUT = '/root/books/enrich/bnf_matches.json'
RAW = '/root/books/enrich/raw'
API = 'https://catalogue.bnf.fr/api/SRU?version=1.2&operation=searchRetrieve&recordSchema=unimarcxchange&maximumRecords=25&query='
UA = {'User-Agent': 'BookCatalogue/1.0 (private family library catalogue)'}

STOP = set('le la les l un une des de du d et a au aux en sur pour par dans ou the of and'.split())


def norm(s):
    s = unicodedata.normalize('NFD', s or '').encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9 ]+', ' ', s)


def words(s):
    return [w for w in norm(s).split() if w not in STOP and len(w) > 1]


def surname(a):
    a = re.split(r'[;/&,]| et ', a or '')[0].strip()
    w = a.split()
    if not w:
        return ''
    if len(w) > 1 and w[-2].lower() in ('de', 'du', 'le', 'la', 'van', 'von', 'di', 'da', 'des'):
        return ' '.join(w[-2:])
    return w[-1]


def fetch(q):
    os.makedirs(RAW, exist_ok=True)
    f = os.path.join(RAW, hashlib.md5(q.encode()).hexdigest() + '.xml')
    if os.path.exists(f):
        return open(f, encoding='utf-8').read()
    url = API + urllib.parse.quote(q)
    for attempt in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
                x = r.read().decode('utf-8')
            open(f, 'w', encoding='utf-8').write(x)
            time.sleep(0.3)
            return x
        except Exception as e:  # network errors and 429s: back off and retry
            time.sleep(2 * (attempt + 1))
            err = e
    raise RuntimeError(f'BnF query failed: {q} ({err})')


def sub(rec, tag, code):
    out = []
    for m in re.finditer(rf'<mxc:datafield tag="{tag}"[^>]*>(.*?)</mxc:datafield>', rec, re.S):
        for s in re.finditer(rf'<mxc:subfield code="{code}">(.*?)</mxc:subfield>', m.group(1), re.S):
            out.append(html.unescape(s.group(1)).strip())
    return out


def parse(x):
    recs = []
    for rec in re.findall(r'<srw:record>.*?</srw:record>', x, re.S):
        ark = re.search(r'<srw:recordIdentifier>(.*?)</srw:recordIdentifier>', rec)
        date = (sub(rec, '210', 'd') or sub(rec, '214', 'd') or [''])[0]
        y = re.search(r'(1[5-9]\d\d|20\d\d)', date)
        recs.append({
            'ark': ark.group(1) if ark else '',
            'title': ' '.join((sub(rec, '200', 'a') or [''])[:1] + sub(rec, '200', 'e')[:1]).strip(),
            'resp': (sub(rec, '200', 'f') or [''])[0],
            'authors': [' '.join(filter(None, [(sub_one(m, 'b')), sub_one(m, 'a')])) for m in fields(rec, '700') + fields(rec, '701')],
            'publisher': (sub(rec, '210', 'c') or sub(rec, '214', 'c') or [''])[0],
            'place': (sub(rec, '210', 'a') or sub(rec, '214', 'a') or [''])[0],
            'year': int(y.group(1)) if y else None,
            'collection': (sub(rec, '225', 'a') or sub(rec, '410', 't') or [''])[0],
            'number': (sub(rec, '225', 'v') or sub(rec, '410', 'v') or [''])[0],
            'isbn': (sub(rec, '010', 'a') or [''])[0],
            'pages': (sub(rec, '215', 'a') or [''])[0],
        })
    return recs


def fields(rec, tag):
    return re.findall(rf'<mxc:datafield tag="{tag}"[^>]*>(.*?)</mxc:datafield>', rec, re.S)


def sub_one(field, code):
    m = re.search(rf'<mxc:subfield code="{code}">(.*?)</mxc:subfield>', field, re.S)
    return html.unescape(m.group(1)).strip() if m else ''


SERIES_ALIASES = {
    'le livre de poche': 'livre de poche', 'folio': 'folio', 'points': 'points', '10 18': '10 18',
    'pocket': 'pocket', 'j ai lu': 'j ai lu', 'que sais je': 'que sais je', 'bouquins': 'bouquins',
    'babel': 'babel', 'serie noire': 'serie noire', 'l imaginaire': 'imaginaire', 'folio classique': 'folio',
}


def series_key(s):
    n = norm(s)
    n = re.sub(r'\b(collection|coll)\b', ' ', n)
    n = re.sub(r'\b(gallimard|actes sud|hachette)\b', ' ', n) if any(k in n for k in ('folio', 'imaginaire', 'serie noire', 'babel', 'livre de poche')) else n
    n = ' '.join(n.split())
    for k, v in SERIES_ALIASES.items():
        if k in n:
            return v
    return n


def score(book, r):
    bw, rw = set(words(book['title'])), set(words(r['title']))
    tsim = len(bw & rw) / max(1, len(bw)) if bw else 0
    sn = norm(surname(book['author']))
    auth = 1 if sn and (sn in norm(r['resp']) or any(sn in norm(a) for a in r['authors'])) else 0
    bs = series_key(book['publisher_series'])
    pw = norm(book['publisher_series']).split()
    coll = 1 if bs and (bs in series_key(r['collection']) or bs in norm(r['publisher']) or (pw and pw[0] not in ('le', 'la', 'les', 'editions') and norm(r['publisher']).strip().startswith(pw[0]) and not r['collection'])) else 0
    num = 1 if book['series_number'] and re.sub(r'\D', '', book['series_number']) and \
        re.sub(r'\D', '', book['series_number']) == re.sub(r'\D', '', r['number'] or '') else 0
    return tsim, auth, coll, num


def match(book):
    t = ' '.join(words(book['title'])[:6])
    a = norm(surname(book['author']))
    if not t:
        return {'confidence': 'none', 'reason': 'no title'}
    queries = []
    if a:
        queries.append(f'bib.title all "{t}" and bib.author all "{a}" and bib.doctype any "a"')
    queries.append(f'bib.title all "{t}" and bib.doctype any "a"')
    cands = []
    for q in queries:
        cands = parse(fetch(q))
        if cands:
            break
    if not cands:
        return {'confidence': 'none', 'reason': 'no BnF record found'}
    scored = [(score(book, r), r) for r in cands]
    full = [(s, r) for s, r in scored if s[0] >= 0.75 and (s[1] or not book['author'])]
    ed = [(s, r) for s, r in full if s[2] and s[3]]
    if ed:
        s, r = ed[0]
        return {'confidence': 'edition', **r}
    coll = [(s, r) for s, r in full if s[2]]
    if coll:  # right series, number unknown or not printed in the record: take the earliest in that series
        s, r = sorted(coll, key=lambda sr: sr[1]['year'] or 9999)[0]
        return {'confidence': 'edition' if not book['series_number'] else 'work', **r}
    if full:
        first = sorted(full, key=lambda sr: sr[1]['year'] or 9999)[0][1]
        return {'confidence': 'work', **first}
    s, r = max(scored, key=lambda sr: (sr[0][0] + sr[0][1], -(sr[1]['year'] or 9999)))
    return {'confidence': 'weak', 'score': list(s), **r}


def key(b):
    return f"{b['bookcase']}|{b['column']}|{b['shelf']}|{b['position']}"


def main():
    cat = json.load(open(CAT, encoding='utf-8'))
    done = json.load(open(OUT, encoding='utf-8')) if os.path.exists(OUT) else {}
    todo = [b for b in cat if key(b) not in done and b['title']]
    with cf.ThreadPoolExecutor(4) as ex:
        futs = {ex.submit(match, b): b for b in todo}
        for i, f in enumerate(cf.as_completed(futs), 1):
            b = futs[f]
            try:
                done[key(b)] = f.result()
            except Exception as e:
                done[key(b)] = {'confidence': 'error', 'reason': str(e)}
            if i % 50 == 0:
                json.dump(done, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False)
                print(i, 'of', len(todo), flush=True)
    for b in cat:
        if not b['title']:
            done.setdefault(key(b), {'confidence': 'none', 'reason': 'title not read'})
    json.dump(done, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False)
    from collections import Counter
    print(Counter(v['confidence'] for v in done.values()))


if __name__ == '__main__':
    main()
