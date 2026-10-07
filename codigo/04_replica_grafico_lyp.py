# replica_lyp.py -- Réplica del gráfico "Producción de soja de Argentina y Brasil" (Libertad y Progreso / Etchevarne)
# Hipótesis a contrastar: los datos son de USDA-FAS PSD (campaña comercial). Año del gráfico = año de cosecha = campaña (t-1)/t.
# Fuentes alternativas incluidas para comparar: FAOSTAT (largo) y MAGyP (Argentina). Correr en Colab.
import pandas as pd, numpy as np, io, zipfile, requests, glob, os
import matplotlib.pyplot as plt

URL = "https://apps.fas.usda.gov/psdonline/downloads/psd_oilseeds_csv.zip"
r = requests.get(URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=300); r.raise_for_status()
z = zipfile.ZipFile(io.BytesIO(r.content)); nombre = [n for n in z.namelist() if n.lower().endswith(".csv")][0]
p = pd.read_csv(z.open(nombre), encoding="latin-1")
p.columns = [c.strip().lower() for c in p.columns]
col = lambda *ns: next(c for n in ns for c in p.columns if c == n)
cd, cn, my, at, va = col("commodity_description"), col("country_name"), col("market_year"), col("attribute_description"), col("value")
s = p[(p[cd].str.lower() == "oilseed, soybean") & (p[at].str.strip().str.lower() == "production") & p[cn].isin(["Argentina", "Brazil"])]
U = s.pivot_table(index=my, columns=cn, values=va, aggfunc="first") / 1000      # millones de toneladas
U.index = U.index + 1                                                           # campaña MY/MY+1 -> año de cosecha MY+1
U.columns = ["Argentina_USDA", "Brasil_USDA"]; U.index.name = "year"
print("USDA PSD (año de cosecha):"); print(U.round(1).to_string())

# Comparación con las bases que ya usamos (si están en el directorio)
def buscar(n):
    h = glob.glob(f"**/{n}", recursive=True) + glob.glob(f"/content/**/{n}", recursive=True); return h[0] if h else None
f = buscar("base_soja_panel_largo.csv")
if f:
    d = pd.read_csv(f); F = d[d.iso3.isin(["ARG", "BRA"])].pivot(index="year", columns="iso3", values="prod_soja") / 1e6
    F.columns = ["Argentina_FAO", "Brasil_FAO"]; U = U.join(F)
g = buscar("soja_1ra_2da_arg.csv")
if g:
    m = pd.read_csv(g); M = m[m.cultivo == "soja_total"].groupby("year").prod_t.sum() / 1e6; U = U.join(M.rename("Argentina_MAGyP"))
U.to_csv("comparacion_fuentes_soja.csv"); print("\nComparación de fuentes:"); print(U.loc[1999:2027].round(1).to_string())

# Gráfico en el estilo del original
V = U.loc[1999:2027]
fig, ax = plt.subplots(figsize=(11, 7.5))
ax.plot(V.index, V.Brasil_USDA, color="#548235", lw=2.5, label="Brasil"); ax.plot(V.index, V.Argentina_USDA, color="#0070C0", lw=2.5, label="Argentina")
ax.set_title("Producción de soja de Argentina y Brasil\nEn millones de toneladas (USDA-PSD)", fontsize=14)
ax.set_ylim(0, 200); ax.set_xticks(V.index); ax.set_xticklabels(V.index, rotation=90); ax.grid(axis="y", alpha=.25); ax.legend(loc="upper center", ncol=2, frameon=False)
a0, a1, b0, b1 = V.Argentina_USDA.iloc[0], V.Argentina_USDA.iloc[-1], V.Brasil_USDA.iloc[0], V.Brasil_USDA.iloc[-1]
ax.text(V.index[0], a0 - 8, f"{a0:.1f}", color="#0070C0", fontweight="bold"); ax.text(V.index[0], b0 + 4, f"{b0:.0f}", color="#548235", fontweight="bold")
ax.text(V.index[-1], a1 + 4, f"{a1:.1f}", color="#0070C0", fontweight="bold", ha="right"); ax.text(V.index[-1], b1 + 4, f"{b1:.0f}", color="#548235", fontweight="bold", ha="right")
ax.table(cellText=[["Argentina", f"{a0:.0f}", f"{a1:.0f}", f"{(a1/V.Argentina_USDA.loc[2000]-1)*100:.0f}%"], ["Brasil", f"{b0:.0f}", f"{b1:.0f}", f"{(b1/V.Brasil_USDA.loc[2000]-1)*100:.0f}%"]],
         colLabels=["País", "1999/00", "2026/27", "Var. 2027/2000"], bbox=[.06, .66, .38, .2])
plt.tight_layout(); plt.savefig("replica_lyp.png", dpi=150); plt.show()
