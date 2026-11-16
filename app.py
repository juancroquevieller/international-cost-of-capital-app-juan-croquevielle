"""Parity · Capital lens — class-consistent international cost of capital."""
from dataclasses import asdict, replace
import json
import os
import pandas as pd
import plotly.graph_objects as go
import pycountry
import streamlit as st
from finance import Inputs, calculate
from sources import snapshot, refresh, NAMES, CURRENCIES

st.set_page_config(page_title='Parity · Capital lens',page_icon='↗',layout='wide',initial_sidebar_state='collapsed')
st.markdown('''<style>
.block-container{padding-top:3.6rem;padding-bottom:2rem;max-width:1440px}
h1{font-size:1.95rem!important;letter-spacing:-.055rem;padding-top:0!important}
h2{font-size:1.2rem!important}h3{font-size:1rem!important}
[data-testid="stMetricValue"]{font-size:1.65rem}[data-testid="stVerticalBlock"]{gap:.65rem}
.eyebrow{color:#167565;letter-spacing:.15em;font-size:.7rem;font-weight:700}
.subline{color:#657984;font-size:.92rem;margin-bottom:.3rem}
@media(max-width:760px){.block-container{padding:3.5rem 1rem 1rem}h1{font-size:1.5rem!important}
[data-testid="stMetricValue"]{font-size:1.35rem}.st-key-controls [data-testid="stHorizontalBlock"]{display:grid!important;grid-template-columns:1fr 1fr;gap:10px!important}.st-key-controls [data-testid="stColumn"]{width:100%!important;min-width:0!important}.st-key-controls [data-testid="stColumn"]:nth-child(-n+2){grid-column:1/-1}.st-key-usd_card [data-testid="stHorizontalBlock"],.st-key-foreign_card [data-testid="stHorizontalBlock"]{display:grid!important;grid-template-columns:1fr 1fr 1fr;gap:8px!important}.st-key-usd_card [data-testid="stColumn"],.st-key-foreign_card [data-testid="stColumn"]{width:100%!important;min-width:0!important}}
</style>''',unsafe_allow_html=True)
st.markdown('<div class="eyebrow">PARITY / INTERNATIONAL FINANCE</div>',unsafe_allow_html=True)
heading, refresh_col=st.columns([5,1])
with heading:
    st.title('Capital lens')
    st.markdown('<div class="subline">One project. Two currencies. Compare the cost of equity, debt and capital.</div>',unsafe_allow_html=True)
@st.cache_data(ttl=3600,show_spinner=False)
def initial_data():
    if os.getenv('CAPITAL_OFFLINE')=='1': return snapshot()
    return refresh()
if 'source_data' not in st.session_state:
    with st.spinner('Loading the latest available source data…'):
        st.session_state.source_data=initial_data()
with refresh_col:
    if st.button('↻ Refresh data',width='stretch'):
        with st.spinner('Refreshing all four sources…'):
            st.session_state.source_data=refresh(st.session_state.source_data)
            initial_data.clear()
data=st.session_state.source_data
betas={r['industry']:r['beta'] for r in data.get('betas',{}).get('rows',[])}
if not betas:
    st.error('Industry data are unavailable. Refresh the sources to continue.'); st.stop()
taxes={r['code']:r for r in data.get('taxes',{}).get('rows',[])}
yields={r['country']:r for r in data.get('yields',{}).get('rows',[])}
countries={c.alpha_3:NAMES.get(c.alpha_3,c.name) for c in pycountry.countries}
for code,r in taxes.items(): countries[code]=r['country']
codes=sorted(countries,key=countries.get)
with st.container(key='controls'):
    c1,c2,c3,c4=st.columns([2.7,2,1.3,1.3])
    industry=c1.selectbox('Industry',sorted(betas),index=sorted(betas).index('Software (System & Application)'))
    country=c2.selectbox('Target country',codes,index=codes.index('USA'),format_func=countries.get)
    erp=c3.number_input('Equity risk premium (%)',0.0,100.0,6.5,.1,format='%.2f')/100
    debt=c4.number_input('Debt financing (%)',0.0,99.9,30.0,1.0,format='%.1f')/100
