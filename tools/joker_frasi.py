#!/usr/bin/env python3
"""Φράσεις Τζόκερ — η φράση-σπόρος κάθε κλήρωσης και η πρόβλεψη της επόμενης.

Κανόνες (ίδιοι για όλες τις κληρώσεις, από την #1):
  * Κάθε κλήρωση έχει 8 «κουτάκια» με γεγονότα γνωστά πριν τις 20:00 της ημέρας:
    ημερομηνία, γιορτή, σελήνη, ήλιος στην Πάτρα, καιρός/εποχή, θέση στη χρονιά,
    προηγούμενη κλήρωση, αριθμός κλήρωσης. Κάθε κουτάκι έχει μερικές διατυπώσεις.
  * Κείμενο = κουτάκια (η ημερομηνία πάντα πρώτη) ενωμένα με ". " και τελεία στο τέλος.
  * Σπόρος = πρώτα 8 bytes του SHA-256 (big endian) mod 24.435.180
    -> rank πεντάδας * 20 + (Τζόκερ - 1).
  * «Διατύπωση» = σειρά κουτακιών + επιλογή σε κάθε κουτάκι.
  * Βρεθείσα φράση (μετά την κλήρωση): η πρώτη διατύπωση (με τη σειρά απαρίθμησης)
    που δίνει ακριβώς την κλήρωση.
  * Πρόβλεψη (πριν την κλήρωση): η πρώτη διατύπωση που ΔΕΝ έχει χρησιμοποιηθεί
    ποτέ (ούτε από κλήρωση ούτε από παλιότερη πρόβλεψη) και που ΔΕΝ δίνει πεντάδα
    που έχει ήδη βγει ή έχει ήδη προβλεφθεί.

Χρήση:  python3 tools/joker_frasi.py update
"""
import json, sys, os, math, hashlib, itertools, subprocess, tempfile, urllib.request
import datetime as dt
from math import comb
from zoneinfo import ZoneInfo
from astral import LocationInfo
from astral.sun import sun

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JOKER = os.path.join(ROOT, 'data', 'joker.json')
FRASI = os.path.join(ROOT, 'data', 'joker_frasi.json')
ND = json.load(open(os.path.join(ROOT, 'tools', 'joker_namedays.json'), encoding='utf-8'))
SEEK = os.path.join(ROOT, 'tools', 'joker_seek')
API = 'https://api.opap.gr/draws/v3.0/5104'
M = 24435180
TZ = ZoneInfo('Europe/Athens')
PAT = LocationInfo('Πάτρα', 'GR', 'Europe/Athens', 38.246, 21.735)
DAYS = ['Δευτέρα','Τρίτη','Τετάρτη','Πέμπτη','Παρασκευή','Σάββατο','Κυριακή']
MON = ['Ιανουαρίου','Φεβρουαρίου','Μαρτίου','Απριλίου','Μαΐου','Ιουνίου','Ιουλίου',
       'Αυγούστου','Σεπτεμβρίου','Οκτωβρίου','Νοεμβρίου','Δεκεμβρίου']
SYN = 29.530588853
REF = dt.datetime(2000,1,6,18,14,tzinfo=dt.timezone.utc).timestamp()


def easter(y):
    a,b,c = y%4, y%7, y%19; d = (19*c+15)%30; e = (2*a+4*b-d+34)%7
    m = (d+e+114)//31; day = (d+e+114)%31+1
    return dt.date(y,m,day) + dt.timedelta(days=13)

def season(d):
    m = d.month
    return 'χειμώνας' if m in (12,1,2) else 'άνοιξη' if m in (3,4,5) else 'καλοκαίρι' if m in (6,7,8) else 'φθινόπωρο'

