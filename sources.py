from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
import io, json, re
import pandas as pd
import requests
from bs4 import BeautifulSoup

ROOT=Path(__file__).parent
URLS={
 'betas':'https://pages.stern.nyu.edu/~adamodar/pc/datasets/betas.xls',
 'spread':'https://pages.stern.nyu.edu/adamodar/New_Home_Page/datafile/ratings.html',
 'taxes':'https://sdmx.oecd.org/public/rest/v1/data/OECD.CTP.TPS,DSD_TAX_CIT@DF_CIT,2.0/.A.CIT_C.ST..S13...?format=csvfile',
 'yields':'https://tradingeconomics.com/country-list/government-bond-10y'}
NAMES={'USA':'United States','GBR':'United Kingdom','KOR':'South Korea','CZE':'Czech Republic','SVK':'Slovakia','TUR':'Turkey','RUS':'Russia','VNM':'Vietnam','CHN':'China','HKG':'Hong Kong','TWN':'Taiwan','LAO':'Laos','IRN':'Iran','VEN':'Venezuela','BOL':'Bolivia','TZA':'Tanzania','COD':'Congo DR'}
CURRENCIES=dict(USA='USD',GBR='GBP',COL='COP',CHL='CLP',BRA='BRL',MEX='MXN',PER='PEN',ARG='ARS',CAN='CAD',AUS='AUD',NZL='NZD',JPN='JPY',CHN='CNY',IND='INR',CHE='CHF',SWE='SEK',NOR='NOK',DNK='DKK',POL='PLN',CZE='CZK',HUN='HUF',ROU='RON',TUR='TRY',ZAF='ZAR',KOR='KRW',SGP='SGD',HKG='HKD',IDN='IDR',MYS='MYR',THA='THB',PHL='PHP',ISR='ILS',ISL='ISK',RUS='RUB',PAK='PKR',KEN='KES',NGA='NGN',EGY='EGP',UKR='UAH',SAU='SAR',ARE='AED',QAT='QAR',BHR='BHD',KWT='KWD',OMN='OMR',MAR='MAD',TUN='TND',LKA='LKR',BGD='BDT',VNM='VND',TWN='TWD',CRI='CRC',URY='UYU',PRY='PYG')
CURRENCIES.update({c:'EUR' for c in 'AUT BEL CYP DEU ESP EST FIN FRA GRC HRV IRL ITA LTU LUX LVA MLT NLD PRT SVK SVN BGR'.split()})

def get(url):
    r=requests.get(url,headers={'User-Agent':'Mozilla/5.0'},timeout=(8,35))
    r.raise_for_status()
    return r

def parse_betas(content):
    raw=pd.read_excel(io.BytesIO(content),sheet_name='Industry Averages',header=None)
    header=next(i for i,row in raw.iterrows() if str(row.iloc[0]).strip()=='Industry Name')
    frame=raw.iloc[header+1:].copy()
    frame.columns=[str(x).strip() for x in raw.iloc[header]]
    beta=pd.to_numeric(frame['Unlevered beta'],errors='coerce') if 'Unlevered beta' in frame else pd.to_numeric(frame['Unlevered Beta'],errors='coerce')
    rows=[{'industry':str(n).strip(),'beta':float(b)} for n,b in zip(frame['Industry Name'],beta) if pd.notna(b) and b>=0 and not str(n).lower().startswith('total market')]
    if len(rows)<20 or not any(x['industry']=='Software (System & Application)' for x in rows):
        raise ValueError('Industry table did not pass schema checks.')
    return {'rows':rows,'as_of':str(raw.iloc[0,1])[:10]}

def parse_spread(html):
    soup=BeautifulSoup(html,'html.parser')
    text=soup.get_text(' ',strip=True)
    date=re.search(r'Data used is as of\s+([A-Za-z]+\s+\d{4})',text)
    # Each row contains the large-nonfinancial table first, then financial firms.
    for tr in soup.select('tr'):
        cells=[x.get_text(' ',strip=True) for x in tr.find_all('td',recursive=False)]
        for i,cell in enumerate(cells):
            if cell.replace(' ','')=='Baa2/BBB' and i+1<len(cells):
                match=re.fullmatch(r'([\d.]+)\s*%',cells[i+1])
                if match:
                    return {'value':float(match[1])/100,'as_of':date[1] if date else 'Not stated'}
    raise ValueError('Baa2/BBB large-nonfinancial spread not found.')