name=countries[country]
cur=CURRENCIES.get(country,'local currency')
tax_choice=st.radio('Project tax rate', ['United States','Selected country'],horizontal=True,help='The chosen project tax rate applies to both currencies, including relevering beta and the debt tax shield.')
tax_code='USA' if tax_choice=='United States' else country
tax_row=taxes.get(tax_code,{})
us_row=yields.get('United States',{})
foreign_row=yields.get(name,{})

# Keys are scoped to the selected country / industry, so overrides do not leak to other projects.
def editable(label,value,key,low,high,percent=True):
    enabled=st.toggle('Override '+label,key='on_'+key)
    if enabled:
        default=0.0 if value is None else value*(100 if percent else 1)
        result=st.number_input(label+(' (%)' if percent else ''),min_value=float(low),max_value=float(high),value=float(default),step=.01,format='%.4f',key='value_'+key)
        return result/(100 if percent else 1),True
    if value is None:
        st.caption(label+': unavailable — enable override to enter a value.')
        return None,False
    st.markdown(f'**{label}: {value:.2%}**' if percent else f'**{label}: {value:.4f}**')
    return value,False

with st.expander('Source inputs & manual overrides',expanded=False):
    st.caption('Rates are annual. Spreads are percentage points above government yields. Overrides affect this project only; turning one off restores the source value.')
    a,b,c=st.columns(3)
    with a:
        beta,beta_manual=editable('Unlevered beta',betas[industry],'beta_'+industry,0,20,False)
        st.caption('Damodaran · '+data['betas']['as_of'])
        tax,tax_manual=editable('Corporate tax rate',tax_row.get('tax'),'tax_'+tax_code,0,100)
        st.caption(countries[tax_code]+' · OECD combined statutory rate · '+tax_row.get('as_of','Unavailable'))
    with b:
        us,us_manual=editable('U.S. 10-year yield',us_row.get('yield'),'us_yield',-99,500)
        st.caption('Trading Economics · '+us_row.get('as_of','Unavailable'))
        foreign,foreign_manual=editable('Selected-country 10-year yield',foreign_row.get('yield'),'yield_'+country,-99,500)
        st.caption(name+' · Trading Economics · '+foreign_row.get('as_of','Unavailable'))
    with c:
        spread,spread_manual=editable('USD BBB spread',data.get('spread',{}).get('value'),'spread',0,100)
        st.caption('Damodaran · large nonfinancial firms · '+data.get('spread',{}).get('as_of','Unavailable'))
        auto=None if any(x is None for x in [spread,us,foreign]) else spread*(1+foreign)/(1+us)
        foreign_spread,foreign_spread_manual=editable('Foreign BBB spread',auto,'foreign_spread_'+country,0,500)
        st.caption('Automatic: USD spread × (1 + foreign yield) / (1 + U.S. yield).')

failures=[k for k,v in data.items() if v.get('error')]
if failures: st.warning('Refresh unavailable for '+', '.join(failures)+'. Saved observations are used where available. See Sources & dates for details.')
if any(x is None for x in [beta,tax,us,foreign,spread,foreign_spread]):
    st.info('Open Source inputs & manual overrides and enter the missing values to calculate this country. No country yield or tax rate is invented.')
    with st.expander('Sources & dates'):
        for k,v in data.items(): st.write(k,v.get('source'),v.get('status'),v.get('error',''))
    st.stop()
p=Inputs(beta,tax,debt,erp,us,foreign,spread,foreign_spread if foreign_spread_manual else None)
try: result=calculate(p)
except ValueError as exc: st.error(str(exc)); st.stop()
st.caption(f'{name} · {industry}  |  Project tax: {tax:.2%} ({countries[tax_code]}'+(' · manual' if tax_manual else '')+f')  |  Relevered beta: {result["beta_e"]:.4f}  |  Debt / equity: {result["debt_equity"]:.3f}')
left,right=st.columns(2)
for col,prefix,title in [(left,'usd','U.S. dollars · USD'),(right,'foreign',name+' · '+cur)]:
    with col:
        with st.container(border=True,key=prefix+'_card'):
            st.markdown('### '+title)
            st.metric('Weighted average cost of capital',f'{result[prefix+"_wacc"]:.2%}')
            x,y,z=st.columns(3)
            x.metric('Cost of equity',f'{result[prefix+"_equity"]:.2%}')
            y.metric('Debt · before tax',f'{result[prefix+"_debt"]:.2%}')
            z.metric('Debt · after tax',f'{result[prefix+"_aftertax_debt"]:.2%}')
