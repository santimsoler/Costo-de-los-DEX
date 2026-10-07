# bajar_cultivos_arg.py -- superficie sembrada por provincia y campaña: soja, maíz, trigo, girasol, sorgo (MAGyP). Colab.
# Salida: /content/cultivos_provincia_arg.csv  (provincia, year, cultivo, area_ha, prod_t)
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

CULT = {"soja total": "soja", "soja": "soja", "maíz": "maiz", "trigo total": "trigo", "girasol": "girasol", "sorgo": "sorgo"}
q = get("https://datos.magyp.gob.ar/api/3/action/package_search", params={"q": "estimaciones agricolas", "rows": 20}).json()
urls = [r["url"] for p in q["result"]["results"] for r in p["resources"]
        if r.get("format", "").upper() == "CSV" and r["url"].lower().split("/")[-1].startswith("estimaciones-agricolas")]
print("archivo:", urls)
raw = get(urls[0]).content
for enc in ("utf-8", "latin-1"):
    try: d = pd.read_csv(io.BytesIO(raw), encoding=enc, sep=None, engine="python"); break
    except Exception: pass
d.columns = [re.sub(r"\W+", "_", c.strip().lower()) for c in d.columns]
d["cult"] = d.cultivo.astype(str).str.lower().str.strip().map(CULT)
d = d[d.cult.notna()].copy()
y = d.campania.astype(str).str.extract(r"(\d{4})/(\d{2,4})")
d["year"] = y[1].astype(float).where(y[1].astype(float) > 100, 2000 + y[1].astype(float))   # año de cosecha
g = d.groupby(["provincia", "year", "cult"]).agg(area_ha=("superficie_sembrada_ha", "sum"), prod_t=("produccion_tm", "sum")).reset_index()
g = g.rename(columns={"cult": "cultivo"})
nac = g[g.year.isin([2000, 2010, 2015, 2020, 2024])].groupby(["year", "cultivo"]).area_ha.sum().unstack() / 1e6
print("Control nacional (Mha):\n", nac.round(1))
g.to_csv(f"{OUT}/cultivos_provincia_arg.csv", index=False); print(g.shape, g.year.min(), g.year.max())
