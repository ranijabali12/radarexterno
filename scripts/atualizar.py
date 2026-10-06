"""
Radar de Demanda Externa - robô de atualização.
Roda no GitHub Actions (semanal) ou localmente: python scripts/atualizar.py
Busca: Fiocruz (SRAG), Google Trends, Open-Meteo (clima) e InfoDengue (dengue).
Se uma fonte falhar, usa a base salva / padrão típico e registra o aviso para a página.
Saída: data/sinais.json
"""
import json, time, datetime as dt, io, os, sys, math
import numpy as np, pandas as pd

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.join(RAIZ, 'data', 'base')
OFFLINE = '--offline' in sys.argv
HOJE = dt.date.today()
MES0 = pd.Timestamp(HOJE.year, HOJE.month, 1)
INI = pd.Timestamp('2022-01-01'); INI_N = pd.Timestamp('2022-03-01')

CAP = {'AC':('Rio Branco',-9.97,-67.81,'1200401'),'AL':('Maceió',-9.67,-35.74,'2704302'),'AM':('Manaus',-3.12,-60.02,'1302603'),
'AP':('Macapá',0.03,-51.07,'1600303'),'BA':('Salvador',-12.97,-38.50,'2927408'),'CE':('Fortaleza',-3.73,-38.53,'2304400'),
'DF':('Brasília',-15.79,-47.88,'5300108'),'ES':('Vitória',-20.32,-40.34,'3205309'),'GO':('Goiânia',-16.68,-49.25,'5208707'),
'MA':('São Luís',-2.53,-44.30,'2111300'),'MG':('Belo Horizonte',-19.92,-43.94,'3106200'),'MS':('Campo Grande',-20.44,-54.65,'5002704'),
'MT':('Cuiabá',-15.60,-56.10,'5103403'),'PA':('Belém',-1.46,-48.49,'1501402'),'PB':('João Pessoa',-7.12,-34.86,'2507507'),
'PE':('Recife',-8.05,-34.88,'2611606'),'PI':('Teresina',-5.09,-42.80,'2211001'),'PR':('Curitiba',-25.43,-49.27,'4106902'),
'RJ':('Rio de Janeiro',-22.91,-43.17,'3304557'),'RN':('Natal',-5.79,-35.21,'2408102'),'RO':('Porto Velho',-8.76,-63.90,'1100205'),
'RR':('Boa Vista',2.82,-60.67,'1400100'),'RS':('Porto Alegre',-30.03,-51.23,'4314902'),'SC':('Florianópolis',-27.60,-48.55,'4205407'),
'SE':('Aracaju',-10.91,-37.07,'2800308'),'SP':('São Paulo',-23.55,-46.63,'3550308'),'TO':('Palmas',-10.18,-48.33,'1721000')}
POP = {'AC':887794,'AL':3221128,'AM':4360926,'AP':809953,'BA':14889472,'CE':9302211,'DF':3009996,'ES':4150692,'GO':7495033,'MA':7024557,
'MG':21460311,'MS':2946317,'MT':3950330,'PA':8756324,'PB':4182828,'PE':9583176,'PI':3392617,'PR':11952524,'RJ':17225410,'RN':3463737,
'RO':1757338,'RR':761012,'RS':11233317,'SC':8312691,'SE':2307255,'SP':46179008,'TO':1595994}
REG = {'Norte':['AC','AM','AP','PA','RO','RR','TO'],'Nordeste':['AL','BA','CE','MA','PB','PE','PI','RN','SE'],
       'Centro-Oeste':['DF','GO','MS','MT'],'Sudeste':['ES','MG','RJ','SP'],'Sul':['PR','RS','SC']}