def parse_taxes(text):
    import pycountry
    frame=pd.read_csv(io.StringIO(text))
    for col,val in [('MEASURE','CIT_C'),('TARGETING','ST'),('SECTOR','S13'),('UNIT_MEASURE','PT_INC_TAX')]:
        frame=frame.loc[frame[col]==val]
    for col in ['DIV_TREATMENT','RATE_STRUCTURE','TAX_BASE']:
        frame=frame.loc[frame[col]=='_Z']
    frame['OBS_VALUE']=pd.to_numeric(frame.OBS_VALUE,errors='coerce')
    frame['TIME_PERIOD']=pd.to_numeric(frame.TIME_PERIOD,errors='coerce')
    frame=frame.dropna(subset=['OBS_VALUE','TIME_PERIOD'])
    frame=frame.loc[frame.TIME_PERIOD<=datetime.now(timezone.utc).year]
    latest=frame.sort_values('TIME_PERIOD').groupby('REF_AREA').tail(1)
    rows=[]
    for _,r in latest.iterrows():
        country=pycountry.countries.get(alpha_3=r.REF_AREA)
        if country and 0<=r.OBS_VALUE<=100:
            rows.append({'code':r.REF_AREA,'country':NAMES.get(r.REF_AREA,country.name),'tax':float(r.OBS_VALUE)/100,'as_of':str(int(r.TIME_PERIOD)),'currency':CURRENCIES.get(r.REF_AREA,'local currency')})
    if not any(r['code']=='USA' for r in rows): raise ValueError('OECD U.S. combined tax rate missing.')
    return {'rows':rows,'as_of':'Latest available year for each country'}

def parse_yields(html):
    soup=BeautifulSoup(html,'html.parser')
    rows=[]
    for tr in soup.select('tr'):
        a=tr.select_one('a[href*="government-bond-yield"]')
        cells=[c.get_text(' ',strip=True) for c in tr.find_all('td',recursive=False)]
        if a and len(cells)>=5 and cells[4]=='%':
            try: value=float(cells[1].replace(',',''))/100
            except ValueError: continue
            if not -1<value<5: continue
            rows.append({'country':a.get_text(' ',strip=True),'yield':value,'as_of':cells[3], 'url':'https://tradingeconomics.com'+a['href']})
    if not any(x['country']=='United States' for x in rows): raise ValueError('Trading Economics U.S. 10-year yield missing.')
    return {'rows':rows,'as_of':'Reference period shown per country (source may report month only)'}

def fetch_one(name):
    response=get(URLS[name])
    parser={'betas':parse_betas,'spread':parse_spread,'taxes':parse_taxes,'yields':parse_yields}[name]
    result=parser(response.content if name=='betas' else response.text)
    result.update(source=URLS[name],retrieved_at=datetime.now(timezone.utc).isoformat(),status='Live fetch')
    return result

def snapshot():
    path=ROOT/'data'/'snapshot.json'
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}

def refresh(previous=None):
    result=dict(previous or snapshot())
    def work(name):
        try: return name,fetch_one(name),None
        except Exception as exc: return name,None,f'{type(exc).__name__}: {str(exc)[:180]}'
    with ThreadPoolExecutor(max_workers=4) as pool:
        for name,value,error in pool.map(work,URLS):
            if value is not None: result[name]=value
            elif name in result: result[name]={**result[name],'status':'Saved data · refresh failed','error':error}
            else: result[name]={'rows':[],'status':'Unavailable','error':error,'source':URLS[name],'as_of':'Unavailable','retrieved_at':'Never'}
    return result

if __name__=='__main__':
    result=refresh()
    print(json.dumps({k:{x:v.get(x) for x in ['status','as_of','error']} for k,v in result.items()},indent=2))
    if any(v['status']!='Live fetch' for v in result.values()): raise SystemExit('Snapshot not replaced: one or more sources failed.')
    (ROOT/'data').mkdir(exist_ok=True)
    (ROOT/'data'/'snapshot.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
