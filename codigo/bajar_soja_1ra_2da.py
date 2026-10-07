# bajar_soja_1ra_2da.py -- soja de 1ra y 2da (y total), trigo y maíz (total, temprano/tardío si existen) por provincia y campaña (MAGyP). Colab.
# Salida: /content/soja_1ra_2da_arg.csv  (provincia, year, cultivo, area_ha, prod_t); year = año de cosecha (campaña 2015/16 -> 2016)
import requests, pandas as pd, numpy as np, re, io, os, time
OUT = "/content" if os.path.isdir("/content") else "."
H = {"User-Agent": "Mozilla/5.0"}
def get(url, tries=4, **kw):
    for i in range(tries):
        try:
            r = requests.get(url, headers=H, timeout=180, **kw); r.raise_for_status(); return r
        except Exception as e:
            print(f"   reintento {i+1}: {str(e)[:80]}"); time.sleep(3*(i+1))
    raise RuntimeError("falló " + url)

q = get("https://datos.magyp.gob.ar/api/3/action/package_search", params={"q": "estimaciones agricolas", "rows": 20}).json()
urls = [r["url"] for p in q["result"]["results"] for r in p["resources"]
        if r.get("format", "").upper() == "CSV" and r["url"].lower().split("/")[-1].startswith("estimaciones-agricolas")]
print("archivo:", urls)
raw = get(urls[0]).content
for enc in ("utf-8", "latin-1"):
    try: d = pd.read_csv(io.BytesIO(raw), encoding=enc, sep=None, engine="python"); break
    except Exception: pass
d.columns = [re.sub(r"\W+", "_", c.strip().lower()) for c in d.columns]
d["c0"] = d.cultivo.astype(str).str.lower().str.strip()
print("\nCultivos disponibles en el archivo:\n", sorted(d.c0.unique()))   # diagnóstico: nombres exactos

def norm(c):
    if c.startswith("soja"):
        if re.search(r"1\s*[ra°ºª]|primera", c):  return "soja_1ra"
        if re.search(r"2\s*[da°ºª]|segunda", c):  return "soja_2da"
        return "soja_total"
    if c.startswith("ma") and "z" in c:
        if re.search(r"temprano|1\s*[ra°ºª]|primera", c): return "maiz_temprano"
        if re.search(r"tard|2\s*[da°ºª]|segunda", c):     return "maiz_tardio"
        return "maiz_total"
    if c.startswith("trigo"):
        return "trigo_total" if "total" in c else "trigo"
    return None
d["cult"] = d.c0.map(norm); d = d[d.cult.notna()].copy()
y = d.campania.astype(str).str.extract(r"(\d{4})/(\d{2,4})")
d["year"] = y[1].astype(float).where(y[1].astype(float) > 100, 2000 + y[1].astype(float))
g = d.groupby(["provincia", "year", "cult"]).agg(area_ha=("superficie_sembrada_ha", "sum"), prod_t=("produccion_tm", "sum")).reset_index()
g = g.rename(columns={"cult": "cultivo"})
nac = g[g.year.isin([2000, 2010, 2015, 2016, 2019, 2022, 2024])].groupby(["year", "cultivo"]).area_ha.sum().unstack() / 1e6
print("\nControl nacional (Mha) -- soja_1ra + soja_2da debería ≈ soja_total (~18.4 en 2010):\n", nac.round(1).to_string())
g.to_csv(f"{OUT}/soja_1ra_2da_arg.csv", index=False); print(g.shape, g.year.min(), g.year.max())