UF2REG = {u:r for r,us in REG.items() for u in us}
REGS = list(REG)
POPR = {r:sum(POP[u] for u in us) for r,us in REG.items()}
SINAIS = [('Saúde: SRAG','SRAG (Fiocruz)','Saúde'),('Saúde: dengue','Dengue','Saúde'),('Busca: Gripe','Buscas "gripe"','Buscas no Google'),
 ('Busca: dor de garganta','Buscas "dor de garganta"','Buscas no Google'),('Busca: candidíase','Buscas "candidíase"','Buscas no Google'),
 ('Busca: pele ressecada','Buscas "pele ressecada"','Buscas no Google'),('Clima: temp. mínima','Temperatura mínima','Clima'),
 ('Clima: temp. máxima','Temperatura máxima','Clima'),('Clima: umidade','Umidade do ar','Clima'),('Clima: chuva','Chuva','Clima')]
TERMOS = {'Busca: Gripe':'Gripe','Busca: dor de garganta':'dor de garganta','Busca: candidíase':'candidíase','Busca: pele ressecada':'pele ressecada'}
CLIMA_VARS = {'Clima: temp. mínima':('temperature_2m_min','media'),'Clima: temp. máxima':('temperature_2m_max','media'),
              'Clima: umidade':('relative_humidity_2m_mean','media'),'Clima: chuva':('precipitation_sum','soma')}
MESES_PT=['janeiro','fevereiro','março','abril','maio','junho','julho','agosto','setembro','outubro','novembro','dezembro']
NOME={'Saúde: SRAG':'casos de síndrome respiratória (Fiocruz)','Saúde: dengue':'casos de dengue','Busca: Gripe':'buscas no Google por "gripe"',
'Busca: dor de garganta':'buscas por "dor de garganta"','Busca: candidíase':'buscas por "candidíase"','Busca: pele ressecada':'buscas por "pele ressecada"',
'Clima: temp. mínima':'temperatura mínima','Clima: temp. máxima':'temperatura máxima','Clima: umidade':'umidade do ar','Clima: chuva':'chuva'}
# Padrões típicos (usados só quando a fonte falha)
NORM={'Clima: temp. mínima':{'Norte':[23.6,23.5,23.6,23.7,23.7,23.3,23.0,23.2,23.6,23.9,24.0,23.8],'Nordeste':[24.0,24.2,24.3,23.8,23.0,22.2,21.6,21.6,22.3,23.0,23.5,23.8],'Centro-Oeste':[19.5,19.5,19.5,18.7,16.5,14.8,14.5,16.0,18.3,19.5,19.6,19.6],'Sudeste':[19.5,19.7,19.0,17.3,14.8,13.4,12.9,13.8,15.3,16.8,17.9,19.0],'Sul':[19.3,19.5,18.3,15.5,12.4,10.5,9.8,11.0,12.6,14.8,16.6,18.3]},
'Clima: temp. máxima':{'Norte':[31.0,30.8,31.0,31.0,31.3,31.5,32.0,33.0,33.5,33.3,32.8,31.8],'Nordeste':[31.0,31.2,31.0,30.3,29.4,28.4,27.9,28.4,29.4,30.3,30.8,31.0],'Centro-Oeste':[29.8,30.0,30.0,29.8,28.8,28.2,28.8,31.0,32.2,31.6,30.2,29.6],'Sudeste':[29.0,29.6,28.8,27.4,25.4,24.4,24.3,25.7,26.5,27.2,27.8,28.5],'Sul':[29.0,28.9,27.6,24.8,21.7,19.6,19.2,20.8,22.0,24.2,26.2,28.0]},
'Clima: umidade':{'Norte':[86,88,88,88,86,83,80,78,77,78,80,83],'Nordeste':[77,78,80,82,83,82,81,78,76,75,75,76],'Centro-Oeste':[76,77,77,73,66,59,52,46,50,62,72,76],'Sudeste':[77,76,77,76,75,73,70,66,68,72,74,77],'Sul':[74,76,77,79,81,82,81,78,77,75,72,72]},
'Clima: chuva':{'Norte':[280,300,330,300,250,120,80,60,70,100,140,210],'Nordeste':[90,110,180,220,200,150,120,70,40,30,30,50],'Centro-Oeste':[250,210,200,110,40,10,8,15,50,150,220,260],'Sudeste':[260,200,170,80,60,40,35,35,70,120,160,230],'Sul':[150,145,120,110,110,120,130,110,140,150,120,130]}}
DENG=[1.4,2.2,2.9,2.8,1.9,0.8,0.4,0.25,0.2,0.25,0.4,0.8]
STATUS={}

