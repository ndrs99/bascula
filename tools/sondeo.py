# Sondeo: descarga el catálogo de Mercadona y prueba otras tiendas online
import json, urllib.request, time, os
UA = {'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Safari/604.1', 'Accept': 'application/json'}
def get(u, h=None):
    r = urllib.request.Request(u, headers={**UA, **(h or {})})
    with urllib.request.urlopen(r, timeout=30) as x: return x.status, x.read().decode('utf-8', 'replace')
os.makedirs('sondeo', exist_ok=True)
out = []
try:
    st, t = get('https://tienda.mercadona.es/api/categories/?lang=es')
    cats = [c['id'] for g in json.loads(t)['results'] for c in g['categories']]
    for cid in cats:
        try:
            st, t = get(f'https://tienda.mercadona.es/api/categories/{cid}/?lang=es&wh=mad1')
            d = json.loads(t)
            for sub in d.get('categories', []):
                for p in sub.get('products', []):
                    pi = p.get('price_instructions', {})
                    out.append([p['id'], p['display_name'], p.get('packaging'), pi.get('unit_price'), pi.get('unit_size'), pi.get('size_format'), pi.get('reference_price'), pi.get('reference_format'), d.get('name'), sub.get('name')])
        except Exception as e: out.append(['ERR', cid, str(e)])
        time.sleep(0.3)
except Exception as e: out.append(['ERR', 'cats', str(e)])
json.dump(out, open('sondeo/mercadona.json', 'w'), ensure_ascii=False)
probes = {
 'dia': 'https://www.dia.es/api/v1/search-back/search/reduced?q=leche%20semidesnatada&page=1',
 'alcampo': 'https://www.compraonline.alcampo.es/api/v5/products/search?term=leche%20semidesnatada',
 'carrefour': 'https://www.carrefour.es/cloud-api/plp-food-papi/v1/search?query=leche%20semidesnatada',
 'eroski': 'https://supermercado.eroski.es/es/search/results/?q=leche%20semidesnatada',
 'consum': 'https://tienda.consum.es/api/rest/V1.0/catalog/product?q=leche%20semidesnatada&limit=5',
 'hipercor': 'https://www.hipercor.es/alimentacion/api/catalog/supermarket/search/?term=leche',
 'lidl': 'https://www.lidl.es/q/api/search?q=leche&fetchsize=5&locale=es_ES&assortment=ES&version=2.1.0',
}
res = {}
for k, u in probes.items():
    try: st, t = get(u); res[k] = [st, t[:3000]]
    except Exception as e: res[k] = ['ERR', str(e)[:300]]
json.dump(res, open('sondeo/otros.json', 'w'), ensure_ascii=False, indent=1)
print(len(out), {k: v[0] for k, v in res.items()})
