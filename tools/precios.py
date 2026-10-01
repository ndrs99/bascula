"""Actualiza precios-auto.json con precios reales de supermercados online.
Lo ejecuta GitHub Actions cada semana (.github/workflows/precios.yml).
Uso local: python3 tools/precios.py [catalogo_mercadona.json]"""
import json, sys, time, unicodedata, urllib.request, urllib.parse, datetime, os, re, html
sys.path.insert(0, os.path.dirname(__file__))
from mapa_precios import M

UA = {'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Safari/604.1', 'Accept': 'application/json'}
DESK = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36', 'Accept': 'text/html,application/json;q=0.9,*/*;q=0.8', 'Accept-Language': 'es-ES,es;q=0.9'}
def get(u, h=None):
    with urllib.request.urlopen(urllib.request.Request(u, headers=h or UA), timeout=30) as x: return json.loads(x.read().decode('utf-8', 'replace'))
def norm(s): return ''.join(c for c in unicodedata.normalize('NFD', (s or '').lower()) if unicodedata.category(c) != 'Mn')
def stem(w): return w[:-2] if w.endswith('es') and len(w) > 5 else w[:-1] if w.endswith('s') and len(w) > 3 else w
def strip_brand(name):
    """Quita la marca en mayúsculas del principio: 'AUCHAN Pechuga de pollo' -> 'Pechuga de pollo'."""
    w = (name or '').replace('-', ' ').split()
    while len(w) > 1 and (w[0].isupper() or not any(c.isalpha() for c in w[0]) or '.' in w[0] or w[0].endswith('®')): w.pop(0)
    return ' '.join(w)
def ok_head(name, s):
    """Sin secciones, el nombre tiene que empezar por el producto (evita 'Refresco de limón' para limones)."""
    words = [w for w in norm(strip_brand(name)).replace(',', ' ').split() if w.isalpha()]
    if not words: return False
    heads = {stem(t) for f in ('q', 'o', 'b', 'h') for t in norm(s.get(f, '')).split()}
    return stem(words[0]) in heads
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
        if not p or not ppu or not ok_name(it.get('display_name', ''), s) or not ok_head(it.get('display_name', ''), s): continue
        if mu in ('KILO', 'KILOGRAMO', 'LITRO', 'KG', 'L'): g = p / ppu * 1000
        elif s.get('u'): g = p / ppu * s['u']
        else: continue
        out.append(dict(p=round(p, 2), g=round(g), n=it['display_name']))
    return out

# ---------- tamaño del envase a partir del texto ("6 x 1 l", "500 g", "Aprox. 360-460g", "2x88 g") ----------
def size_g(txt, u=None):
    t = norm(txt).replace(',', '.')
    m = re.search(r'(\d+)\s*x\s*(\d+(?:\.\d+)?)\s*(kg|g|gr|l|ml|cl)\b', t)
    if m: n, q, un = int(m.group(1)), float(m.group(2)), m.group(3)
    else:
        m = re.search(r'(\d+(?:\.\d+)?)\s*(?:-\s*(\d+(?:\.\d+)?))?\s*(kg|g|gr|l|ml|cl)\b', t)
        if not m:
            m2 = re.search(r'(\d+)\s*(?:uds?|unidades|piezas)\b', t)
            return int(m2.group(1)) * u if (m2 and u) else None
        n, q, un = 1, (float(m.group(1)) + float(m.group(2))) / 2 if m.group(2) else float(m.group(1)), m.group(3)
    k = {'kg': 1000, 'l': 1000, 'g': 1, 'gr': 1, 'ml': 1, 'cl': 10}[un]
    g = n * q * k
    return g if 5 <= g <= 20000 else None

# ---------- Alcampo (web de compra online: se leen las fichas de la búsqueda) ----------
def alcampo_offers(s):
    q = urllib.parse.quote(s.get('b') or s['q'])
    req = urllib.request.Request(f'https://www.compraonline.alcampo.es/search?q={q}', headers=DESK)
    with urllib.request.urlopen(req, timeout=40) as x: t = x.read().decode('utf-8', 'replace')
    out = []
    for c in t.split('data-test="fop-wrapper:')[1:41]:
        n = re.search(r'data-test="fop-product-link"[^>]*>(?:<[^>]+>)*?<span class="salt-vc">([^<]+)</span>', c)
        p = re.search(r'data-test="fop-price">([^<]+)<', c)
        if not n or not p: continue
        name = html.unescape(n.group(1)).strip().rstrip('.'); name = re.sub(r'\s*Producto Alcampo\.?$', '', name)
        try: price = float(p.group(1).replace('\xa0', ' ').replace('€', '').replace('.', '').replace(',', '.').strip())
        except: continue
        if not ok_name(name, s) or not ok_head(name, s): continue
        g = None; u = re.search(r'data-test="fop-price-per-unit">\(([\d.,]+)\s*(?:&nbsp;|\xa0)?€ por (kilogramo|litro|unidad)', c)
        if u:
            per = float(u.group(1).replace('.', '').replace(',', '.'))
            if per > 0 and u.group(2) in ('kilogramo', 'litro'): g = price / per * 1000
            elif per > 0 and s.get('u'): g = price / per * s['u']
        if not g: g = size_g(name, s.get('u'))
        if g: out.append(dict(p=round(price, 2), g=round(g), n=name))
    return out

# ---------- Lidl (solo los productos que tiene en su web, sobre todo ofertas de la semana) ----------
def lidl_offers(s):
    q = urllib.parse.quote(s.get('b') or s['q'])
    d = get(f'https://www.lidl.es/q/api/search?q={q}&locale=es_ES&assortment=ES&version=v2.0.0&fetchsize=48', DESK)
    out = []
    for it in d.get('items', []):
        g0 = (it.get('gridbox') or {}).get('data') or {}
        if g0.get('category') != 'Food': continue
        name, pr = g0.get('fullTitle') or g0.get('title') or '', g0.get('price') or {}
        price = pr.get('price')
        if not price or not ok_name(name, s) or not ok_head(name, s): continue
        g = size_g(((pr.get('packaging') or {}).get('text') or '') + ' ' + name, s.get('u'))
        bp = re.search(r'([\d.,]+)\s*€/(kg|l)\b', norm((pr.get('basePrice') or {}).get('text', '')))
        if bp:
            per = float(bp.group(1).replace('.', '').replace(',', '.'))
            if per > 0: g = price / per * 1000
        if g: out.append(dict(p=round(price, 2), g=round(g), n=strip_brand(name)))
    return out

# ---------- Consum (ya no se consulta: no hay en Sevilla) ----------
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
        if not prices or not ok_name(full, s) or not ok_head(pd.get('name', ''), s): continue
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
        for tienda, fn in (('dia', dia_offers), ('alcampo', alcampo_offers), ('lidl', lidl_offers)):
            if len(sys.argv) > 1: break
            try:
                offs = fn(s); x = pick(offs, s, ref)
                if x: row[tienda] = x
                elif tienda in ('alcampo', 'lidl'): log.append(f'{tienda} {ing}: {len(offs)} candidatos, ninguno válido')
            except Exception as e: log.append(f'{tienda} {ing}: ERROR {str(e)[:120]}')
            time.sleep(0.3)
        res[ing] = row
    for ing, s in M.items():
        if 'de' in s:
            base = res.get(s['de'], {}); r = s['r']
            res[ing] = {t: dict(p=v['p'], g=round(v['g'] * r), k=round(v['k'] / r, 2), n=v['n']) for t, v in base.items()}
    out = dict(fecha=datetime.date.today().isoformat(), tiendas=['mercadona', 'dia', 'alcampo', 'lidl'], precios=res)
    json.dump(log, open('tools/ultimo-registro.json', 'w'), ensure_ascii=False, indent=0)
    json.dump(out, open('precios-auto.json', 'w'), ensure_ascii=False, separators=(',', ':'))
    falta = [k for k, v in res.items() if not v]
    print('ingredientes', len(res), 'sin precio', falta)
    for t in ('mercadona', 'dia', 'alcampo', 'lidl'): print(t, sum(1 for v in res.values() if t in v))
    for l in log[:30]: print(l)

if __name__ == '__main__': main()