def get(url, params=None, tries=4, wait=30, text=False):
    import requests
    for t in range(tries):
        try:
            r = requests.get(url, params=params, timeout=120)
            if r.status_code == 200: return r.text if text else r.json()
            print('  status', r.status_code, url)
        except Exception as e: print('  erro', e)
        time.sleep(wait)
    raise RuntimeError('falhou: ' + url)

def ponderar(df, col='Valor'):
    """df: UF, Mes, Valor -> Regiao, Mes, Valor (média ponderada pela população)"""
    df = df.copy(); df['Regiao'] = df.UF.map(UF2REG); df['p'] = df.UF.map(POP)
    g = df.dropna(subset=[col]).groupby(['Regiao','Mes']).apply(lambda x: np.average(x[col], weights=x.p), include_groups=False)
    return g.rename('Valor').reset_index()

# ---------------- FONTES ----------------
def fonte_srag():
    url = 'https://raw.githubusercontent.com/infogripe/Boletim_InfoGripe/main/Dados/InfoGripe/estados_e_pais_serie_estimativas_tendencia_sem_filtro_febre.csv'
    try:
        if OFFLINE: raise RuntimeError('offline')
        txt = get(url, text=True); d = pd.read_csv(io.StringIO(txt), sep=';', decimal=',')
        d.to_csv(os.path.join(BASE,'fiocruz_srag.csv'), sep=';', decimal=',', index=False)
        STATUS['fiocruz'] = {'status':'ok','detalhe':'InfoGripe/Fiocruz atualizado nesta execução'}
    except Exception as e:
        d = pd.read_csv(os.path.join(BASE,'fiocruz_srag.csv'), sep=';', decimal=',')
        STATUS['fiocruz'] = {'status':'base','detalhe':'Fiocruz indisponível: usando a última base salva'}
    d = d[(d.escala=='incidência') & (d.DS_UF_SIGLA!='BR')].copy()
    def ini(y,w):
        j4 = dt.date(int(y),1,4); s = j4 - dt.timedelta(days=(j4.weekday()+1)%7); return s + dt.timedelta(weeks=int(w)-1)
    d['ini'] = pd.to_datetime([ini(y,w) for y,w in zip(d['Ano epidemiológico'], d['Semana epidemiológica'])])
    d['Mes'] = d.ini.dt.to_period('M').dt.to_timestamp()
    m = d.groupby(['DS_UF_SIGLA','Mes'])['casos estimados'].mean().reset_index(); m.columns = ['UF','Mes','Valor']
    STATUS['fiocruz']['ate'] = str(d.ini.max().date())
    return ponderar(m)

