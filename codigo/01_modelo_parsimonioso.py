# parsimonioso_rinde.py -- (A) producción de soja ARG ~ precio, retenciones y brecha (con rezagos), forma parsimoniosa
#                          (B) canal de rendimiento: retención -> fertilizante -> rendimiento
import pandas as pd,numpy as np,os,glob
from scipy import stats
def buscar(*nombres):
    for base in ["/content","."]:
        for n in nombres:
            hit=glob.glob(f"{base}/**/{n}",recursive=True)
            if hit: print("usando",hit[0]); return hit[0]
    raise FileNotFoundError(f"No encuentro {nombres}. Subilo a /content.")
d=pd.read_csv(buscar('base_soja_panel_largo.csv','largo.csv'));a=d[d.iso3=='ARG'].set_index('year')
bf=pd.read_csv(buscar('base_final.csv','bf.csv'));br=bf[bf.iso3c=='ARG'].set_index('year').brecha_anual
X=pd.DataFrame(index=range(1996,2026))
X['lP']=np.log(a.prod_soja);X['lA']=np.log(a.area_soja);X['lY']=np.log(a.rend_soja_t_ha)
X['lp']=np.log(a.pint_soja/a.defl_us)                    # precio internacional real (USD constantes)
X['ltau']=np.log(1-a.der_expo_soja_pct/100)                # ln(1-τ) nominal vigente
X['lb']=np.log(br.reindex(X.index).ffill())              # ln brecha cambiaria anual (oficial vs CCL)
X['lw']=X.ltau-X.lb                                        # ln(1-τ efectiva) = ln(1-τ) - ln brecha
X['lF']=np.log(a.fert_kg_ha);X['sq']=a.sequia;X['trend']=X.index-2000

# ---------- Extensión a 2024-2025 ----------
# brecha anual 2024-25: media CCL/oficial desde argentina_mensual.csv (base_final termina en 2023)
try:
    mens=pd.read_csv(buscar('argentina_mensual.csv','mens.csv'));mens['y']=mens.mes.str[:4].astype(int)
    bm=(mens.dolar_contadoconliqui/mens.dolar_oficial).groupby(mens.y).mean()
    for y in range(int(br.index.max())+1,2026):
        if y in bm.index: X.loc[y,'lb']=np.log(bm[y])
    print('brecha anual usada:',{y:round(float(np.exp(X.lb[y])),2) for y in (2023,2024,2025)})
except Exception as ex: print('Sin argentina_mensual.csv; la brecha 2024-25 repite el último valor (sesgo):',str(ex)[:60])
# producción y superficie 2025 (campaña 2024/25) desde MAGyP, ajustadas a la convención FAO (cosechada) con el cociente de 2024
mg=pd.read_csv(buscar('soja_1ra_2da_arg.csv'));tt=mg[mg.cultivo=='soja_total'].groupby('year')[['area_ha','prod_t']].sum()
kk=a.area_soja[2024]/tt.area_ha[2024]
X.loc[2025,'lP']=np.log(tt.prod_t[2025]);X.loc[2025,'lA']=np.log(tt.area_ha[2025]*kk);X.loc[2025,'lY']=X.lP[2025]-X.lA[2025]
print(f'2025 (MAGyP): producción {tt.prod_t[2025]/1e6:.1f} Mt, superficie {tt.area_ha[2025]*kk/1e6:.1f} Mha (ajustada), rinde {np.exp(X.lY[2025]):.2f} t/ha')
def L(c,k): return X[c].shift(k)
def hac(y,Z,Lg=2):
    Z=np.column_stack([np.ones(len(y)),Z]);n,k=Z.shape
    b=np.linalg.lstsq(Z,y,rcond=None)[0];e=y-Z@b;Q=np.linalg.inv(Z.T@Z);u=Z*e[:,None];S=u.T@u
    for l in range(1,Lg+1):
        G=u[l:].T@u[:-l];S+=(1-l/(Lg+1))*(G+G.T)
    V=Q@S@Q*n/(n-k);return b,V,n,k
