"""Fetch small cover thumbnails from Open Library for matched books.

Input:  /root/books/enrich/bnf_matches.json, /root/books/catalogue/catalogue_final.json
Output: /root/books/enrich/covers.json      key -> data URI (JPEG, 60 px wide)
        /root/books/enrich/cover_source.json key -> "isbn" (cover of this edition) or "title" (cover of some edition of the work)
Downloads are cached in /root/books/enrich/img/ so reruns do not re-fetch.

Order of preference: the ISBN from the BnF record (identifies the edition); otherwise an Open Library title and
author search, which may return the cover of a different edition.
"""
import base64
import concurrent.futures as cf
import io
import json
import os
import re
import time
import urllib.parse
import urllib.request

from PIL import Image

E = '/root/books/enrich'
IMG = f'{E}/img'
UA = {'User-Agent': 'BookCatalogue/1.0 (private family library catalogue)'}
os.makedirs(IMG, exist_ok=True)


def get(url, binary=True):
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
                return r.read() if binary else r.read().decode('utf-8')
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            time.sleep(2 * (attempt + 1))
        except Exception:
            time.sleep(2 * (attempt + 1))
    return None


def thumb(raw):
    try:
        im = Image.open(io.BytesIO(raw)).convert('RGB')
    except Exception:
        return None
    if im.width < 20 or im.height < 30:  # Open Library returns a 1x1 placeholder for missing covers
        return None
    im.thumbnail((60, 92))
    b = io.BytesIO()
    im.save(b, 'JPEG', quality=72)
    return 'data:image/jpeg;base64,' + base64.b64encode(b.getvalue()).decode()


def cached(name, url):
    f = os.path.join(IMG, name)
    if os.path.exists(f):
        return open(f, 'rb').read() or None
    raw = get(url)
    open(f, 'wb').write(raw or b'')
    time.sleep(0.2)
    return raw


def cover_for(key, book, m):
    isbn = re.sub(r'[^0-9Xx]', '', (m or {}).get('isbn', ''))
    if len(isbn) in (10, 13):
        raw = cached(f'isbn_{isbn}.jpg', f'https://covers.openlibrary.org/b/isbn/{isbn}-M.jpg?default=false')
        t = raw and thumb(raw)
        if t:
            return t, 'isbn'
    if not book['title']:
        return None, None
    q = {'title': book['title'], 'limit': 3, 'fields': 'cover_i,title,author_name'}
    if book['author']:
        q['author'] = book['author'].split(';')[0]
    js = get('https://openlibrary.org/search.json?' + urllib.parse.urlencode(q), binary=False)
    try:
        docs = json.loads(js or '{}').get('docs', [])
    except ValueError:
        docs = []
    for d in docs:
        if d.get('cover_i'):
            raw = cached(f"id_{d['cover_i']}.jpg", f"https://covers.openlibrary.org/b/id/{d['cover_i']}-M.jpg")
            t = raw and thumb(raw)
            if t:
                return t, 'title'
    return None, None


def main():
    cat = json.load(open('/root/books/catalogue/catalogue_final.json', encoding='utf-8'))
    bnf = json.load(open(f'{E}/bnf_matches.json', encoding='utf-8'))
    covers = json.load(open(f'{E}/covers.json', encoding='utf-8')) if os.path.exists(f'{E}/covers.json') else {}
    src = json.load(open(f'{E}/cover_source.json', encoding='utf-8')) if os.path.exists(f'{E}/cover_source.json') else {}
    todo = [b for b in cat if b['match_key'] not in src]
    with cf.ThreadPoolExecutor(6) as ex:
        futs = {ex.submit(cover_for, b['match_key'], b, bnf.get(b['match_key'])): b for b in todo}
        for i, f in enumerate(cf.as_completed(futs), 1):
            b = futs[f]
            try:
                t, s = f.result()
            except Exception:
                t, s = None, None
            src[b['match_key']] = s or 'none'
            if t:
                covers[b['match_key']] = t
            if i % 100 == 0:
                print(i, 'of', len(todo), flush=True)
    json.dump(covers, open(f'{E}/covers.json', 'w', encoding='utf-8'))
    json.dump(src, open(f'{E}/cover_source.json', 'w', encoding='utf-8'))
    from collections import Counter
    print(Counter(src.values()), 'size', sum(len(v) for v in covers.values()) // 1024, 'KB')


if __name__ == '__main__':
    main()
