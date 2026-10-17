#!/usr/bin/env python3
"""Αρχείο κληρώσεων ΚΙΝΟ σε δυαδικά αρχεία ανά μήνα (UTC): data/kino/YYYY-MM.bin + index.json.
Εγγραφή 31 bytes: id(uint32 LE) · drawTime σε δευτερόλεπτα (uint32 LE) · 20 αριθμοί με σειρά κλήρωσης · 3 αριθμοί 2ης ευκαιρίας (0 = κανένας).
Χρήση:  python3 tools/archive.py update            → φέρνει από το API ό,τι λείπει ως σήμερα (για το GitHub Action)
        python3 tools/archive.py merge a.json b.json → προσθέτει draws από αρχεία [[id,t_ms,list,sc?],...] ή {"draws":[...]}"""
import json, os, struct, sys, time, datetime, urllib.request
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'kino')
API = 'https://api.opap.gr/draws/v3.0/1100'
REC = struct.Struct('<II20B3B')

def month_of(t_ms): return datetime.datetime.fromtimestamp(t_ms/1000, datetime.timezone.utc).strftime('%Y-%m')

def load_all():
    d = {}
    if not os.path.isdir(ROOT): return d
    for f in sorted(os.listdir(ROOT)):
        if not f.endswith('.bin'): continue
        b = open(os.path.join(ROOT, f), 'rb').read()
        for i in range(0, len(b), REC.size):
            r = REC.unpack_from(b, i)
            sc = [x for x in r[22:25] if x]
            d[r[0]] = [r[0], r[1]*1000, list(r[2:22]), sc]
    return d

def month_bits(rows):
    """bits/YYYY-MM.bin: για κάθε αριθμό 1..80 ένα bitset W=ceil(n/32) λέξεων uint32 LE· bit i = βγήκε στην i-οστή κλήρωση του μήνα (με σειρά id)."""
    W = (len(rows) + 31) // 32; B = [[0] * W for _ in range(80)]
    for i, x in enumerate(rows):
        for v in x[2]: B[v - 1][i >> 5] |= 1 << (i & 31)
    return b''.join(struct.pack('<%dI' % W, *r) for r in B)

def save_all(d):
    os.makedirs(ROOT, exist_ok=True)
    by = {}
    for k in sorted(d):
        x = d[k]
        if len(x[2]) != 20: continue
        by.setdefault(month_of(x[1]), []).append(x)
    files = []
    for m, rows in sorted(by.items()):
        buf = b''.join(REC.pack(x[0], x[1]//1000, *x[2], *((list(x[3]) + [0, 0, 0])[:3])) for x in rows)
        p = os.path.join(ROOT, m + '.bin')
        if not os.path.exists(p) or open(p, 'rb').read() != buf: open(p, 'wb').write(buf)
        bits = month_bits(rows); pb = os.path.join(ROOT, 'bits', m + '.bin')
        os.makedirs(os.path.dirname(pb), exist_ok=True)
        if not os.path.exists(pb) or open(pb, 'rb').read() != bits: open(pb, 'wb').write(bits)
        files.append({'f': m + '.bin', 'n': len(rows), 'min': rows[0][0], 'max': rows[-1][0]})
    total = sum(f['n'] for f in files)
    json.dump({'v': 1, 'rec': REC.size, 'total': total, 'updated': int(time.time()), 'files': files}, open(os.path.join(ROOT, 'index.json'), 'w'), separators=(',', ':'))
    return total

def add(d, rows):
    n = 0
    for x in rows:
        x = list(x) + [[]] * (4 - len(x))
        old = d.get(x[0])
        if old is None or (not old[3] and x[3]): d[x[0]] = [x[0], x[1], list(x[2]), list(x[3] or [])]; n += old is None
    return n

def get(u):
    for a in range(8):
        try:
            with urllib.request.urlopen(u + '&_=%d' % time.time_ns(), timeout=30) as r: return json.load(r)
        except Exception: time.sleep(2 * (a + 1))
    raise RuntimeError('API απέτυχε: ' + u)

def fetch_day(ds):
    f = get(f'{API}/draw-date/{ds}/{ds}?page=0&size=10'); rows = list(f['content'])
    for p in range(1, f['totalPages']): rows += get(f'{API}/draw-date/{ds}/{ds}?page={p}&size=10')['content']
    return [[c['drawId'], c['drawTime'], c['winningNumbers']['list'], c['winningNumbers'].get('secondChance') or []] for c in rows if c.get('status') == 'results']

if __name__ == '__main__':
    d = load_all(); cmd = sys.argv[1] if len(sys.argv) > 1 else 'update'
    if cmd == 'merge':
        for fn in sys.argv[2:]:
            j = json.load(open(fn)); rows = j['draws'] if isinstance(j, dict) else j
            print(fn, '+', add(d, rows))
    else:
        last = max(d.values(), key=lambda x: x[0])[1] if d else int(time.time()*1000) - 3*86400000
        day = datetime.datetime.fromtimestamp(last/1000, datetime.timezone.utc).date()
        today = datetime.datetime.now(datetime.timezone.utc).date(); new = 0
        while day <= today: new += add(d, fetch_day(day.isoformat())); day += datetime.timedelta(days=1)
        print('νέες', new)
    print('σύνολο', save_all(d))