def run(dep,regs,ctrl=['sq','trend'],start=1998,end=2025):
    cols={};
    for name,(c,ks) in regs.items():
        for k in ks: cols[f'{name}_{k}']=L(c,k)
    for c in ctrl: cols[c]=X[c]
    D=pd.DataFrame(cols);D[dep]=X[dep];D=D.loc[start:end].dropna()
    b,V,n,k=hac(D[dep].values,D[list(cols)].values);return D,list(cols),b,V,n,k
def suma(names,cn,b,V,n,k):
    idx=[1+cn.index(x) for x in names];w=np.zeros(len(b));w[idx]=1
    est=w@b;se=np.sqrt(w@V@w);p=2*(1-stats.t.cdf(abs(est/se),n-k));return est,se,p
def linea(tag,dep,regs,start=1998):
    D,cn,b,V,n,k=run(dep,regs,start=start)
    s=f'{tag:38s} n={n}'
    for name,(c,ks) in regs.items():
        e,se,p=suma([f'{name}_{j}' for j in ks],cn,b,V,n,k);s+=f' | Σ{name}={e:+.2f}({se:.2f}) p={p:.2f}'
    print(s);return D,cn,b,V,n,k
print('\n=== (A) Producción ===')
X['z']=X.lp+X.ltau-X.lb                                    # precio internacional neto de retención y de brecha
for dep,lab in [('lP','ln PRODUCCIÓN'),('lA','ln SUPERFICIE'),('lY','ln RENDIMIENTO')]:
    print('--',lab)
    linea('1. índice z (rez. 1-2)',dep,{'z':('z',[1,2])})
    linea('2. precio y cuña separados (1-2)',dep,{'p':('lp',[1,2]),'w':('lw',[1,2])})
    linea('3. precio, retención, brecha (1-2)',dep,{'p':('lp',[1,2]),'t':('ltau',[1,2]),'b':('lb',[1,2])})
    linea('4. índice z (rez. 1-3)',dep,{'z':('z',[1,2,3])})
    linea('5. z rez. 1-2, 2002-24',dep,{'z':('z',[1,2])},start=2002)
    linea('6. precio y cuña sep., 2002-24',dep,{'p':('lp',[1,2]),'w':('lw',[1,2])},start=2002)
# test de equivalencia precio = (1-τ) = 1/brecha : coef p = coef t = -coef b (spec 3, producción)
D,cn,b,V,n,k=run('lP',{'p':('lp',[1,2]),'t':('ltau',[1,2]),'b':('lb',[1,2])})
ip=[1+cn.index(f'p_{j}') for j in (1,2)];it=[1+cn.index(f't_{j}') for j in (1,2)];ib=[1+cn.index(f'b_{j}') for j in (1,2)]
R=np.zeros((2,len(b)));R[0,ip]=1;R[0,it]=-1;R[1,ip]=1;R[1,ib]=1
r=R@b;W=r@np.linalg.inv(R@V@R.T)@r;print(f'Wald equivalencia (Σp=Σt=-Σb): chi2(2)={W:.2f}, p={1-stats.chi2.cdf(W,2):.2f}')
# efecto implícito (spec 5: índice z, 2002-24, producción): eliminar la retención o neutralizar el cepo
D,cn,b,V,n,k=run('lP',{'z':('z',[1,2])},start=2002);e,se,p=suma(['z_1','z_2'],cn,b,V,n,k)
def ef(dl,etq):
    f=lambda x:100*(np.exp(x*dl)-1);print(f'  {etq}: producción {f(e):+.0f}%  [IC90 {f(e-1.645*se):+.0f}, {f(e+1.645*se):+.0f}]')