gap=(result['foreign_wacc']-result['usd_wacc'])*100
comparison = 'Both WACCs are equal.' if abs(gap)<1e-10 else f'The selected-country WACC is {abs(gap):.2f} percentage points '+('above' if gap>0 else 'below')+' the USD WACC.'
st.markdown('**Reading the comparison.** '+comparison+' Match each discount rate to cash flows in that currency; a lower nominal rate alone does not imply cheaper financing.')
if country=='USA' and abs(us-foreign)<1e-12 and not foreign_spread_manual:
    st.caption('U.S.–U.S. check: both columns coincide because government yields and all shared assumptions are equal.')
if CURRENCIES.get(country)=='USD' and abs(us-foreign)>1e-12:
    st.warning('Both columns use USD, but the government-yield inputs differ. This is a yield scenario, not a conversion between distinct currencies.')
tab1,tab2,tab3=st.tabs(['Compare & download','How it works','Sources & dates'])
with tab1:
    fig=go.Figure()
    for prefix,title,color in [('usd','USD','#167565'),('foreign',cur+' / '+name,'#7764a5')]:
        fig.add_bar(name=title,x=['Equity contribution','After-tax debt contribution'],y=[(1-debt)*result[prefix+'_equity']*100,debt*result[prefix+'_aftertax_debt']*100],marker_color=color,hovertemplate='%{y:.2f} pp<extra>%{fullData.name}</extra>')
    fig.update_layout(height=260,margin=dict(l=0,r=0,t=10,b=0),barmode='group',paper_bgcolor='white',plot_bgcolor='white',legend=dict(orientation='h',y=1.15),yaxis_title='Contribution to WACC (percentage points)',font=dict(color='#172b39'))
    st.plotly_chart(fig,width='stretch')
    st.subheader('All-industry comparison')
    st.caption('Same country, tax, debt share, ERP, yields and spreads. Each row uses its fetched industry beta; a manual beta affects only the selected-project results above.')
    records=[]
    for ind,b in sorted(betas.items()):
        calc=calculate(replace(p,beta_u=b))
        records.append({'Industry':ind,'Unlevered beta':b,'Equity beta':calc['beta_e'],'USD equity (%)':100*calc['usd_equity'],'Foreign equity (%)':100*calc['foreign_equity'],'USD WACC (%)':100*calc['usd_wacc'],'Foreign WACC (%)':100*calc['foreign_wacc']})
    table=pd.DataFrame(records)
    st.dataframe(table,hide_index=True,width='stretch',height=330,column_config={c:st.column_config.NumberColumn(format='%.2f') for c in table.columns if c!='Industry'})
    audit={'country':name,'currency':cur,'industry':industry,'tax_jurisdiction':countries[tax_code],**asdict(p),**result,'beta_manual':beta_manual,'tax_manual':tax_manual,'us_yield_manual':us_manual,'foreign_yield_manual':foreign_manual,'usd_spread_manual':spread_manual,'foreign_spread_manual':foreign_spread_manual}
    source_rows=[]
    for k,v in data.items():
        audit[k+'_source']=v.get('source'); audit[k+'_retrieved_at']=v.get('retrieved_at'); audit[k+'_status']=v.get('status'); audit[k+'_as_of']=v.get('as_of')
    audit.update(us_yield_as_of=us_row.get('as_of'),foreign_yield_as_of=foreign_row.get('as_of'),tax_as_of=tax_row.get('as_of'))
    a,b,c=st.columns(3)
    a.download_button('Download project CSV',pd.DataFrame([audit]).to_csv(index=False).encode(),'capital-project.csv','text/csv',width='stretch')
    # Repeat shared inputs in the industry export so it remains independently reproducible.
    export=table.assign(country=name,currency=cur,tax=p.tax,debt_share=p.debt_share,erp=p.erp,us_yield=p.us_yield,foreign_yield=p.foreign_yield,usd_spread=p.usd_spread,foreign_spread=result['effective_foreign_spread'])
    for k,v in data.items():
        for field in ['retrieved_at','as_of','source','status']: export[k+'_'+field]=v.get(field)
    export['tax_observation_year']=tax_row.get('as_of')
    export['us_yield_observation']=us_row.get('as_of')
    export['foreign_yield_observation']=foreign_row.get('as_of')
    b.download_button('Download all industries',export.to_csv(index=False).encode(),'capital-all-industries.csv','text/csv',width='stretch')
    c.download_button('Download full audit (JSON)',json.dumps({'project':audit,'sources':data},indent=2).encode(),'capital-audit.json','application/json',width='stretch')
    st.caption('CSV project rates are decimals (0.065 = 6.5%); industry result columns marked (%) are percentages. Exports retain full precision.')
