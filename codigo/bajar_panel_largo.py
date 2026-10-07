# bajar_panel_largo.py -- panel global ampliado de soja (todos los países productores relevantes), 1961-2025
# Uso en Colab: pegar en una celda y ejecutar. Cachea cada descarga en /content (si falla, se vuelve a correr y retoma).
# Salida: /content/base_soja_panel_largo.csv
import os, io, re, time, zipfile, subprocess, sys
import numpy as np, pandas as pd, requests
try: import pycountry
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "pycountry"]); import pycountry

OUT = "/content" if os.path.isdir("/content") else "."
H = {"User-Agent": "Mozilla/5.0"}
ANIO0, ANIO1 = 1961, 2025
P = lambda n: os.path.join(OUT, n)

def get(url, timeout=120, intentos=3, espera=3):
    for i in range(intentos):
        try:
            r = requests.get(url, headers=H, timeout=timeout); r.raise_for_status(); return r
        except Exception as e:
            print(f"  intento {i+1}/{intentos} falló: {type(e).__name__}"); time.sleep(espera)
    return None

# ====================================================================== 1) FAOSTAT (todos los países)
FAO = "https://bulks-faostat.fao.org/production/"
def m49_a_iso3(x):
    try: return pycountry.countries.get(numeric=str(x).replace("'", "").strip().zfill(3)).alpha_3
    except Exception: return None

def fao_cultivos():
    cache = P("fao_cultivos_largo.csv")
    if os.path.exists(cache): print("FAOSTAT caché"); return pd.read_csv(cache)
    print("FAOSTAT cultivos (descarga grande, puede tardar varios minutos)...")
    r = get(FAO + "Production_Crops_Livestock_E_All_Data_(Normalized).zip", 1200)
    if r is None: return None
    z = zipfile.ZipFile(io.BytesIO(r.content)); nom = [n for n in z.namelist() if n.endswith(".csv") and "Normalized" in n][0]
    df = pd.read_csv(z.open(nom), encoding="latin-1", low_memory=False)
    df = df[df["Item Code"].isin([236, 56, 15]) & df["Element Code"].isin([5510, 5312])].copy()   # soja, maíz, trigo; producción y superficie cosechada
    col = [c for c in df.columns if "M49" in c][0]
    df["iso3"] = df[col].map(m49_a_iso3); df = df[df.iso3.notna()]
    df["v"] = df["Element Code"].map({5510: "prod", 5312: "area"}) + "_" + df["Item Code"].map({236: "soja", 56: "maiz", 15: "trigo"})
    out = df.pivot_table(index=["iso3", "Year"], columns="v", values="Value", aggfunc="first").reset_index().rename(columns={"Year": "year"})
    out.to_csv(cache, index=False); return out

def elegir_paises(c):
    """Productores de soja relevantes: >=100 mil ha en algún año, o >=30 mil ha en 15 años o más (1991-2024)."""
    s = c[c.year.between(1991, 2024)]
    mx = s.groupby("iso3").area_soja.max(); n30 = s[s.area_soja >= 30000].groupby("iso3").size()
    sel = sorted(set(mx[mx >= 100000].index) | set(n30[n30 >= 15].index))
    print(f"{len(sel)} países seleccionados:", sel); return sel

# ====================================================================== 2) Banco Mundial
WB_IND = {"PA.NUS.FCRF": "ner", "FP.CPI.TOTL": "cpi", "NY.GDP.PCAP.KD": "pib_pc", "NY.GDP.MKTP.KD.ZG": "pib_crec",
          "AG.LND.ARBL.HA": "tierra_arable_ha", "AG.CON.FERT.ZS": "fert_kg_ha", "AG.PRD.CROP.XD": "idx_prod_cultivos",
          "NV.AGR.TOTL.ZS": "agro_pib_pct", "VC.BTL.DETH": "muertes_batalla"}
def wb_indicador(cod, nombre, paises):
    cache = P(f"wbL_{cod}.csv")
    if os.path.exists(cache): return pd.read_csv(cache)
    filas = []
    for i in range(0, len(paises), 25):                                   # lotes de 25 países
        pag = 1
        while True:
            url = (f"https://api.worldbank.org/v2/country/{';'.join(paises[i:i+25])}/indicator/{cod}"
                   f"?format=json&per_page=2000&date={ANIO0}:{ANIO1}&page={pag}")
            r = get(url, 60)
            if r is None: return None
            j = r.json()
            if not isinstance(j, list) or len(j) < 2 or j[1] is None: break
            filas += [{"iso3": x["countryiso3code"], "year": int(x["date"]), nombre: x["value"]} for x in j[1]]
            if pag >= j[0]["pages"]: break
            pag += 1
    d = pd.DataFrame(filas)
    if len(d): d.to_csv(cache, index=False)
    return d if len(d) else None

