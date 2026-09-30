"""Actualiza precios-auto.json con precios reales de supermercados online.
Lo ejecuta GitHub Actions cada semana (.github/workflows/precios.yml).
Uso local: python3 tools/precios.py [catalogo_mercadona.json]"""
import json, sys, time, unicodedata, urllib.request, urllib.parse, datetime, os
sys.path.insert(0, os.path.dirname(__file__))
from mapa_precios import M

UA = {'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Safari/604.1', 'Accept': 'application/json'}
def get(u):
    with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30) as x: return json.loads(x.read().decode('utf-8', 'replace'))
def norm(s): return ''.join(c for c in unicodedata.normalize('NFD', (s or '').lower()) if unicodedata.category(c) != 'Mn')
def ok_name(name, s):
    n = norm(name)
    if not all(t in n for t in norm(s['q']).split()): return False
    if s.get('o') and not any(t in n for t in norm(s['o']).split()): return False
    return not any(t and t in n for t in norm(s.get('x', '')).split())

# ---------- Mercadona: catálogo completo ----------
def mercadona_catalogo():
    out = []
    cats = [c['id'] for g in get('https://tienda.mercadona.es/api/categories/?lang=es')['results'] for c in g['categories']]
    for cid in cats:
        try:
            d = get(f'https://tienda.mercadona.es/api/categories/{cid}/?lang=es&wh=mad1')
            for sub in d.get('categories', []):
                for p in sub.get('products', []):
                    pi = p.get('price_instructions', {})
                    out.append([p['id'], p['display_name'], p.get('packaging'), pi.get('unit_price'), pi.get('unit_size'), pi.get('size_format'), pi.get('reference_price'), pi.get('reference_format'), d.get('name'), sub.get('name')])
        except Exception as e: print('mercadona cat', cid, e)
        time.sleep(0.25)
    return out

def merca_offer(x, s):
    _id, name, pack, up, usize, sfmt, rp, rfmt, cat, sub = x
    try: up = float(up); rp = float(rp) if rp else None
    except: return None
    if sfmt in ('kg', 'l'):
        if usize: g = float(usize) * 1000
        elif rp and rfmt in ('kg', 'L'): g = up / rp * 1000
        else: return None
    elif sfmt == 'ud':
        if not s.get('u') or not usize: return None
        g = float(usize) * s['u']
    else: return None
    if g <= 0 or up <= 0: return None
    return dict(p=round(up, 2), g=round(g), n=name)

# ---------- Dia ----------
def dia_offers(s):
    q = urllib.parse.quote(s.get('b') or s['q'])
    d = get(f'https://www.dia.es/api/v1/search-back/search/reduced?q={q}&page=1')
    out = []
    for it in d.get('search_items', [])[:40]:
        pr = it.get('prices') or {}; p, ppu, mu = pr.get('price'), pr.get('price_per_unit'), (pr.get('measure_unit') or '').upper()
        if not p or not ppu or not ok_name(it.get('display_name', ''), s): continue
        if mu in ('KILO', 'KILOGRAMO', 'LITRO', 'KG', 'L'): g = p / ppu * 1000
        elif s.get('u'): g = p / ppu * s['u']
        else: continue
        out.append(dict(p=round(p, 2), g=round(g), n=it['display_name']))
    return out

# ---------- Consum ----------
def consum_offers(s):
    q = urllib.parse.quote(s.get('b') or s['q'])
    d = get(f'https://tienda.consum.es/api/rest/V1.0/catalog/product?q={q}&limit=30')
    out = []
    for it in d.get('products', []):
        pd, pr = it.get('productData', {}), it.get('priceData', {})
        name = (pd.get('brand', {}) or {}).get('name', '')
        name = f"{pd.get('name', '')} {name}".strip()
        full = f"{pd.get('name', '')} {pd.get('description', '')}"
        prices = pr.get('prices') or []
        if not prices or not ok_name(full, s): continue
        v = prices[-1].get('value', {}); p, pu, ut = v.get('centAmount'), v.get('centUnitAmount'), norm(pr.get('unitPriceUnitType', ''))
        if not p or not pu: continue
        if 'kg' in ut or ut.endswith(' l') or ut == 'l' or '1 l' in ut: g = p / pu * 1000
        elif s.get('u'): g = p / pu * s['u']
        else: continue
        out.append(dict(p=round(p, 2), g=round(g), n=pd.get('description') or name))
    return out

def pick(offers, s, ref=None):
    """El más barato por kg; como envase de referencia, el más pequeño que cueste como mucho un 15% más por kg."""
    r = s.get('r', 1)
    offs = [dict(o, k=o['p'] / o['g'] * 1000 / r) for o in offers if o and o['g'] > 0]
    if ref: offs = [o for o in offs if ref * 0.35 <= o['k'] <= ref * 2.8]
    peq = [o for o in offs if o['g'] <= 3000]
    if peq: offs = peq
    if not offs: return None
    best = min(o['k'] for o in offs)
    o = min((o for o in offs if o['k'] <= best * 1.15), key=lambda o: o['g'])
    return dict(p=o['p'], g=round(o['g'] * r), k=round(best, 2), n=o['n'])

def main():
    cat = json.load(open(sys.argv[1])) if len(sys.argv) > 1 else mercadona_catalogo()
    res, log = {}, []
    for ing, s in M.items():
        if 'de' in s: continue
        row = {}
        cands = [merca_offer(x, s) for x in cat if (s.get('c') is None or x[9] in s['c'] or x[8] in s['c']) and ok_name(x[1], s)]
        m = pick(cands, s)
        if m: row['mercadona'] = m
        ref = m['k'] if m else None
        for tienda, fn in (('dia', dia_offers), ('consum', consum_offers)):
            if len(sys.argv) > 1: break
            try:
                x = pick(fn(s), s, ref)
                if x: row[tienda] = x
            except Exception as e: log.append(f'{tienda} {ing}: {e}')
            time.sleep(0.3)
        res[ing] = row
    for ing, s in M.items():
        if 'de' in s:
            base = res.get(s['de'], {}); r = s['r']
            res[ing] = {t: dict(p=v['p'], g=round(v['g'] * r), k=round(v['k'] / r, 2), n=v['n']) for t, v in base.items()}
    out = dict(fecha=datetime.date.today().isoformat(), tiendas=['mercadona', 'dia', 'consum'], precios=res)
    json.dump(out, open('precios-auto.json', 'w'), ensure_ascii=False, separators=(',', ':'))
    falta = [k for k, v in res.items() if not v]
    print('ingredientes', len(res), 'sin precio', falta)
    for t in ('mercadona', 'dia', 'consum'): print(t, sum(1 for v in res.values() if t in v))
    for l in log[:30]: print(l)

if __name__ == '__main__': main()