def fonte_trends():
    base = pd.read_csv(os.path.join(BASE,'trends_mensal.csv'), parse_dates=['Mes'])
    novos = []; falhas = 0
    if not OFFLINE:
        try:
            from pytrends.request import TrendReq
            py = TrendReq(hl='pt-BR', tz=180, retries=2, backoff_factor=2)
            for termo in TERMOS.values():
                for uf in POP:
                    try:
                        py.build_payload([termo], timeframe='today 5-y', geo=f'BR-{uf}')
                        x = py.interest_over_time()
                        if x.empty: raise RuntimeError('vazio')
                        x = x[[termo]].reset_index(); x.columns = ['Data','Interesse']
                        x['Mes'] = x.Data.dt.to_period('M').dt.to_timestamp()
                        mm = x.groupby('Mes').Interesse.mean().reset_index(); mm['UF']=uf; mm['Termo']=termo; novos.append(mm)
                        time.sleep(4)
                    except Exception as e:
                        falhas += 1; time.sleep(10)
                        if falhas > 8: raise RuntimeError('Google Trends bloqueou as consultas')
        except Exception as e:
            print('Trends:', e)
    if novos and falhas == 0:
        t = pd.concat(novos); t.to_csv(os.path.join(BASE,'trends_mensal.csv'), index=False)
        STATUS['trends'] = {'status':'ok','detalhe':'Google Trends atualizado nesta execução'}
    else:
        t = base
        if novos:  # parcial: atualiza o que veio
            t = pd.concat([base, pd.concat(novos)]).drop_duplicates(['UF','Termo','Mes'], keep='last')
        STATUS['trends'] = {'status':'base','detalhe':'Não foi possível atualizar o Google Trends: usando os dados salvos até '+str(base.Mes.max().date())[:7]}
    t = t[t.Mes < MES0]
    # qualidade: descarta estados com muitos zeros
    out = {}
    for sig, termo in TERMOS.items():
        x = t[t.Termo.str.lower()==termo.lower()]
        z = x.groupby('UF').Interesse.apply(lambda s:(s==0).mean())
        x = x[x.UF.isin(z[z<=0.35].index)][['UF','Mes','Interesse']].rename(columns={'Interesse':'Valor'})
        out[sig] = ponderar(x) if len(x) else None
    return out

def fonte_clima():
    hist_path = os.path.join(BASE,'clima_hist.csv')
    vars_ = ','.join(v for v,_ in CLIMA_VARS.values())
    try:
        if OFFLINE: raise RuntimeError('offline')
        hist = pd.read_csv(hist_path, parse_dates=['Data']) if os.path.exists(hist_path) else pd.DataFrame()
        ini = (hist.Data.max()+pd.Timedelta(days=1)).date() if len(hist) else dt.date(2022,1,1)
        fim = HOJE - dt.timedelta(days=7); novos=[]
        if ini <= fim:
            for uf,(c,la,lo,g) in CAP.items():
                j = get('https://archive-api.open-meteo.com/v1/archive', {'latitude':la,'longitude':lo,'start_date':str(ini),'end_date':str(fim),'daily':vars_,'timezone':'America/Sao_Paulo'})
                x = pd.DataFrame(j['daily']).rename(columns={'time':'Data'}); x['UF']=uf; novos.append(x); time.sleep(15)
            hist = pd.concat([hist]+[n.assign(Data=pd.to_datetime(n.Data)) for n in novos])
            hist.to_csv(hist_path, index=False)
        prev=[]
        for uf,(c,la,lo,g) in CAP.items():
            j = get('https://seasonal-api.open-meteo.com/v1/seasonal', {'latitude':la,'longitude':lo,'models':'ecmwf_seasonal_ensemble_mean_seamless','forecast_days':183,'daily':vars_,'timezone':'America/Sao_Paulo'})
            x = pd.DataFrame(j['daily']).rename(columns={'time':'Data'}); x['UF']=uf; prev.append(x); time.sleep(3)
        prev = pd.concat(prev); prev['Data']=pd.to_datetime(prev.Data)
        STATUS['clima'] = {'status':'ok','detalhe':'Open-Meteo: histórico real + previsão sazonal (EC46/SEAS5)'}
        def mensal(df):
            df = df.copy(); df['Mes'] = df.Data.dt.to_period('M').dt.to_timestamp(); res = {}
            for sig,(v,ag) in CLIMA_VARS.items():
                if v not in df: continue
                m = df.groupby(['UF','Mes'])[v].mean()
                if ag == 'soma': m = m * pd.DatetimeIndex(m.index.get_level_values('Mes')).days_in_month.values
                res[sig] = ponderar(m.rename('Valor').reset_index())
            return res
        return mensal(hist[hist.Data < MES0]), mensal(prev)
    except Exception as e:
        print('Clima:', e)
        STATUS['clima'] = {'status':'tipico','detalhe':'Clima indisponível: usando o padrão típico de cada região (normais climatológicas aproximadas), sem previsão'}
        return None, None

