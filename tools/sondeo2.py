import json, urllib.request, urllib.parse, ssl, os, http.cookiejar
H = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36', 'Accept': 'text/html,*/*;q=0.8', 'Accept-Language': 'es-ES,es;q=0.9'}
ctx = ssl._create_unverified_context()
cj = http.cookiejar.CookieJar(); op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj), urllib.request.HTTPSHandler(context=ctx))
res = {}
def go(k, u, data=None):
    try:
        r = op.open(urllib.request.Request(u, data=urllib.parse.urlencode(data).encode() if data else None, headers=H), timeout=30); t = r.read().decode('utf-8', 'replace'); res[k] = [r.status, r.geturl(), len(t), t[:700000]]
    except urllib.error.HTTPError as e: res[k] = [e.code, u, 0, e.read()[:500].decode('utf-8', 'replace')]
    except Exception as e: res[k] = ['ERR', u, 0, str(e)[:300]]
go('home', 'https://www.supermercadoseljamon.com/')
U = 'https://www.supermercadoseljamon.com/resultados?p_p_id=ProductosFoodPortlet_WAR_comerzziaportletsfood&p_p_lifecycle=1&p_p_state=normal&p_p_mode=view&_ProductosFoodPortlet_WAR_comerzziaportletsfood_accion=buscar&_ProductosFoodPortlet_WAR_comerzziaportletsfood_operacion=consultar'
go('post_leche', U, {'textoBuscador': 'leche semidesnatada', 'filtersBuscador': ''})
go('post_pollo', U, {'textoBuscador': 'pechuga pollo', 'filtersBuscador': ''})
go('get_leche', U + '&textoBuscador=leche')
go('detalle', 'https://www.supermercadoseljamon.com/detalle/-/Producto/arroz-largo-1kg/25010250')
os.makedirs('sondeo', exist_ok=True); json.dump(res, open('sondeo/tiendas.json', 'w'), ensure_ascii=False, indent=1)
for k, v in res.items(): print(k, v[0], v[2])