# ====================================================================== 3) Precios internacionales (FRED -> DBnomics/FMI)
def anual(fechas, valores, nombre):
    s = pd.DataFrame({"year": pd.to_datetime(fechas).year, "v": pd.to_numeric(valores, errors="coerce")})
    return s.groupby("year").v.mean().rename(nombre).reset_index()

def precio_intl(nombre, fred_id, imf):
    r = get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={fred_id}", 30, 1)
    if r is not None:
        f = pd.read_csv(io.StringIO(r.text)); return anual(f.iloc[:, 0], f.iloc[:, 1], nombre)
    r = get(f"https://api.db.nomics.world/v22/series/IMF/PCPS/M.W00.{imf}.USD?observations=1", 30, 1)
    if r is not None:
        try:
            d = r.json()["series"]["docs"][0]
            return anual([p[:7] + "-01" if len(p) == 7 else p for p in d["period"]], d["value"], nombre)
        except Exception as e: print("  DBnomics:", type(e).__name__)
    print(f"  sin {nombre}: se usará el precio al productor de FAOSTAT"); return None

# ====================================================================== 4) Clima por zona sojera (Open-Meteo / ERA5), un punto por país nuevo
PUNTOS = {"ARG": [(-33.0, -61.5), (-32.5, -63.5), (-27.0, -60.0)],
          "BRA": [(-12.5, -55.7), (-24.5, -51.5), (-28.5, -53.5), (-17.5, -50.0)],
          "PRY": [(-26.0, -55.5), (-24.0, -55.2)], "URY": [(-33.5, -57.5)], "BOL": [(-17.0, -62.5)],
          "USA": [(42.0, -93.5), (40.5, -89.0), (40.5, -86.0)], "CAN": [(43.0, -81.5), (49.5, -98.0)],
          "UKR": [(49.2, 28.5), (49.6, 34.5)], "RUS": [(45.5, 39.5), (50.3, 127.5)],
          "IND": [(23.0, 77.5), (19.5, 76.5)], "CHN": [(47.0, 127.5)],
          # países nuevos (zona sojera principal, coordenadas aproximadas)
          "ITA": [(45.2, 11.0)], "SRB": [(45.3, 19.8)], "ROU": [(44.5, 26.0)], "HUN": [(47.0, 19.5)], "HRV": [(45.5, 18.0)],
          "FRA": [(43.8, 1.0)], "AUT": [(48.0, 15.5)], "ZAF": [(-26.0, 29.2)], "NGA": [(7.7, 8.5)], "ZMB": [(-15.0, 28.0)],
          "MEX": [(23.7, -98.5)], "IDN": [(-7.5, 111.0)], "JPN": [(43.0, 142.5)], "KOR": [(36.5, 127.5)],
          "PRK": [(39.0, 126.5)], "THA": [(18.5, 99.5)], "VNM": [(21.0, 105.5)], "KAZ": [(53.0, 63.0)], "TUR": [(37.0, 35.5)]}

def clima_estacion(df, lat):
    """Agrega diario -> campaña (año de cosecha). HS sur: nov(y-1)-mar(y), crítico ene-feb. HN: may-sep, crítico jul-ago."""
    df = df.copy(); f = pd.to_datetime(df["time"]); m, y = f.dt.month, f.dt.year
    if lat < 0: df["ay"] = np.where(m >= 11, y + 1, y); est = (m >= 11) | (m <= 3); crit = m.isin([1, 2])
    else:       df["ay"] = y;                          est = m.between(5, 9);     crit = m.isin([7, 8])
    df["est"], df["crit"] = est, crit
    df["calor"] = df["temperature_2m_max"] > 32
    a = df[df.est].groupby("ay").agg(prec_est=("precipitation_sum", "sum"), tmax_est=("temperature_2m_max", "mean"), n_est=("calor", "size"))
    b = df[df.crit].groupby("ay").agg(prec_crit=("precipitation_sum", "sum"), dias_calor_crit=("calor", "sum"))
    out = a.join(b); return out[out.n_est >= 140].drop(columns="n_est")      # solo campañas completas