def fonte_dengue():
    try:
        if OFFLINE: raise RuntimeError('offline')
        linhas=[]
        for uf,(c,la,lo,geo) in CAP.items():
            txt = get('https://info.dengue.mat.br/api/alertcity', {'geocode':geo,'disease':'dengue','format':'csv','ew_start':1,'ew_end':53,'ey_start':2022,'ey_end':HOJE.year}, text=True)
            d = pd.read_csv(io.StringIO(txt))
            if pd.api.types.is_numeric_dtype(d.data_iniSE): d['data_iniSE']=pd.to_datetime(d.data_iniSE, unit='ms')
            else: d['data_iniSE']=pd.to_datetime(d.data_iniSE)
            d['Mes']=d.data_iniSE.dt.to_period('M').dt.to_timestamp()
            m=d.groupby('Mes').casos_est.sum().reset_index(); m['UF']=uf; m['Valor']=m.casos_est/ (POP[uf]/1e5); linhas.append(m[['UF','Mes','Valor']]); time.sleep(1)
        STATUS['dengue']={'status':'ok','detalhe':'InfoDengue atualizado nesta execução (capitais)'}
        x=pd.concat(linhas); return ponderar(x[x.Mes<MES0])
    except Exception as e:
        print('Dengue:', e)
        STATUS['dengue']={'status':'tipico','detalhe':'Dengue indisponível: usando o perfil sazonal típico (pico de fevereiro a maio)'}
        return None

NOMES_UF = {'acre':'AC','alagoas':'AL','amapa':'AP','amazonas':'AM','bahia':'BA','ceara':'CE','distrito federal':'DF','espirito santo':'ES',
 'goias':'GO','maranhao':'MA','mato grosso':'MT','mato grosso do sul':'MS','minas gerais':'MG','para':'PA','paraiba':'PB','parana':'PR',
 'pernambuco':'PE','piaui':'PI','rio de janeiro':'RJ','rio grande do norte':'RN','rio grande do sul':'RS','rondonia':'RO','roraima':'RR',
 'santa catarina':'SC','sao paulo':'SP','sergipe':'SE','tocantins':'TO'}
COD_UF = {'11':'RO','12':'AC','13':'AM','14':'RR','15':'PA','16':'AP','17':'TO','21':'MA','22':'PI','23':'CE','24':'RN','25':'PB','26':'PE',
 '27':'AL','28':'SE','29':'BA','31':'MG','32':'ES','33':'RJ','35':'SP','41':'PR','42':'SC','43':'RS','50':'MS','51':'MT','52':'GO','53':'DF'}
def _uf_de(props):
    import unicodedata
    for k in ('codarea','codigo_ibg','cod_uf','CD_UF','id'):
        v = str(props.get(k,''))[:2]
        if v in COD_UF: return COD_UF[v]
    for k in ('sigla','SIGLA','UF','uf','SIGLA_UF','abbrev'):
        v = str(props.get(k,'')).upper()
        if v in POP: return v
    for k in ('name','nome','NOME','NM_UF','Estado'):
        v = unicodedata.normalize('NFKD', str(props.get(k,''))).encode('ascii','ignore').decode().lower().strip()
        if v in NOMES_UF: return NOMES_UF[v]
    return None
