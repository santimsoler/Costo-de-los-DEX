import pandas as pd,numpy as np,matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams.update({'font.family':'DejaVu Sans','axes.spines.top':False,'axes.spines.right':False,'axes.edgecolor':'#9a9a96','axes.labelcolor':'#52514e','xtick.color':'#52514e','ytick.color':'#52514e','figure.facecolor':'#fcfcfb','axes.facecolor':'#fcfcfb','axes.grid':True,'grid.color':'#e6e5e1','grid.linewidth':.8,'axes.axisbelow':True})
B,O,G='#2a78d6','#eb6834','#1baf7a';INK='#0b0b0b';SUB='#52514e'
d=pd.read_csv('datos/base_soja_panel_largo.csv');P=d.pivot(index='year',columns='iso3',values='prod_soja')/1e6
a=d[d.iso3=='ARG'].set_index('year')
U=pd.read_csv('datos/usda_psd_soja.csv').set_index('year')
# --- Fig1: producción anual (USDA-PSD), misma medida que el gráfico original
f,ax=plt.subplots(figsize=(8,4.6));v=U.loc[1999:2025]
ax.plot(v.index,v.Brasil,color=O,lw=2.4);ax.plot(v.index,v.Argentina,color=B,lw=2.4)
w=U.loc[2025:2027];ax.plot(w.index,w.Brasil,color=O,lw=1.6,ls='--');ax.plot(w.index,w.Argentina,color=B,lw=1.6,ls='--')
ax.text(2027.3,w.Brasil.iloc[-1],f'Brasil\n{w.Brasil.iloc[-1]:.0f}',color=INK,va='center',fontsize=10);ax.text(2027.3,w.Argentina.iloc[-1],f'Argentina\n{w.Argentina.iloc[-1]:.0f}',color=INK,va='center',fontsize=10)
ax.text(1999.2,v.Brasil.iloc[0]+5,f'{v.Brasil.iloc[0]:.0f}',color=INK,fontsize=9);ax.text(1999.2,v.Argentina.iloc[0]-11,f'{v.Argentina.iloc[0]:.0f}',color=INK,fontsize=9)
ax.set_xlim(1999,2030);ax.set_ylim(0,200);ax.set_ylabel('Millones de toneladas');ax.set_title('Producción de soja de Argentina y Brasil',loc='left',color=INK,fontsize=12,fontweight='bold')
f.text(.01,.01,'Fuente: USDA-FAS, PSD (año de cosecha). Línea punteada: proyección 2026-2027. Elaboración propia.',fontsize=8,color=SUB);plt.tight_layout(rect=(0,.03,1,1));plt.savefig('figuras/fig1_acumulada.png',dpi=160);plt.close()
# --- Fig2: Argentina como % de Brasil + retención
f,(ax,bx)=plt.subplots(2,1,figsize=(8,6.6),sharex=True,gridspec_kw={'height_ratios':[3,2]})
r=(U.Argentina/U.Brasil*100).loc[1991:2025];ax.plot(r.index,r,color=B,lw=2.2,marker='o',ms=3.5)
ax.set_ylabel('% de la producción de Brasil');ax.set_title('Producción de soja de Argentina como porcentaje de la de Brasil',loc='left',color=INK,fontsize=12,fontweight='bold')
for x,l in [(2002,'2002'),(2007,'2007'),(2015.9,'dic-2015')]: ax.axvline(x,color='#aaa',ls=':',lw=1)
ax.set_ylim(0,90);ax.text(2002.2,6,'2002:\n23,5%',fontsize=8,color=SUB,va='bottom');ax.text(2007.2,6,'2007:\n35%',fontsize=8,color=SUB,va='bottom');ax.text(2015.2,6,'dic-2015:\n30%',fontsize=8,color=SUB,va='bottom',ha='right')
t=pd.read_csv('datos/tauef_campana.csv').set_index('year')
nom=a.der_expo_soja_pct.loc[1996:2024]
bx.step(nom.index,nom,where='post',color=O,lw=2.2);bx.plot(t.index,t.ef_campana*100,color=B,lw=2.2)
bx.text(2024.4,nom.iloc[-1]-3,'nominal',color=INK,fontsize=9);bx.text(2024.4,t.ef_campana.iloc[-1]*100+1.5,'efectiva\n(con brecha)',color=INK,fontsize=9)
bx.set_ylabel('% sobre el valor exportado');bx.set_title('Derecho de exportación a la soja',loc='left',color=INK,fontsize=11,fontweight='bold');bx.set_xlim(1990.5,2028)
f.text(.01,.005,'Fuente: USDA-FAS (PSD); normativa de derechos de exportación (Chequeado, Boletín Oficial); elaboración propia.\nLa retención efectiva suma el costo de la brecha cambiaria.',fontsize=7.5,color=SUB)
plt.tight_layout(rect=(0,.04,1,1));plt.savefig('figuras/fig2_relativa.png',dpi=160);plt.close()
# --- Fig3: superficie por cultivo (MAGyP)
m=pd.read_csv('datos/soja_1ra_2da_arg.csv');N=m.groupby(['year','cultivo']).area_ha.sum().unstack()/1e6;N.index=N.index.astype(int);N=N.loc[2008:2025]
f,ax=plt.subplots(figsize=(8,4.6))
for c,l,col in [('soja_1ra','Soja de primera',B),('maiz_total','Maíz',O),('trigo_total','Trigo',G)]:
    ax.plot(N.index,N[c],color=col,lw=2.4,marker='o',ms=3.5);ax.text(2025.3,N[c].iloc[-1],l,color=INK,va='center',fontsize=10)