def bajar_clima(paises):
    res = []
    for iso, pts in PUNTOS.items():
        if iso not in paises: continue
        for lat, lon in pts:
            cache = P(f"clima_{lat}_{lon}.csv")
            if os.path.exists(cache): d = pd.read_csv(cache)
            else:
                url = ("https://archive-api.open-meteo.com/v1/archive?"
                       f"latitude={lat}&longitude={lon}&start_date=1994-01-01&end_date=2025-12-31"
                       "&daily=temperature_2m_max,precipitation_sum&timezone=UTC")
                r = get(url, 120, 3, 20)
                if r is None: print("  sin clima en", iso, lat, lon); continue
                d = pd.DataFrame(r.json()["daily"]); d.to_csv(cache, index=False); time.sleep(2)
            c = clima_estacion(d, lat); c["iso3"] = iso; res.append(c.reset_index().rename(columns={"ay": "year"}))
    if not res: return None
    c = pd.concat(res).groupby(["iso3", "year"]).mean().reset_index()
    for v in ["prec_est", "prec_crit", "tmax_est", "dias_calor_crit"]:
        c[v + "_z"] = c.groupby("iso3")[v].transform(lambda s: (s - s.mean()) / s.std())
    c["sequia"] = (c.prec_est_z < -1).astype(int); c["calor_extremo"] = (c.dias_calor_crit_z > 1).astype(int)
    return c

def bajar_oni():
    r = get("https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt", 60)
    if r is None: return None
    f = pd.read_csv(io.StringIO(r.text), sep=r"\s+")
    djf = f[f.SEAS == "DJF"].set_index("YR").ANOM.rename("oni_djf")           # El Niño/La Niña (verano austral)
    jja = f[f.SEAS == "JJA"].set_index("YR").ANOM.rename("oni_jja")
    o = pd.concat([djf, jja], axis=1).reset_index().rename(columns={"YR": "year"}); return o

# ====================================================================== 5) Derechos de exportación y eventos
def tabla_derechos(paises):
    """Soja, tasa nominal fin de año (%). Verificado = 1 solo donde hay fuente; el resto se asume 0 SIN verificar (columna der_verificado)."""
    def ser(base, tramos, desde=ANIO0):
        d = {a: (base if a >= desde else np.nan) for a in range(ANIO0, ANIO1 + 1)}
        for (a, b), v in tramos.items():
            for y in range(a, b + 1): d[y] = v
        return d
    arg_soja = ser(3.5, {(2002, 2006): 23.5, (2007, 2014): 35, (2015, 2017): 30, (2018, 2018): 28,
                         (2019, 2019): 30, (2020, 2024): 33, (2025, 2025): 24}, desde=1996)   # antes de 1996: sin dato verificado
    arg_maiz = ser(0, {(2002, 2006): 20, (2007, 2007): 25, (2008, 2014): 20, (2015, 2017): 0,
                       (2018, 2023): 12, (2024, 2024): 9.5, (2025, 2025): 8.5}, desde=1996)
    arg_trigo = ser(0, {(2002, 2006): 20, (2007, 2007): 28, (2008, 2014): 23, (2015, 2017): 0,
                        (2018, 2023): 12, (2024, 2024): 9.5, (2025, 2025): 7.5}, desde=1996)
    cero = lambda: {a: 0.0 for a in range(ANIO0, ANIO1 + 1)}
    ver = {"ARG": 1, "BRA": 1, "USA": 1, "CAN": 1, "UKR": 1, "RUS": 1}
    filas = []
    for p in paises:
        s = {"ARG": arg_soja, "UKR": ser(0, {(2025, 2025): 10}), "RUS": ser(0, {(2021, 2025): 20})}.get(p, cero())
        m = arg_maiz if p == "ARG" else cero(); t = arg_trigo if p == "ARG" else cero()
        for a in range(ANIO0, ANIO1 + 1):
            filas.append((p, a, s[a], m[a], t[a], ver.get(p, 0)))
    x = pd.DataFrame(filas, columns=["iso3", "year", "der_expo_soja_pct", "der_expo_maiz_pct", "der_expo_trigo_pct", "der_verificado"])
    x["restriccion_export_cuant"] = ((x.iso3 == "BOL") & x.year.between(2008, 2019)).astype(int)
    return x

def parche_cpi_arg(wb):
    """Reemplaza el IPC de Argentina (2004+) por ipc_empalmado.csv (el del Banco Mundial no sirve 2007-2015)."""
    f = P("ipc_empalmado.csv")
    if wb is None or not os.path.exists(f): print("  sin ipc_empalmado.csv en", OUT, "-> TCR de ARG no disponible"); return wb
    m = pd.read_csv(f, index_col=0); m.columns = ["var"]; m.index = pd.PeriodIndex(m.index, freq="M")
    idx = (1 + m["var"] / 100).cumprod(); a = idx.groupby(idx.index.year).mean()
    a = a[(a.index >= 2004) & (a.index <= ANIO1)]
    w = wb[wb.iso3 == "ARG"].set_index("year").cpi.dropna(); com = [y for y in w.index if y in a.index]
    k = (w[com[0]] / a[com[0]]) if com else 1.0                 # empalme con el IPC del Banco Mundial
    wb = wb.copy(); mk = (wb.iso3 == "ARG") & wb.year.isin(a.index)
    wb.loc[mk, "cpi"] = wb.loc[mk, "year"].map(a * k); return wb