with tab2:
    st.markdown('''**1 · Relever business risk.** Use target market-value debt share d to obtain D/E = d / (1 − d). The project equity beta is βE = βU × [1 + (1 − τ) × D/E].

**2 · Price USD financing.** Cost of equity Re = Rf + βE × ERP. Pretax debt cost Rd = Rf + s, where s is the USD BBB spread for large nonfinancial firms.

**3 · Convert the currency.** F = (1 + Rf foreign) / (1 + Rf USD). Foreign equity cost = (1 + Re USD) × F − 1. Automatic foreign spread = s USD × F. Foreign debt cost = foreign government yield + foreign spread. A foreign-spread override changes only foreign debt and WACC.

**4 · Weight each currency separately.** WACC = (1 − d) × Re + d × Rd × (1 − τ). The same project tax, debt share and ERP apply to both columns. Do not simply convert the USD WACC as a gross rate: the tax shield is calculated in each currency.

**Assumptions to keep in view.** U.S. industry betas proxy for project operating risk; debt beta is zero. Government yields are risk-free proxies even though they can contain sovereign credit, liquidity and term premia. The conversion assumes equal real rates and relative purchasing power parity. No extra country equity-risk premium is added. Interest deductions are fully and immediately usable. OECD rates are combined central/subcentral headline rates; the effective tax rate of a specific project may differ.

**Class reference.** Sergio Rebelo, *CasePacket2026-part9*, slides 564–587. The Colombia example (βU 0.80; tax 35%; debt 30%; ERP 6.5%; yields 4% / 12%; USD spread 1.5%) yields USD WACC **8.5265%** and COP WACC **16.0670%**.''')
    st.caption(f'Current conversion factor: {result["conversion_factor"]:.6f} · Automatic foreign spread: {result["auto_foreign_spread"]*10000:,.2f} basis points.')
with tab3:
    st.caption('The app attempts a live fetch on initial load (cached for one hour). Refresh retries every source. A failed source retains its last successful data and original retrieval timestamp. Observation dates and retrieval dates are different.')
    for k,v in data.items():
        st.markdown(f'**{k.title()}** · [{v.get("source","")}]({v.get("source","")})')
        st.caption(f'{v.get("status")} | Observation: {v.get("as_of")} | Retrieved (UTC): {v.get("retrieved_at")}')
        if v.get('error'): st.warning(v['error'])
    st.markdown('Trading Economics’ main bonds page loads dynamically; the app reads its public country-list table of the same 10-year government-bond indicator. That table may expose only a month reference, which is retained without inventing a day. Tax data use OECD’s current database rather than freezing the assignment’s 2024 report.')
    st.dataframe(pd.DataFrame([{'Input':'U.S. yield','Observation date':us_row.get('as_of'),'Value':f'{us:.4%}','Manual':us_manual},{'Input':name+' yield','Observation date':foreign_row.get('as_of'),'Value':f'{foreign:.4%}','Manual':foreign_manual},{'Input':'Project tax','Observation date':tax_row.get('as_of'),'Value':f'{tax:.4%}','Manual':tax_manual}]),hide_index=True,width='stretch')