ef(-np.log(1-0.35),'eliminar τ=35%');ef(-np.log(1-0.33),'eliminar τ=33%');ef(np.log(.67)-np.log(.45),'neutralizar cepo (τ_ef 55% -> τ_nom 33%)')
print('\n=== (B) Canal de rendimiento: cuña -> fertilizante -> rendimiento ===')
Dd,cn,b1,V1,n1,k1=run('lF',{'w':('lw',[1,2]),'p':('lp',[1,2])},ctrl=['trend'],end=2023)
th=suma(['w_1','w_2'],cn,b1,V1,n1,k1);print(f'lF ~ cuña(1-2), precio(1-2), trend:  Σθ_cuña={th[0]:+.2f}({th[1]:.2f}) p={th[2]:.2f}  n={n1}')
Dd,cn,b2,V2,n2,k2=run('lY',{'F':('lF',[1,2])},ctrl=['sq','trend'],end=2024)
ph=suma(['F_1','F_2'],cn,b2,V2,n2,k2);print(f'lY ~ fert(1-2), sequía, trend:      Σφ_fert={ph[0]:+.2f}({ph[1]:.2f}) p={ph[2]:.2f}  n={n2}')
Dd,cn,b3,V3,n3,k3=run('lY',{'w':('lw',[1,2]),'p':('lp',[1,2])},ctrl=['sq','trend'],end=2024)
rf=suma(['w_1','w_2'],cn,b3,V3,n3,k3);print(f'lY ~ cuña(1-2), precio(1-2), sequía, trend (forma reducida): Σ={rf[0]:+.2f}({rf[1]:.2f}) p={rf[2]:.2f}')
rng=np.random.default_rng(3);med=[]
D1,c1,_,_,_,_=run('lF',{'w':('lw',[1,2]),'p':('lp',[1,2])},ctrl=['trend'],end=2023)
D2,c2,_,_,_,_=run('lY',{'F':('lF',[1,2])},ctrl=['sq','trend'],end=2024)
for r in range(2000):
    i1=rng.integers(0,len(D1),len(D1));i2=rng.integers(0,len(D2),len(D2))
    bb1=np.linalg.lstsq(np.column_stack([np.ones(len(i1)),D1[c1].values[i1]]),D1['lF'].values[i1],rcond=None)[0]
    bb2=np.linalg.lstsq(np.column_stack([np.ones(len(i2)),D2[c2].values[i2]]),D2['lY'].values[i2],rcond=None)[0]
    med.append((bb1[1+c1.index('w_1')]+bb1[1+c1.index('w_2')])*(bb2[1+c2.index('F_1')]+bb2[1+c2.index('F_2')]))
lo,hi=np.percentile(med,[5,95]);print(f'Efecto mediado cuña->fert->rinde (Σθ·Σφ): {th[0]*ph[0]:+.3f}  IC90 [{lo:+.3f},{hi:+.3f}]')

# ================= CONTROLES: otros granos, hacienda mensual y clima extremo como dummies =================
print('\n=== Controles adicionales ===')
# (1) Hacienda mensual (promedio de las semanas del mes), real con IPC mensual empalmado; ventana de siembra sep-dic del año t-1
h=pd.read_csv(buscar('hacienda_semanal.csv'),parse_dates=['fecha'])
hm=h.set_index('fecha').precio_prom.resample('MS').mean().to_frame('hac_ars');hm['mes']=hm.index.strftime('%Y-%m')
try:
    ip=pd.read_csv(buscar('ipc_empalmado.csv'),index_col=0).iloc[:,0].rename('var');ip=(1+ip/100).cumprod();ip.name='ipc'
    hm=hm.join(ip,on='mes');hm['hac_real']=hm.hac_ars/hm.ipc;print('IPC mensual usado para deflactar la hacienda.')
except Exception as ex:
    cpi=a.cpi.rename('cpi_a');hm['hac_real']=hm.hac_ars/hm.index.year.map(cpi);print('Sin IPC mensual, deflacto con IPC anual:',str(ex)[:60])