def fonte_mapas():
    """Mapa detalhado: baixa os estados (IBGE ou espelhos), junta por região e salva data/base/mapa_regioes.geojson."""
    alvo = os.path.join(BASE,'mapa_regioes.geojson')
    if os.path.exists(alvo):
        STATUS['mapa'] = {'status':'ok','detalhe':'Mapa detalhado por região (salvo)'}; return
    fontes = [('https://servicodados.ibge.gov.br/api/v3/malhas/paises/BR', {'formato':'application/vnd.geo+json','qualidade':'intermediaria','intrarregiao':'UF'}),
              ('https://raw.githubusercontent.com/codeforgermany/click_that_hood/main/public/data/brazil-states.geojson', None),
              ('https://raw.githubusercontent.com/giuliano-oliveira/geodata-br-states/main/geojson/br_states.json', None)]
    try:
        if OFFLINE: raise RuntimeError('offline')
        import requests
        from shapely.geometry import shape, mapping
        from shapely.ops import unary_union
        geo = None
        for url, params in fontes:
            try:
                r = requests.get(url, params=params, timeout=120); r.raise_for_status(); g = r.json()
                ufs = {_uf_de(f.get('properties',{})): f for f in g.get('features',[])}
                if len([u for u in ufs if u]) >= 27: geo = ufs; print('Mapa:', url); break
            except Exception as e: print('Mapa falhou em', url, e)
        if geo is None: raise RuntimeError('nenhuma fonte de mapa respondeu')
        feats = []
        for reg, ufs in REG.items():
            poly = unary_union([shape(geo[u]['geometry']).buffer(0) for u in ufs]).simplify(0.004, preserve_topology=True)
            gm = mapping(poly)
            def arred(c):
                return [arred(x) for x in c] if isinstance(c[0], (list, tuple)) else [round(c[0],4), round(c[1],4)]
            gm = {'type': gm['type'], 'coordinates': arred(gm['coordinates'])}
            feats.append({'type':'Feature','properties':{'regiao':reg},'geometry':gm})
        with open(alvo,'w',encoding='utf-8') as f: json.dump({'type':'FeatureCollection','features':feats}, f)
        STATUS['mapa'] = {'status':'ok','detalhe':'Mapa detalhado por região baixado nesta execução'}
    except Exception as e:
        print('Mapa:', e)
        STATUS['mapa'] = {'status':'base','detalhe':'Mapa detalhado ainda não foi baixado: usando o mapa simplificado por região'}

# ---------------- CÁLCULO ----------------
MESES = [MES0 + pd.DateOffset(months=k) for k in range(6)]
def rot(m,k): s=MESES_PT[m.month-1].capitalize()+f'/{m.year}'; return s+(' (este mês)' if k==0 else '')
def pct(v): return f"{abs(v)*100:.0f}%"
def num(v): return f"{abs(v):.1f}".replace('.',',')
def cap(s): return s[0].upper()+s[1:]