def tabla_eventos(paises):
    g = pd.DataFrame([(p, a) for p in paises for a in range(ANIO0, ANIO1 + 1)], columns=["iso3", "year"])
    g["guerra_activa"] = (g.iso3.isin(["UKR", "RUS"]) & (g.year >= 2022)).astype(int)
    g["conflicto_parcial"] = ((g.iso3 == "UKR") & g.year.between(2014, 2021)).astype(int)
    g["guerra_comercial_ee_cn"] = ((g.iso3 == "USA") & g.year.isin([2018, 2019])).astype(int)
    return g

# ====================================================================== 6) Armado
def armar(paises, cult, wb, pint, clima, oni, tax, ev):
    g = pd.DataFrame([(p, a) for p in paises for a in range(ANIO0, ANIO1 + 1)], columns=["iso3", "year"])
    for d in [cult, wb, clima, tax, ev]:
        if d is not None: g = g.merge(d, on=["iso3", "year"], how="left")
    for d in [pint, oni]:
        if d is not None: g = g.merge(d, on="year", how="left")
    for c in ["soja", "maiz", "trigo"]:
        g[f"rend_{c}_t_ha"] = g[f"prod_{c}"] / g[f"area_{c}"]
    g["tau"] = g.der_expo_soja_pct / 100; g["tau_maiz"] = g.der_expo_maiz_pct / 100
    if "cpi" in g and "ner" in g:
        us = g[g.iso3 == "USA"].set_index("year").cpi
        raw = g.ner * g.year.map(us) / g.cpi
        base10 = raw[g.year == 2010].groupby(g.iso3[g.year == 2010]).first()
        g["tcr_bilat"] = 100 * raw / g.iso3.map(base10)
        g["defl_us"] = g.year.map(us / us.get(2015, np.nan))
    g["ing_bruto_ha_soja"] = g.pint_soja * g.rend_soja_t_ha
    g["ing_neto_ha_soja"] = g.pint_soja * (1 - g.tau) * g.rend_soja_t_ha
    g["cuña_ha_soja"] = g.pint_soja * g.tau * g.rend_soja_t_ha
    g["ing_neto_ha_maiz"] = g.pint_maiz * (1 - g.tau_maiz) * g.rend_maiz_t_ha
    g["ing_rel_soja_maiz"] = g.ing_neto_ha_soja / g.ing_neto_ha_maiz
    g["part_soja_area"] = g.area_soja / (g.area_soja + g.area_maiz + g.area_trigo)
    if "defl_us" in g: g["pint_soja_real"] = g.pint_soja / g.defl_us
    return g.sort_values(["iso3", "year"]).reset_index(drop=True)

def main():
    cult = fao_cultivos()
    if cult is None: raise SystemExit("FAOSTAT no respondió; reintentá")
    paises = elegir_paises(cult)
    if "USA" not in paises: paises.append("USA")                      # USA se necesita para el deflactor
    cult = cult[cult.iso3.isin(paises)]
    wb = None
    for cod, nom in WB_IND.items():
        print("Banco Mundial", cod); d = wb_indicador(cod, nom, paises)
        if d is not None: wb = d if wb is None else wb.merge(d, on=["iso3", "year"], how="outer")
    wb = parche_cpi_arg(wb)
    pint = None
    for nom, fred, imf in [("pint_soja", "PSOYBUSDM", "PSOYB"), ("pint_maiz", "PMAIZMTUSDM", "PMAIZMT"), ("pint_trigo", "PWHEAMTUSDM", "PWHEAMT")]:
        d = precio_intl(nom, fred, imf)
        if d is not None: pint = d if pint is None else pint.merge(d, on="year", how="outer")
    print("Clima (Open-Meteo)..."); clima = bajar_clima(paises); oni = bajar_oni()
    g = armar(paises, cult, wb, pint, clima, oni, tabla_derechos(paises), tabla_eventos(paises))
    g.to_csv(P("base_soja_panel_largo.csv"), index=False)
    cols = [c for c in ["area_soja", "pint_soja", "tcr_bilat", "fert_kg_ha", "prec_est", "der_expo_soja_pct"] if c in g]
    print(g.shape); print(g.groupby("iso3")[cols].count().to_string())
    print("\nSuperficie de soja 2015 (Mha), control:", (g[g.year == 2015].set_index("iso3").area_soja / 1e6).round(1).sort_values(ascending=False).head(8).to_dict())

if __name__ == "__main__":
    main()