OUT='/content' if os.path.isdir('/content') else '.';hm.to_csv(f'{OUT}/hacienda_mensual.csv')
mm=hm[hm.index.month.isin([9,10,11,12])];sd=mm.groupby(mm.index.year).hac_real.apply(lambda v:np.log(v).mean())
X['lhac']=sd.reindex(X.index-1).values                                  # valor de la ventana de siembra (sep-dic del año t-1) en la fila de la cosecha t
# (2) Precio de otros granos (control): media geométrica real de maíz y trigo, rezago 1
X['lpg']=0.5*np.log(a.pint_maiz/a.defl_us)+0.5*np.log(a.pint_trigo/a.defl_us)
# (3) Clima extremo como dummies (0/1), no continuo
X['seca']=(((a.prec_crit_z<-1)|(a.prec_est_z<-0.9))).astype(float)       # sequía: déficit en el período crítico o en la estación
X['calor']=(a.dias_calor_crit_z>1).astype(float)                          # estrés térmico extremo en el período crítico
X['nina']=(a.oni_djf<=-1.0).astype(float)                                 # La Niña fuerte (ONI dic-feb <= -1)
print('Años con seca=1:',[int(y) for y in X.index[X.seca==1]]);print('Años con calor=1:',[int(y) for y in X.index[X.calor==1]]);print('Años con nina=1:',[int(y) for y in X.index[X.nina==1]])
def spec(dep,start,ctrl,extra=None,end=2025):
    regs={'z':('z',[1,2])}
    if extra: regs.update(extra)
    D,cn,b,V,n,k=run(dep,regs,ctrl=ctrl,start=start,end=end);e,se,p=suma(['z_1','z_2'],cn,b,V,n,k);return e,se,p,n,k
for ini in [2002,2004]:
    print(f'-- desde {ini}: Σz (elasticidad) con distintos controles; dependiente producción / superficie / rendimiento')
    for tag,ctrl,extra in [('base (sequía vieja + tendencia)',['sq','trend'],None),
                           ('+ otros granos',['sq','trend'],{'g':('lpg',[1])}),
                           ('dummies climáticas + tendencia',['seca','calor','nina','trend'],None),
                           ('dummies + otros granos',['seca','calor','nina','trend'],{'g':('lpg',[1])})]:
        s=f'   {tag:34s}'
        for dep in ['lP','lA','lY']:
            e,se,p,n,k=spec(dep,ini,ctrl,extra);s+=f' | {dep[1]}: {e:+.2f}({se:.2f}) p={p:.2f}'
        print(s+f' | n={n},k={k}')
print('-- con hacienda (siembra sep-dic del año previo), desde 2008')
for tag,ctrl,extra in [('base + dummies',['seca','calor','nina','trend'],None),
                       ('+ otros granos',['seca','calor','nina','trend'],{'g':('lpg',[1])}),
                       ('+ otros granos + hacienda',['seca','calor','nina','trend'],{'g':('lpg',[1]),'h':('lhac',[0])})]:
    s=f'   {tag:30s}'
    for dep in ['lP','lA','lY']:
        e,se,p,n,k=spec(dep,2008,ctrl,extra);s+=f' | {dep[1]}: {e:+.2f}({se:.2f}) p={p:.2f}'
    print(s+f' | n={n},k={k}')
D,cn,b,V,n,k=run('lP',{'z':('z',[1,2]),'g':('lpg',[1])},ctrl=['seca','calor','nina','trend'],start=2004);e,se,p=suma(['z_1','z_2'],cn,b,V,n,k)
print('Efecto de eliminar τ=35% con dummies y otros granos (2004-24):',end=' ')
dl=-np.log(1-0.35);f=lambda x:100*(np.exp(x*dl)-1);print(f'{f(e):+.0f}% [IC90 {f(e-1.645*se):+.0f}, {f(e+1.645*se):+.0f}]')

