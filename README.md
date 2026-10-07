# Costo de los DEX: retenciones y producción de soja en la Argentina

¿Los derechos de exportación (DEX, "retenciones") afectaron negativamente el volumen producido de soja en la Argentina y en qué cuantía?

**Autor:** Pablo Santiago Martínez Soler — Maestría en Economía Aplicada, UBA

## Resultado principal

Modelo parsimonioso de rezagos distribuidos, Argentina 2004-2025, en logaritmos, con errores robustos Newey-West (2 rezagos):

| Medida | Estimación | Rango (IC 90 %) |
|---|---|---|
| Elasticidad de la producción al precio neto | 0,40 (e.e. 0,18; p = 0,04) | — |
| Elasticidad de la superficie | ≈ 0,26 | — |
| Rendimiento por hectárea | sin efecto detectable | — |
| Eliminar una retención de 35 % | +19 % de producción (≈ −16 % causado por el impuesto) | +5 % a +35 % |
| Idem, muestra desde 2002 | +24 % | +8 % a +42 % |
| Neutralizar el cepo (retención efectiva de 55 % a 33 %) | +17 % | +4 % a +32 % |
| Exportaciones no realizadas 2004-2023, solo retención | US$ 59.800 millones (corrientes) | 14.500 a 110.600 |
| Idem, contando la brecha cambiaria | US$ 86.500 millones (corrientes) | 20.300 a 166.000 |

El índice de precio neto es `z = ln p + ln(1 − τ) − ln B` (p: precio internacional real; τ: retención; B: brecha CCL/oficial), con rezagos de 1 y 2 años. Controles: variables ficticias de sequía, calor extremo y La Niña fuerte, tendencia y precio real de maíz y trigo.

Supuestos del cálculo en dólares: toda la producción adicional se exporta, el precio mundial no cambia y no se considera la recaudación fiscal. Es un orden de magnitud, no una predicción. El estudio se apoya en un único país tratado y en pocos cambios de alícuota.

## Estructura

```
datos/        series usadas (FAOSTAT, MAGyP, FMI, BCRA/mercado, alícuotas)
codigo/       scripts (ver orden abajo)
figuras/      gráficos del documento
documento/    gacetilla en PDF
```

## Cómo reproducir

```
pip install -r requirements.txt
python codigo/01_modelo_parsimonioso.py   # estimación, efectos y dólares perdidos
python codigo/02_figuras.py               # figuras en figuras/
python codigo/03_ml_superficie.py         # ejercicio de predicción de superficie
python codigo/04_replica_grafico_lyp.py   # réplica del gráfico Argentina-Brasil con USDA (requiere conexión)
```

Ejecutar siempre desde la raíz del repositorio. Los scripts `bajar_*.py` regeneran las bases desde las fuentes (requieren conexión).

## Fuentes de datos

- FAO, FAOSTAT (QCL): producción, superficie y rendimiento.
- USDA-FAS, PSD Online: producción de soja de Argentina y Brasil por campaña (`datos/usda_psd_soja.csv`).
- Ministerio de Agricultura, Ganadería y Pesca: estimaciones agrícolas (soja de 1ra y 2da, otros cultivos, por provincia).
- FMI, Primary Commodity Prices: precios internacionales.
- Decretos 133/2015, 1343/2016 y 230/2020 y cronología de alícuotas (Chequeado, Escuela de Gobierno de la Universidad Austral).

## Licencia

MIT. Ver `LICENSE`.