ax.axvline(2015.5,color='#aaa',ls=':',lw=1);ax.text(2015.7,1.6,'dic-2015: se eliminan las retenciones\nde maíz y trigo; soja baja de 35% a 30%',fontsize=8.5,color=SUB,va='center')
ax.set_xlim(2008,2028);ax.set_xticks(range(2008,2026,2));ax.set_ylim(0,19);ax.set_ylabel('Millones de hectáreas sembradas');ax.set_title('Argentina: superficie sembrada por cultivo',loc='left',color=INK,fontsize=12,fontweight='bold')
f.text(.01,.01,'Fuente: MAGyP, estimaciones agrícolas (campaña de cosecha). Elaboración propia.',fontsize=8,color=SUB);plt.tight_layout(rect=(0,.03,1,1));plt.savefig('figuras/fig3_cultivos.png',dpi=160);plt.close()
# --- Fig4: efecto estimado
f,ax=plt.subplots(figsize=(8,3.6))
rows=[('Sin retención del 35%\n(muestra 2004-2025)',19,5,35),('Sin retención del 35%\n(muestra 2002-2025)',24,8,42),('Sin cepo (retención efectiva\n55% a 33%, 2004-2025)',17,4,32)]
for i,(l,c,lo,hi) in enumerate(rows[::-1]):
    ax.plot([lo,hi],[i,i],color=B,lw=3,solid_capstyle='round');ax.plot([c],[i],'o',color=B,ms=9,mec='#fcfcfb',mew=2)
    ax.text(hi+1.2,i,f'+{c}%  [+{lo}, +{hi}]',va='center',fontsize=10,color=INK)
ax.set_yticks(range(3));ax.set_yticklabels([r[0] for r in rows[::-1]],fontsize=9.5);ax.axvline(0,color='#888',lw=1)
ax.set_xlim(-2,58);ax.set_xlabel('Aumento estimado de la producción de soja (%, intervalo de confianza 90%)');ax.grid(axis='y',visible=False)
ax.set_title('¿Cuánto más habría producido Argentina?',loc='left',color=INK,fontsize=12,fontweight='bold')
f.text(.01,.01,'Fuente: elaboración propia con FAOSTAT y MAGyP.',fontsize=8,color=SUB);plt.tight_layout(rect=(0,.04,1,1));plt.savefig('figuras/fig4_efecto.png',dpi=160);plt.close()
# --- Fig5: dólares
f,ax=plt.subplots(figsize=(8,4.6));per=['2004-2010','2011-2015','2016-2019','2020-2023'];nm=[13.7,21.9,11.3,12.9];ef=[13.8,31.5,16.4,24.8];x=np.arange(4);w=.38
b1=ax.bar(x-w/2-.01,nm,w,color=B);b2=ax.bar(x+w/2+.01,ef,w,color=O)
for bars in (b1,b2):
    for r in bars: ax.text(r.get_x()+r.get_width()/2,r.get_height()+.6,f'{r.get_height():.1f}'.replace('.',','),ha='center',fontsize=9,color=INK)
ax.set_xticks(x);ax.set_xticklabels(per);ax.set_ylabel('Miles de millones de US$ (corrientes)');ax.grid(axis='x',visible=False)
ax.legend([b1,b2],['Solo retención nominal (total: 59,8)','Retención + brecha cambiaria (total: 86,5)'],frameon=False,loc='upper right',fontsize=9.5)
ax.set_title('Exportaciones de soja que no se hicieron, por período',loc='left',color=INK,fontsize=12,fontweight='bold');ax.set_ylim(0,42)
f.text(.01,.01,'Fuente: elaboración propia (FAOSTAT, FMI). Estimación central; ver intervalos en el texto.',fontsize=8,color=SUB);plt.tight_layout(rect=(0,.03,1,1));plt.savefig('figuras/fig5_dolares.png',dpi=160);plt.close()
print(r.iloc[[0,10,20,24,27,32,33]].round(0).to_dict() if False else (P.ARG/P.BRA*100).loc[[1991,2001,2010,2015,2018,2023,2024]].round(0).to_dict())