def slots(draw_id, ts, prev):
    """prev = (sorted mains, joker) της προηγούμενης κλήρωσης ή None."""
    t = dt.datetime.fromtimestamp(ts, TZ); d = t.date(); wd = DAYS[d.weekday()]; mo = MON[d.month-1]
    S = []
    S.append(['%s %d %s %d'%(wd,d.day,mo,d.year), '%s, %d %s %d'%(wd,d.day,mo,d.year),
              '%d %s %d, ημέρα %s'%(d.day,mo,d.year,wd), '%d/%d/%d'%(d.day,d.month,d.year),
              'Σήμερα, %s %d %s %d'%(wd,d.day,mo,d.year), 'Ημέρα %s, %d του %s %d'%(wd,d.day,mo,d.year)])
    names = ND['fixed'].get('%d/%d'%(d.day,d.month), [])
    E = easter(d.year); rel = [x[1] for x in ND['easter'] if E+dt.timedelta(days=x[0]) == d]
    nd = []
    if names:
        nd += ['Σήμερα γιορτάζουν: '+', '.join(names[:3]),
               'Γιορτάζουν '+names[0]+(' και '+names[1] if len(names)>1 else ''),
               'Χρόνια πολλά σε όσους λέγονται '+names[0]]
        nd += ['Γιορτάζει '+n for n in names[:8]]
    if rel: nd += ['Η Εκκλησία γιορτάζει: '+x for x in rel] + ['Σήμερα είναι '+x for x in rel]
    if not nd: nd = ['Σήμερα δεν έχει μεγάλη γιορτή', 'Ημέρα χωρίς μεγάλη ονομαστική εορτή']
    S.append(nd)
    age = ((ts-REF)/86400) % SYN; ill = round((1-math.cos(2*math.pi*age/SYN))/2*100)
    ph = 'Νέα σελήνη' if age<1.5 or age>SYN-1.5 else 'Πανσέληνος' if abs(age-SYN/2)<1.5 else ('Αύξουσα σελήνη' if age<SYN/2 else 'Φθίνουσα σελήνη')
    S.append(['Η σελήνη είναι φωτισμένη κατά %d%%'%ill, '%s, φωτισμένη %d%%'%(ph,ill), 'Η σελήνη είναι %d ημερών'%round(age), ph])
    s = sun(PAT.observer, date=d, tzinfo=TZ); L = s['sunset']-s['sunrise']; h,m = divmod(int(L.total_seconds()//60),60)
    sr, ss = s['sunrise'].strftime('%H:%M'), s['sunset'].strftime('%H:%M')
    S.append(['Στην Πάτρα ο ήλιος ανέτειλε στις %s'%sr, 'Στην Πάτρα ο ήλιος δύει στις %s'%ss,
              'Η μέρα στην Πάτρα κρατάει %d ώρες και %d λεπτά'%(h,m), 'Ανατολή %s, δύση %s στην Πάτρα'%(sr,ss)])
    # Καιρός: οι ωριαίες μετρήσεις του σταθμού (Meteostat 16687) σταμάτησαν τον 11/2025 -> εποχή/χρονιά
    S.append(['Μέρα '+{'χειμώνας':'του χειμώνα','άνοιξη':'της άνοιξης','καλοκαίρι':'του καλοκαιριού','φθινόπωρο':'του φθινοπώρου'}[season(d)],
              'Χρονιά %d'%d.year, 'Έτος %d'%d.year])
    doy = d.timetuple().tm_yday
    xm = (dt.date(d.year if d <= dt.date(d.year,12,25) else d.year+1,12,25)-d).days
    S.append(['Η %dη μέρα του %d'%(doy,d.year), 'Μένουν %d μέρες ως τα Χριστούγεννα'%xm,
              'Εβδομάδα %d του χρόνου'%d.isocalendar()[1], 'Εποχή: %s'%season(d),
              'Μένουν %d μέρες ως το τέλος της χρονιάς'%((dt.date(d.year,12,31)-d).days)])
    if prev:
        pm = ' '.join(map(str, sorted(prev[0])))
        S.append(['Η προηγούμενη κλήρωση έφερε %s και Τζόκερ %d'%(pm,prev[1]),
                  'Στην προηγούμενη κλήρωση βγήκαν τα %s'%pm, 'Προηγούμενο Τζόκερ: το %d'%prev[1]])
    else:
        S.append(['Η πρώτη κλήρωση του Τζόκερ', 'Ξεκινά το Τζόκερ'])
    S.append(['Κλήρωση Τζόκερ αριθμός %d'%draw_id, 'Η %dη κλήρωση του Τζόκερ'%draw_id, 'Τζόκερ #%d'%draw_id])
    return S

def rank(mains, j):
    return sum(comb(x-1, i+1) for i,x in enumerate(sorted(mains)))*20 + (j-1)

def unrank(v):
    r, j = divmod(v, 20); out = []
    for i in range(5, 0, -1):
        x = i
        while comb(x, i) <= r: x += 1
        x -= 1; out.append(x+1); r -= comb(x, i)
    return sorted(out), j+1

def text_of(S, perm, ch):
    return '. '.join(S[s][ch[s]] for s in perm) + '.'

def seed_of(txt):
    return int.from_bytes(hashlib.sha256(txt.encode()).digest()[:8], 'big') % M

def seek(draw_id, S, target):
    """Βρεθείσα φράση με το γρήγορο πρόγραμμα C (ίδια σειρά απαρίθμησης)."""
    with tempfile.NamedTemporaryFile('w', encoding='utf-8', delete=False, suffix='.txt') as f:
        f.write('%d %d %d\n' % (draw_id, target, len(S)))
        for sl in S:
            f.write('%d\n' % len(sl))
            for o in sl: f.write(o+'\n')
        fn = f.name
    out = subprocess.run([SEEK, '0', '1', fn], capture_output=True, text=True, check=True).stdout.split()
    os.unlink(fn)
    if out[1] == 'MISS': return None
    i = out.index('|'); perm = [int(x) for x in out[1:i]]; ch = [int(x) for x in out[i+1:]]
    txt = text_of(S, perm, ch)
    assert seed_of(txt) == target
    return perm, ch, txt

def key(perm, ch): return ' '.join(map(str, perm)) + '|' + ' '.join(map(str, ch))

def predict(draw_id, ts, prev, used_pat, used_res):
    S = slots(draw_id, ts, prev); n = len(S)
    for rest in itertools.permutations(range(1, n)):
        perm = [0] + list(rest)
        for ch in itertools.product(*[range(len(x)) for x in S]):
            ch = list(ch)
            if key(perm, ch) in used_pat: continue
            txt = text_of(S, perm, ch); v = seed_of(txt)
            if v // 20 in used_res: continue          # ίδια πεντάδα με κλήρωση/πρόβλεψη -> επόμενη
            mains, j = unrank(v)
            return {'id': draw_id, 'ts': ts, 'perm': perm, 'ch': ch, 'text': txt, 'seed': v,
                    'n': mains, 'j': j, 'made': dt.datetime.now(TZ).strftime('%d/%m/%Y %H:%M')}

def get(url):
    req = urllib.request.Request(url)
    return json.load(urllib.request.urlopen(req, timeout=30))

def rec(d):
    return [d['drawId'], d['drawTime']//1000, d['winningNumbers']['list'], d['winningNumbers']['bonus'][0],
            d['pricePoints']['amount'], [float(c['divident']) for c in d['prizeCategories']]]

def update():
    J = json.load(open(JOKER))
    F = json.load(open(FRASI, encoding='utf-8')) if os.path.exists(FRASI) else {'found': [], 'pred': []}
    la = get(API + '/last-result-and-active')
    last = la['last']; active = la['active']
    # 1. νέες κληρώσεις στο αρχείο
    changed = False
    have = {r[0] for r in J}
    for i in range(J[-1][0]+1, last['drawId']+1):
        d = last if i == last['drawId'] else get('%s/%d' % (API, i))
        if d.get('status') != 'results' or i in have: continue
        J.append(rec(d)); changed = True
    if changed:
        json.dump(J, open(JOKER, 'w'), separators=(',', ':'))
    # 2. βρεθείσες φράσεις για ό,τι λείπει
    done = {x[0] for x in F['found']}
    for k, r in enumerate(J):
        if r[0] in done: continue
        prev = (J[k-1][2], J[k-1][3]) if k else None
        S = slots(r[0], r[1], prev)
        res = seek(r[0], S, rank(r[2], r[3]))
        F['found'].append([r[0], *(key(res[0], res[1]).split('|')), res[2]] if res else [r[0], None, None, None])
        print('βρέθηκε', r[0], res[2] if res else 'MISS')
    F['found'].sort(key=lambda x: x[0])
    # 3. πρόβλεψη για την επόμενη κλήρωση (μόνο αν δεν υπάρχει ήδη)
    nid = active['drawId']
    if J[-1][0] == nid - 1 and not any(p['id'] == nid for p in F['pred']):
        used_pat = {x[1]+'|'+x[2] for x in F['found'] if x[1] is not None} | {key(p['perm'], p['ch']) for p in F['pred']}
        used_res = {rank(r[2], r[3])//20 for r in J} | {p['seed']//20 for p in F['pred']}
        p = predict(nid, active['drawTime']//1000, (J[-1][2], J[-1][3]), used_pat, used_res)
        F['pred'].append(p); print('πρόβλεψη', nid, p['n'], p['j'], p['text'])
    json.dump(F, open(FRASI, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))

if __name__ == '__main__':
    if sys.argv[1:] == ['update']: update()
    else: print(__doc__)