print('\n=== Efecto de agregar 2025 (dummies + otros granos): elasticidad Σz producción / superficie / rendimiento ===')
for ini in [2002,2004]:
    for fin in [2024,2025]:
        r=[spec(dep,ini,['seca','calor','nina','trend'],{'g':('lpg',[1])},end=fin) for dep in ['lP','lA','lY']]
        print(f'   {ini}-{fin}: '+' | '.join(f'{lab} {x[0]:+.2f}({x[1]:.2f}) p={x[2]:.2f}' for lab,x in zip(['P','A','Y'],r))+f' | n={r[0][3]}')
    D,cn,b,V,n,k=run('lP',{'z':('z',[1,2]),'g':('lpg',[1])},ctrl=['seca','calor','nina','trend'],start=ini,end=2025);e,se,p=suma(['z_1','z_2'],cn,b,V,n,k)
    dl=-np.log(1-0.35);f=lambda x:100*(np.exp(x*dl)-1);print(f'      eliminar τ=35% (hasta 2025): {f(e):+.0f}% [IC90 {f(e-1.645*se):+.0f}, {f(e+1.645*se):+.0f}]')

# ================= DÓLARES DE EXPORTACIÓN PERDIDOS 2004-2023 (aproximación) =================
print('\n=== Dólares de exportación perdidos por las retenciones, 2004-2023 ===')
D,cn,b,V,n,k=run('lP',{'z':('z',[1,2]),'g':('lpg',[1])},ctrl=['seca','calor','nina','trend'],start=2004,end=2025)
i1,i2=1+cn.index('z_1'),1+cn.index('z_2');b1,b2=b[i1],b[i2];e,se,p=suma(['z_1','z_2'],cn,b,V,n,k)
print(f'b1={b1:.2f} b2={b2:.2f} suma={e:.2f} se={se:.2f} n={n}')
Q=a.prod_soja;P=a.pint_soja;dfl=a.defl_us
def calc(eps,efectiva):
    dz=-X.ltau+(X.lb if efectiva else 0)         # Δz = z contrafactual - z observado
    w1,w2=b1/(b1+b2),b2/(b1+b2)
    m=w1*dz.shift(1)+w2*dz.shift(2)
    dq=Q*(np.exp(eps*m)-1);val=dq*P/1e9;real=val*dfl[2023]/dfl
    return dq/1e6,val,real
yrs=list(range(2004,2024))
for efectiva,tag in [(False,'sólo retención nominal'),(True,'retención + brecha (cepo como retención encubierta)')]:
    print('\n==',tag)
    for lab,eps in [('central',e),('IC90 inferior',e-1.645*se),('IC90 superior',e+1.645*se)]:
        dq,val,real=calc(eps,efectiva)
        print(f'  {lab:14s} ε={eps:.2f}: producción perdida acumulada {dq.loc[yrs].sum():6.0f} Mt | USD corrientes {val.loc[yrs].sum():6.1f} mil millones | USD 2023 {real.loc[yrs].sum():6.1f} mil millones')
dq,val,real=calc(e,False);dq2,val2,real2=calc(e,True)
t=pd.DataFrame({'prod_Mt':(Q/1e6).round(1),'perd_nom_Mt':dq.round(1),'USDmM_nom':val.round(2),'perd_ef_Mt':dq2.round(1),'USDmM_ef':val2.round(2),'tau':a.der_expo_soja_pct,'brecha':np.exp(X.lb).round(2)}).loc[yrs]
print(t.to_string())
for lab,(y0,y1) in {'2004-2010':(2004,2010),'2011-2015':(2011,2015),'2016-2019':(2016,2019),'2020-2023':(2020,2023)}.items():
    print(lab,'nominal',round(val.loc[y0:y1].sum(),1),'| efectiva',round(val2.loc[y0:y1].sum(),1))