def stats_serie(ser, sig, previsao=None):
    """ser: DataFrame Mes, Valor (mensal, uma região). Retorna dict com z/conf/fato p/ 6 meses + histórico."""
    s = ser[(ser.Mes>=INI)&(ser.Mes<MES0)].sort_values('Mes').set_index('Mes').Valor
    if len(s) < 18: return None
    df = pd.DataFrame({'v':s}); df['mn']=df.index.month
    N = df[df.index>=INI_N].groupby('mn').v.mean(); df['N']=df.mn.map(N); media = N.mean()
    busca = sig.startswith('Busca')
    df['aj'] = (df.v.shift(1).rolling(12).mean()-media).fillna(0) if busca else 0.0
    df['an'] = df.v-df.N-df.aj
    b = df[df.index>=INI_N]
    sdA = b.an.std(); sdT = (b.v-b.aj).std()
    a = b.an.values; r = np.corrcoef(a[:-1],a[1:])[0,1] if len(a)>4 else 0; r = 0 if (np.isnan(r) or r<0) else r
    r2s = max(0, 1-(sdA/sdT)**2) if sdT>0 else 0
    last = df.iloc[-1]; ult = df.index[-1]
    z=[];conf=[];fato=[];idx=[]
    bias=0
    if previsao is not None:
        devs=[previsao[m]-N[m.month] for m in MESES if m in previsao]
        bias=np.mean(devs) if devs else 0
    for k,m in enumerate(MESES):
        h = max(1,(m.year-ult.year)*12+m.month-ult.month)
        if previsao is not None and m in previsao:
            ae = previsao[m]-N[m.month]-bias; r2a = 0.5*0.6**k
        else:
            ae = last.an*(r**h); r2a = r**(2*h)
        numr = N[m.month]-media+ae
        zz = float(np.clip(numr/sdT,-3,3)) if sdT>0 else 0.0
        z.append(round(zz,4)); conf.append(round(r2s+(1-r2s)*r2a,4)); idx.append(round(100*(1+numr/media),2) if media else 100)
        mt = MESES_PT[m.month-1]
        if sig.startswith('Clima'):
            val=N[m.month]+ae
            if 'temp' in sig: f=f"{cap(NOME[sig])} esperada em {mt}: {num(val)} °C ({num(numr)} °C {'acima' if numr>=0 else 'abaixo'} da média do ano)"
            elif 'umidade' in sig: f=f"Umidade do ar esperada em {mt}: {val:.0f}% ({abs(numr):.0f} pontos {'acima' if numr>=0 else 'abaixo'} da média do ano)"
            else: f=f"Chuva esperada em {mt}: {val:.0f} mm ({pct(numr/media)} {'acima' if numr>=0 else 'abaixo'} da média do ano)"
        else:
            pt=numr/media; ps=(N[m.month]-media)/media; pa=ae/media
            esp='esperadas' if busca else 'esperados'
            f=cap(f"{NOME[sig]} {esp} em {mt}: {pct(pt)} {'acima' if pt>=0 else 'abaixo'} da média do ano (época do ano {'+' if ps>=0 else '-'}{pct(ps)}; situação atual {'+' if pa>=0 else '-'}{pct(pa)})")
        fato.append(f)
    hz=[];hi=[]
    for m in pd.date_range(MES0-pd.DateOffset(months=24),MES0-pd.DateOffset(months=1),freq='MS'):
        if m in df.index:
            row=df.loc[m]; hz.append(round(float(np.clip((row.v-row.aj-media)/sdT,-3,3)),4)); hi.append(round(100*(row.v-row.aj)/media,2))
        else: hz.append(0); hi.append(100)
    return {'disp':1,'z':z,'conf':conf,'fato':fato,'hist_z':hz,'hist_idx':hi,'prev_idx':idx}

def tipico(sig, rg):
    arr = np.array(DENG if sig=='Saúde: dengue' else NORM[sig][rg]); mu=arr.mean(); sd=arr.std()
    z=[];conf=[];fato=[];idx=[]
    for m in MESES:
        mi=m.month-1; d=arr[mi]-mu; z.append(round(float(np.clip(d/sd,-3,3)),4)); conf.append(0.4 if sig=='Saúde: dengue' else 0.6); idx.append(round(100*arr[mi]/mu,2))
        mt=MESES_PT[mi]
        if sig=='Saúde: dengue': fato.append(f"Casos de dengue costumam ficar {pct(d/mu)} {'acima' if d>=0 else 'abaixo'} da média do ano em {mt} (perfil típico)")
        elif 'temp' in sig: fato.append(f"{cap(NOME[sig])} típica de {mt}: {num(arr[mi])} °C ({num(d)} °C {'acima' if d>=0 else 'abaixo'} da média do ano)")
        elif 'umidade' in sig: fato.append(f"Umidade do ar típica de {mt}: {arr[mi]:.0f}% ({abs(d):.0f} pontos {'acima' if d>=0 else 'abaixo'} da média do ano)")
        else: fato.append(f"Chuva típica de {mt}: {arr[mi]:.0f} mm ({pct(d/mu)} {'acima' if d>=0 else 'abaixo'} da média do ano)")
    hz=[];hi=[]
    for m in pd.date_range(MES0-pd.DateOffset(months=24),MES0-pd.DateOffset(months=1),freq='MS'):
        hz.append(round(float(np.clip((arr[m.month-1]-mu)/sd,-3,3)),4)); hi.append(round(100*arr[m.month-1]/mu,2))
    return {'disp':1,'z':z,'conf':conf,'fato':fato,'hist_z':hz,'hist_idx':hi,'prev_idx':idx,'tipico':True}

