import json, urllib.request, os
H = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36', 'Accept': 'text/html,application/json;q=0.9,*/*;q=0.8', 'Accept-Language': 'es-ES,es;q=0.9'}
U0 = {
 'familycash_secc': 'https://www.familycash.es/secciones/alimentacion/',
 'familycash_q1': 'https://www.familycash.es/catalogsearch/result/?q=leche',
 'familycash_q2': 'https://www.familycash.es/?s=leche',
 'dani_json': 'https://supermercadosdani.com/products.json?limit=3',
 'dani_suggest': 'https://supermercadosdani.com/search/suggest.json?q=leche&resources[type]=product',
 'dani_es': 'https://www.supermercadosdani.es/',
 'eljamon_home': 'https://www.supermercadoseljamon.com/',
 'eljamon_q': 'https://www.supermercadoseljamon.com/buscador?texto=leche',
 'mas_alim': 'https://www.supermercadosmas.com/alimentacion/',
 'mas_q': 'https://www.supermercadosmas.com/catalogsearch/result/?q=leche',
 'alcampo_api': 'https://www.compraonline.alcampo.es/api/webproductpagews/v5/products/search?term=leche',
 'alcampo_web': 'https://www.compraonline.alcampo.es/search?q=leche',
 'carrefour_web': 'https://www.carrefour.es/supermercado/?q=leche',
 'eroski_web': 'https://supermercado.eroski.es/es/search/results/?q=leche',
 'lidl_api': 'https://www.lidl.es/q/api/search?q=leche&locale=es_ES&assortment=ES&version=v2.0.0',
 'lidl_web': 'https://www.lidl.es/q/search?q=leche',
 'aldi_web': 'https://www.aldi.es/productos.html',
 'aldi_q': 'https://www.aldi.es/buscar.html?query=leche',
 'hipercor_q': 'https://www.hipercor.es/supermercado/buscar/?term=leche',
 'eci_q': 'https://www.elcorteingles.es/supermercado/buscar/?term=leche',
 'costco_q': 'https://www.costco.es/search?text=leche',
 'coviran': 'https://www.coviran.es/',
}
U = {k: U0[k] for k in ['familycash_q2', 'familycash_secc', 'dani_es', 'alcampo_web', 'lidl_api', 'aldi_web', 'costco_q', 'coviran']}
U['lidl_api2'] = 'https://www.lidl.es/q/api/search?q=pechuga%20pollo&locale=es_ES&assortment=ES&version=v2.0.0'
U['alcampo_web2'] = 'https://www.compraonline.alcampo.es/search?q=pechuga%20de%20pollo'
U['aldi_leche'] = 'https://www.aldi.es/productos/frescos/leche-y-huevos.html'
U['familycash_q3'] = 'https://www.familycash.es/?s=pechuga+pollo&post_type=product'
res = {}
for k, u in U.items():
    try:
        r = urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=25)
        t = r.read().decode('utf-8', 'replace'); res[k] = [r.status, r.geturl(), dict(r.headers).get('Server', ''), len(t), t[:600000]]
    except urllib.error.HTTPError as e:
        res[k] = [e.code, u, e.headers.get('Server', ''), 0, e.read()[:300].decode('utf-8', 'replace')]
    except Exception as e: res[k] = ['ERR', u, '', 0, str(e)[:300]]
os.makedirs('sondeo', exist_ok=True); json.dump(res, open('sondeo/tiendas.json', 'w'), ensure_ascii=False, indent=1)
for k, v in res.items(): print(k, v[0], v[2], v[3])
