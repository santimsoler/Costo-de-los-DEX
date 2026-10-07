# ml_superficie.py -- ML: predecir el cambio de superficie de soja por provincia (Δ ln área) con precios, retenciones, brecha, etc.
# Validación hacia adelante (se entrena con años < t y se predice t). Compara conjuntos de variables y mide importancia.
import pandas as pd,numpy as np,os,glob,warnings;warnings.filterwarnings('ignore')
from sklearn.linear_model import RidgeCV
from sklearn.ensemble import HistGradientBoostingRegressor,RandomForestRegressor
from sklearn.inspection import permutation_importance
def buscar(*nombres):
    for base in ["/content","."]:
        for n in nombres:
            hit=glob.glob(f"{base}/**/{n}",recursive=True)
            if hit: print("usando",hit[0]); return hit[0]
    raise FileNotFoundError(f"No encuentro {nombres}. Subilo a /content.")
d=pd.read_csv(buscar('base_soja_panel_largo.csv','largo.csv'));a=d[d.iso3=='ARG'].set_index('year')
bf=pd.read_csv(buscar('base_final.csv','bf.csv'));br=bf[bf.iso3c=='ARG'].set_index('year').brecha_anual
c=pd.read_csv(buscar('cultivos_provincia_arg.csv'))
P=c.pivot_table(index=['provincia','year'],columns='cultivo',values='area_ha',aggfunc='sum').reset_index()
P['year']=P.year.astype(int)
grande=P[P.year.between(2005,2020)].groupby('provincia').soja.mean();prov=grande[grande>30e3].index
P=P[P.provincia.isin(prov)&P.year.between(1993,2024)].sort_values(['provincia','year']).copy()
P['lA']=np.log(P.soja.clip(lower=1))
g=P.groupby('provincia')
P['y']=g.lA.diff()                                    # variable a predecir: Δ ln superficie de soja
P['dA1']=g.y.shift(1);P['dA2']=g.y.shift(2);P['lA1']=g.lA.shift(1)
P['sh1']=(P.soja/(P.soja+P.maiz.fillna(0)+P.trigo.fillna(0))).groupby(P.provincia).shift(1)
P['dM1']=np.log(P.maiz.clip(lower=1)).groupby(P.provincia).diff().groupby(P.provincia).shift(1)
N=pd.DataFrame(index=range(1990,2025))
N['pS']=np.log(a.pint_soja/a.defl_us);N['pM']=np.log(a.pint_maiz/a.defl_us);N['relp']=N.pS-N.pM
N['tau_s']=a.der_expo_soja_pct/100;N['tau_m']=a.der_expo_maiz_pct/100
N['brecha']=np.log(br.reindex(N.index).ffill());N['oni']=a.oni_djf;N['fert']=np.log(a.fert_kg_ha)
N1=N.shift(1);N1.columns=[x+'_1' for x in N.columns]
P=P.merge(N1,left_on='year',right_index=True,how='left')
F0=['dA1','dA2','lA1','sh1','dM1']                    # propias de la provincia
F1=F0+['pS_1','pM_1','relp_1','oni_1','fert_1']   # + precios y macro
F2=F1+['tau_s_1','tau_m_1','brecha_1']                # + retenciones y brecha
P=P.dropna(subset=['y']+F2).reset_index(drop=True)
print(f'Panel: {P.provincia.nunique()} provincias, {P.year.min()}-{P.year.max()}, n={len(P)}')
def mk(kind):
    if kind=='ridge': return RidgeCV(alphas=np.logspace(-2,3,20))
    if kind=='gbm':   return HistGradientBoostingRegressor(max_depth=3,learning_rate=0.05,max_iter=200,min_samples_leaf=15,random_state=0)
    return RandomForestRegressor(n_estimators=300,min_samples_leaf=8,max_features=0.5,random_state=0,n_jobs=-1)
def estandar(tr,te,F):
    mu,sd=tr[F].mean(),tr[F].std().replace(0,1);return ((tr[F]-mu)/sd).values,((te[F]-mu)/sd).values
def cv(F,kind,y0=2008):
    e=[];base=[]
    for t in range(y0,2025):
        tr=P[P.year<t];te=P[P.year==t]
        if len(te)==0: continue
        A,B=estandar(tr,te,F);m=mk(kind).fit(A,tr.y.values);e.append((te.y.values-m.predict(B)));base.append(te.y.values-tr.y.mean())
    e=np.concatenate(e);base=np.concatenate(base);return np.sqrt((e**2).mean()),np.sqrt((base**2).mean())
print('\n=== Validación hacia adelante 2008-2024: RMSE de Δln superficie (menor = mejor); referencia = promedio histórico ===')
print(f'{"modelo":7s} {"propias":>9s} {"+precios":>9s} {"+retenc/brecha":>15s}')
for kind in ['ridge','gbm','rf']:
    r=[cv(F,kind) for F in (F0,F1,F2)];print(f'{kind:7s} {r[0][0]:9.3f} {r[1][0]:9.3f} {r[2][0]:15.3f}   (referencia {r[0][1]:.3f})')
# importancia por grupos (random forest entrenado hasta 2015, evaluado 2016-2024)
tr=P[P.year<=2015];te=P[P.year>2015];A,B=estandar(tr,te,F2);m=mk('rf').fit(A,tr.y.values)
grupos={'propias':F0,'precios y macro':['pS_1','pM_1','relp_1','oni_1','fert_1'],'retenciones':['tau_s_1','tau_m_1'],'brecha':['brecha_1']}
rng=np.random.default_rng(0);base_mse=((te.y.values-m.predict(B))**2).mean();print(f'\nImportancia por permutación (entrena <=2015, evalúa 2016-24; MSE base={base_mse:.4f}):')
for gname,cols in grupos.items():
    inc=[]
    for r in range(50):
        Bp=B.copy()
        for cname in cols: Bp[:,F2.index(cname)]=rng.permutation(Bp[:,F2.index(cname)])
        inc.append(((te.y.values-m.predict(Bp))**2).mean()-base_mse)
    print(f'  {gname:18s} aumento del MSE al permutar: {np.mean(inc):+.4f}')
# dependencia parcial (modelo final con toda la muestra): efecto marginal predicho de tau_s y brecha sobre Δln superficie
A,B=estandar(P,P,F2);m=mk('rf').fit(A,P.y.values)
def dp(col,grid):
    out=[]
    for v in grid:
        X=P[F2].copy();X[col]=v;mu,sd=P[F2].mean(),P[F2].std();out.append(m.predict(((X-mu)/sd).values).mean())
    return np.array(out)
g1=np.array([.035,.20,.235,.30,.35]);r1=dp('tau_s_1',g1);print('\nDependencia parcial: Δln superficie predicho según retención de soja del año previo:')
for x,y in zip(g1,r1): print(f'  τ={x:.3f}: {100*y:+.1f}%')
g2=np.log([1.0,1.2,1.5,1.9]);r2=dp('brecha_1',g2);print('Dependencia parcial según brecha cambiaria del año previo:')
for x,y in zip(np.exp(g2),r2): print(f'  brecha={x:.2f}: {100*y:+.1f}%')