def main():
    def seguro(f, padrao):
        try: return f()
        except Exception as e: print('Erro em', f.__name__, e); return padrao
    seguro(fonte_mapas, None); srag = fonte_srag(); trends = seguro(fonte_trends, {})
    clima_h, clima_p = seguro(fonte_clima, (None, None)); dengue = seguro(fonte_dengue, None)
    dados = {r:{} for r in REGS}
    for rg in REGS:
        for sig,_,_ in SINAIS:
            res=None
            try:
                if sig=='Saúde: SRAG': res=stats_serie(srag[srag.Regiao==rg][['Mes','Valor']], sig)
                elif sig=='Saúde: dengue': res=stats_serie(dengue[dengue.Regiao==rg][['Mes','Valor']], sig) if dengue is not None else None
                elif sig.startswith('Busca'):
                    t=trends.get(sig); res=stats_serie(t[t.Regiao==rg][['Mes','Valor']], sig) if t is not None and (t.Regiao==rg).any() else None
                elif clima_h is not None and sig in clima_h:
                    p=clima_p.get(sig) if clima_p else None
                    prev={m:v for m,v in p[p.Regiao==rg][['Mes','Valor']].itertuples(index=False)} if p is not None else None
                    res=stats_serie(clima_h[sig][clima_h[sig].Regiao==rg][['Mes','Valor']], sig, previsao=prev)
            except Exception as e:
                print('Falha em', rg, sig, e); res=None
            if res is None and (sig.startswith('Clima') or sig=='Saúde: dengue'): res=tipico(sig,rg)
            if res is None: res={'disp':0,'z':[0]*6,'conf':[0]*6,'fato':['']*6,'hist_z':[0]*24,'hist_idx':[100]*24,'prev_idx':[100]*6}
            dados[rg][sig]=res
    hist_meses=[m.strftime('%Y-%m') for m in pd.date_range(MES0-pd.DateOffset(months=24),MES0-pd.DateOffset(months=1),freq='MS')]+[m.strftime('%Y-%m') for m in MESES]
    nac={}
    for sig,_,_ in SINAIS:
        ws=[POPR[r]*dados[r][sig]['disp'] for r in REGS]; tot=sum(ws) or 1
        hz=[sum(w*dados[r][sig]['hist_z'][i] for w,r in zip(ws,REGS))/tot for i in range(24)]+[sum(w*dados[r][sig]['z'][i] for w,r in zip(ws,REGS))/tot for i in range(6)]
        hi=[sum(w*dados[r][sig]['hist_idx'][i] for w,r in zip(ws,REGS))/tot for i in range(24)]+[sum(w*dados[r][sig]['prev_idx'][i] for w,r in zip(ws,REGS))/tot for i in range(6)]
        nac[sig]={'z':[round(x,4) for x in hz],'idx':[round(x,2) for x in hi]}
    for r in REGS:
        for sig in dados[r]:
            for k in ('hist_z','hist_idx','prev_idx'): dados[r][sig].pop(k,None)
    out={'meta':{'gerado_em':dt.datetime.now().strftime('%d/%m/%Y %H:%M'),'mes_base':MES0.strftime('%Y-%m'),'fontes':STATUS},
         'regioes':REGS,'pop_regiao':POPR,'ufs_regiao':REG,
         'meses':[{'id':m.strftime('%Y-%m'),'rotulo':rot(m,k),'curto':MESES_PT[m.month-1][:3].capitalize()+'/'+str(m.year)[2:]} for k,m in enumerate(MESES)],
         'sinais':[{'id':s,'curto':c,'categoria':cat} for s,c,cat in SINAIS],
         'dados':dados,'historico':{'meses':hist_meses,'n_hist':24,'sinais':nac}}
    with open(os.path.join(RAIZ,'data','sinais.json'),'w',encoding='utf-8') as f: json.dump(out,f,ensure_ascii=False)
    print('OK sinais.json', json.dumps(STATUS, ensure_ascii=False))

if __name__=='__main__': main()
