"""Parity Capital lens: two-country hurdle rates with a Total Market benchmark."""
from dataclasses import asdict, replace
import json, os
import pandas as pd
import plotly.graph_objects as go
import pycountry
import streamlit as st
from finance import PairInputs, compare
from sources import snapshot, refresh, NAMES, CURRENCIES

st.set_page_config(page_title='Parity · Capital lens',page_icon='↗',layout='wide',initial_sidebar_state='collapsed')
st.markdown('''<style>
.block-container{padding-top:3.6rem;padding-bottom:2rem;max-width:1440px}
h1{font-size:1.95rem!important;letter-spacing:-.055rem;padding-top:0!important}
h2{font-size:1.2rem!important}h3{font-size:1rem!important}
[data-testid="stMetricValue"]{font-size:1.65rem}[data-testid="stVerticalBlock"]{gap:.65rem}
.eyebrow{color:#167565;letter-spacing:.15em;font-size:.7rem;font-weight:700}
.subline{color:#657984;font-size:.92rem;margin-bottom:.3rem}
@media(max-width:900px){.st-key-controls [data-testid="stHorizontalBlock"]{display:grid!important;grid-template-columns:1fr 1fr;gap:10px!important}.st-key-controls [data-testid="stColumn"]{width:100%!important;min-width:0!important}.st-key-controls [data-testid="stColumn"]:first-child{grid-column:1/-1}}
@media(max-width:760px){.block-container{padding:3.5rem 1rem 1rem}h1{font-size:1.5rem!important}
[data-testid="stMetricValue"]{font-size:1.35rem}.st-key-country1_card [data-testid="stHorizontalBlock"],.st-key-country2_card [data-testid="stHorizontalBlock"]{display:grid!important;grid-template-columns:1fr 1fr 1fr;gap:8px!important}.st-key-country1_card [data-testid="stColumn"],.st-key-country2_card [data-testid="stColumn"]{width:100%!important;min-width:0!important}}
</style>''',unsafe_allow_html=True)
st.markdown('<div class="eyebrow">PARITY / INTERNATIONAL FINANCE</div>',unsafe_allow_html=True)
heading,refresh_col=st.columns([5,1])
with heading:
    st.title('Capital lens')
    st.markdown('<div class="subline">Compare project hurdle rates across two currencies, with a Total Market benchmark.</div>',unsafe_allow_html=True)
@st.cache_data(ttl=3600,show_spinner=False)
def initial_data():
    return snapshot() if os.getenv('CAPITAL_OFFLINE')=='1' else refresh()
if 'source_data_v2' not in st.session_state:
    with st.spinner('Loading the latest available source data…'): st.session_state.source_data_v2=initial_data()
with refresh_col:
    if st.button('↻ Refresh data',width='stretch'):
        with st.spinner('Refreshing all four sources…'):
            st.session_state.source_data_v2=refresh(st.session_state.source_data_v2)
            initial_data.clear()
data=st.session_state.source_data_v2
betas={r['industry']:r['beta'] for r in data.get('betas',{}).get('rows',[])}
if not betas: st.error('Industry data unavailable. Refresh to continue.'); st.stop()
taxes={r['code']:r for r in data.get('taxes',{}).get('rows',[])}
yields={r['country']:r for r in data.get('yields',{}).get('rows',[])}
countries={c.alpha_3:NAMES.get(c.alpha_3,c.name) for c in pycountry.countries}
for code,row in taxes.items(): countries[code]=row['country']
codes=sorted(countries,key=countries.get)
industries=(['Total Market'] if 'Total Market' in betas else [])+sorted(i for i in betas if i!='Total Market')
with st.container(key='controls'):
    c0,c1,c2,c3,c4=st.columns([2.5,1.8,1.8,1.35,1.35])
    industry=c0.selectbox('Industry',industries,index=industries.index('Software (System & Application)'),key='industry')
    country1=c1.selectbox('Country 1',codes,index=codes.index('USA'),format_func=countries.get,key='country1')
    country2=c2.selectbox('Country 2',codes,index=codes.index('USA'),format_func=countries.get,key='country2')
    erp=c3.number_input('Equity risk premium (%)',0.0,100.0,6.5,.1,format='%.2f',key='erp')/100
    debt=c4.number_input('Debt financing (%)',0.0,99.9,30.0,1.0,format='%.1f',key='debt')/100
names=[countries[country1],countries[country2]]
currencies=[CURRENCIES.get(country1,'local currency'),CURRENCIES.get(country2,'local currency')]
tax_options=list(dict.fromkeys(['USA',country1,country2]))
mode=st.radio('Comparison method',['Class method','Project location'],horizontal=True,key='comparison_mode')
location=mode=='Project location'
if location:
    st.caption('Same project, two locations: each country’s tax rate affects its equity beta and interest tax shield. Industry risk, debt share, ERP and the USD borrowing benchmark stay the same.')
else:
    st.caption('One project, two currencies: the same project tax rate applies to both sides, following the class method.')
tax_code='USA' if location else st.radio('Project tax rate',tax_options,horizontal=True,format_func=countries.get,key='tax_country',help='One project tax rate applies to both currencies and the Total Market benchmark. This holds the project constant when comparing currency-denominated hurdle rates.')
tax_row=taxes.get(tax_code,{})
us_row=yields.get('United States',{})
yield_rows=[yields.get(name,{}) for name in names]

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

with st.expander('Source inputs & manual overrides'):
    st.caption('Annual rates; spreads are percentage points above government yields. USD remains the common reference for the class CAPM and BBB spread, even when neither selected country is the U.S.')
    a,b=st.columns(2)
    with a:
        beta,beta_manual=editable('Unlevered beta',betas[industry],'beta_'+industry,0,20,False)
        st.caption('Damodaran · '+data['betas']['as_of'])
        tax,tax_manual=None,False
        if not location:
            tax,tax_manual=editable('Corporate tax rate',tax_row.get('tax'),'tax_'+tax_code,0,100)
            st.caption(countries[tax_code]+' · OECD · '+tax_row.get('as_of','Unavailable'))
    with b:
        us,us_manual=editable('U.S. reference yield',us_row.get('yield'),'us_yield',-99,500)
        st.caption('Trading Economics · '+us_row.get('as_of','Unavailable'))
        spread,spread_manual=editable('USD BBB spread',data.get('spread',{}).get('value'),'spread',0,100)
        st.caption('Damodaran · large nonfinancial firms · '+data.get('spread',{}).get('as_of','Unavailable'))
    rates=[];spreads=[];rate_manual=[];spread_manuals=[];side_taxes=[];side_tax_manuals=[]
    for side,(col,code) in enumerate(zip(st.columns(2),[country1,country2]),1):
        with col:
            st.markdown(f'**Country {side} · {countries[code]}**')
            if location:
                row=taxes.get(code,{})
                side_tax,side_tax_manual=editable(f'Country {side} corporate tax rate',row.get('tax'),f'location_tax{side}_'+code,0,100)
                st.caption('OECD · '+row.get('as_of','Unavailable'))
            else:
                side_tax,side_tax_manual=tax,tax_manual
            side_taxes.append(side_tax);side_tax_manuals.append(side_tax_manual)
            if code=='USA':
                rate,manual=us,us_manual
                st.caption('Government yield uses the U.S. reference yield above.')
            else:
                rate,manual=editable(f'Country {side} 10-year yield',yield_rows[side-1].get('yield'),f'yield{side}_'+code,-99,500)
                st.caption('Trading Economics · '+yield_rows[side-1].get('as_of','Unavailable'))
            auto=None if any(v is None for v in [spread,us,rate]) else spread*(1+rate)/(1+us)
            effective,overridden=editable(f'Country {side} BBB spread',auto,f'spread{side}_'+code,0,500)
            st.caption('Automatic: USD spread × (1 + selected yield) / (1 + U.S. yield).')
            rates.append(rate);spreads.append(effective);rate_manual.append(manual);spread_manuals.append(overridden)
failures=[k for k,v in data.items() if v.get('error')]
if failures: st.warning('Refresh failed for '+', '.join(failures)+'. Saved observations retain their original dates; see Sources & dates.')
if any(v is None for v in [beta,*side_taxes,us,spread,*rates,*spreads]):
    st.info('Open Source inputs & manual overrides and enter missing values. No missing country yield or tax rate is estimated.')
    with st.expander('Sources & dates'):
        for k,v in data.items(): st.write(k,v.get('source'),v.get('status'),v.get('error',''))
    st.stop()
p=PairInputs(beta,side_taxes[0],debt,erp,us,*rates,spread,*[s if m else None for s,m in zip(spreads,spread_manuals)],tax1=side_taxes[0] if location else None,tax2=side_taxes[1] if location else None)
try: result=compare(p)
except ValueError as exc: st.error(str(exc)); st.stop()
market=compare(replace(p,beta_u=betas['Total Market'])) if 'Total Market' in betas else None
st.caption(f'{industry}  |  {mode}  |  Debt / equity: {result["debt_equity"]:.3f}')
for side,col in enumerate(st.columns(2),1):
    prefix=f'country{side}'
    with col:
        with st.container(border=True,key=prefix+'_card'):
            st.markdown(f'### {names[side-1]} · {currencies[side-1]}')
            st.caption(f'Tax: {side_taxes[side-1]:.2%}'+(' · manual' if side_tax_manuals[side-1] else '')+f' · Equity beta: {result[prefix+"_beta_e"]:.4f}')
            st.metric('Weighted average cost of capital',f'{result[prefix+"_wacc"]:.2%}')
            x,y,z=st.columns(3)
            x.metric('Cost of equity',f'{result[prefix+"_equity"]:.2%}')
            y.metric('Debt · before tax',f'{result[prefix+"_debt"]:.2%}')
            z.metric('Debt · after tax',f'{result[prefix+"_aftertax_debt"]:.2%}')
            if market:
                diff=100*(result[prefix+'_wacc']-market[prefix+'_wacc'])
                st.caption(f'Total Market WACC: {market[prefix+"_wacc"]:.2%} · Selected project: {diff:+.2f} pp vs benchmark')
if market:
    st.caption(f'Total Market uses Damodaran’s U.S. aggregate excluding financial firms (unlevered beta {betas["Total Market"]:.4f}). The benchmark uses each side’s effective tax, leverage, ERP, yield and spread; it retains the source beta even if you override the selected project’s beta.')
else: st.warning('Total Market source data are unavailable. Refresh to load the aggregate benchmark.')
gap=100*(result['country2_wacc']-result['country1_wacc'])
comparison='Both WACCs are equal.' if abs(gap)<1e-10 else f'Country 2’s nominal WACC is {abs(gap):.2f} percentage points '+('above' if gap>0 else 'below')+' Country 1’s.'
st.markdown('**Reading the comparison.** '+comparison+' These are project hurdle rates in each currency. Compare expected cash-flow returns with the matching rate; the nominal gap alone does not isolate the extra risk of locating the project in either country.')
if currencies[0]==currencies[1] and currencies[0]!='local currency' and abs(rates[0]-rates[1])>1e-12:
    st.warning('Both countries use the same currency, but their government yields differ. The model mechanically applies the yield inputs; this difference is not an exchange-rate conversion and may reflect sovereign or other yield premia.')
tab1,tab2,tab3=st.tabs(['Compare & download','How it works','Sources & dates'])
with tab1:
    fig=go.Figure()
    for side,color in [(1,'#167565'),(2,'#7764a5')]:
        xs=[industry+(' (override)' if beta_manual else '')];ys=[100*result[f'country{side}_wacc']]
        if market and (industry!='Total Market' or beta_manual): xs.append('Total Market');ys.append(100*market[f'country{side}_wacc'])
        fig.add_bar(name=f'Country {side} · {currencies[side-1]}',x=xs,y=ys,marker_color=color,hovertemplate='%{y:.2f}%<extra>%{fullData.name}</extra>')
    fig.update_layout(height=260,margin=dict(l=0,r=0,t=10,b=0),barmode='group',paper_bgcolor='white',plot_bgcolor='white',legend=dict(orientation='h',y=1.15),yaxis_title='Annual WACC (%)',font=dict(color='#172b39'))
    st.plotly_chart(fig,width='stretch')
    st.subheader('All-industry comparison')
    st.caption('Total Market appears first, followed by industries. Each row uses its source beta and the same project assumptions. A manual beta affects only the selected project above.')
    records=[]
    for ind in industries:
        calc=compare(replace(p,beta_u=betas[ind]))
        records.append({'Industry':ind,'Unlevered beta':betas[ind],**{f'Country {side} equity beta':calc[f'country{side}_beta_e'] for side in [1,2]},**{f'Country {side} {metric} (%)':100*calc[f'country{side}_{metric}'] for side in [1,2] for metric in ['equity','wacc']}})
    table=pd.DataFrame(records)
    st.dataframe(table,hide_index=True,width='stretch',height=330,column_config={c:st.column_config.NumberColumn(format='%.4f' if 'beta' in c.lower() else '%.2f') for c in table.columns if c!='Industry'})
    audit={'country1':names[0],'country2':names[1],'currency1':currencies[0],'currency2':currencies[1],'industry':industry,'comparison_mode':mode,'tax_jurisdiction':'Country-specific' if location else countries[tax_code],'country1_tax_jurisdiction':names[0] if location else countries[tax_code],'country2_tax_jurisdiction':names[1] if location else countries[tax_code],'country1_tax_manual':side_tax_manuals[0],'country2_tax_manual':side_tax_manuals[1],**asdict(p),**result,'beta_manual':beta_manual,'tax_manual':tax_manual,'us_yield_manual':us_manual,'usd_spread_manual':spread_manual,'country1_yield_manual':rate_manual[0],'country2_yield_manual':rate_manual[1],'country1_spread_manual':spread_manuals[0],'country2_spread_manual':spread_manuals[1]}
    if location:
        audit['tax']=None  # No shared project tax in this mode.
        audit['tax_manual']=None
    if market:
        audit.update(total_market_source_row='Total Market (without financials)',total_market_beta=betas['Total Market'],total_market_country1_wacc=market['country1_wacc'],total_market_country2_wacc=market['country2_wacc'])
    for k,v in data.items():
        for field in ['source','retrieved_at','status','as_of']: audit[k+'_'+field]=v.get(field)
    audit.update(us_yield_as_of=us_row.get('as_of'),country1_yield_as_of=yield_rows[0].get('as_of'),country2_yield_as_of=yield_rows[1].get('as_of'),tax_as_of=None if location else tax_row.get('as_of'),country1_tax_as_of=(taxes.get(country1,{}) if location else tax_row).get('as_of'),country2_tax_as_of=(taxes.get(country2,{}) if location else tax_row).get('as_of'))
    # Shared assumptions and provenance accompany every industry row.
    shared={k:v for k,v in audit.items() if k not in ['industry','beta_u','beta_e','beta_manual'] and not k.endswith(('_equity','_debt','_wacc','_beta_e'))}
    export=pd.concat([table,pd.DataFrame([shared]*len(table))],axis=1)
    a,b,c=st.columns(3)
    a.download_button('Download project CSV',pd.DataFrame([audit]).to_csv(index=False).encode(),'capital-project.csv','text/csv',width='stretch')
    b.download_button('Download all industries',export.to_csv(index=False).encode(),'capital-all-industries.csv','text/csv',width='stretch')
    c.download_button('Download full audit (JSON)',json.dumps({'project':audit,'total_market':market,'sources':data},indent=2).encode(),'capital-audit.json','application/json',width='stretch')
    st.caption('Project CSV rates are decimals (0.065 = 6.5%). Industry result columns marked (%) are percentages. All exports retain calculation precision.')
with tab2:
    st.markdown('''**What the rates mean.** WACC is the required return, or opportunity cost, for project cash flows. The class example is a Colombian project valued in USD and COP, with the same 35% project tax in both financing scenarios (slides 578–585). A country selector supplies a government-yield proxy and currency; it does not automatically change the project’s location, cash flows or operating risk.

**Choose the comparison.** Class method applies one chosen project tax to both currencies. Project location applies each selected country’s OECD statutory tax (or its manual override) to its own equity beta and interest tax shield. Industry beta, debt share, ERP and USD borrowing benchmark remain common. The USD equity reference is recalculated for each location’s relevered beta.

**1 · Relever project risk.** D/E = d / (1 − d). Equity beta βE = βU × [1 + (1 − τ) × D/E].

**2 · Establish the common USD reference.** Re USD = Rf USD + βE × ERP. Rd USD = Rf USD + s USD. U.S. industry betas and the USD BBB spread remain the reference when comparing any two countries.

**3 · Convert independently to each selected currency.** For country i, Fi = (1 + Rf i) / (1 + Rf USD). Re i = (1 + Re USD) × Fi − 1. Automatic spread si = s USD × Fi. Rd i = Rf i + si. Each country’s spread override affects only that country’s debt cost and WACC. A selected U.S. yield shares the USD reference input.

**4 · Calculate WACC in each currency.** WACC i = (1 − d) × Re i + d × Rd i × (1 − τ). Use the shared project tax in Class method, or the respective country tax in Project location. Both sides share debt share and ERP. Total Market follows the active mode and each side’s tax. The tax shield is computed in each financing currency.

**Currency differences and country risk.** Slides 564–571 derive the currency factor from equal real rates, the Fisher equation and relative PPP: the adjustment captures expected currency depreciation. Slides 580 and 587 explicitly add no separate country equity-risk premium. Slide 575 shows that actual government yields also contain real-yield and sovereign-credit differences. The app uses these yields as the class’s proxies; it cannot separate those components or attribute the entire WACC gap to country risk.

**Comparing investment locations.** Use these hurdle rates with cash flows in the matching currency. A location decision also needs location-specific revenues, costs, taxes and operating risks. The class discusses infrastructure, institutions and political risk in slides 548–563. Project location adds country-specific taxes to this controlled comparison; it does not estimate different cash flows, operating risks or country equity premia. Compare after-tax cash flows against their matching currency WACC. A lower nominal WACC alone does not establish a better investment.

**Total Market.** The label uses Damodaran’s source row “Total Market (without financials)” and its unlevered beta. This is the publisher’s aggregate, not an equal-weighted average of industry betas or a beta assumed to equal one. Excluding financials aligns the benchmark with the class’s nonfinancial BBB spread. The resulting WACC is a broad business-risk benchmark under your selected financing assumptions, not a country-specific stock-market expected return.

**Other assumptions.** Debt beta is zero; interest deductions are fully and immediately usable; target leverage is held fixed. OECD combined statutory tax rates can differ from a project’s effective rate. No extra country equity premium or estimated country cash-flow forecast is added.

**Class check.** βU 0.80; tax 35%; debt 30%; ERP 6.5%; yields 4% USD / 12% COP; USD spread 1.5%: USD WACC **8.5265%**, COP WACC **16.0670%**. Source: Sergio Rebelo, CasePacket2026-part9, slides 564–587.''')
    for side in [1,2]:
        st.caption(f'Country {side}: USD equity reference {result[f"country{side}_usd_reference_equity"]:.2%} · currency factor {result[f"country{side}_factor"]:.6f}.')
with tab3:
    st.caption('Initial load attempts all sources (one-hour cache). Refresh retries all four. Failed sources retain their last successful values and timestamps. Observation dates differ from retrieval dates.')
    for k,v in data.items():
        st.markdown(f'**{k.title()}** · [{v.get("source","")}]({v.get("source","")})')
        st.caption(f'{v.get("status")} | Observation: {v.get("as_of")} | Retrieved (UTC): {v.get("retrieved_at")}')
        if v.get('error'): st.warning(v['error'])
    st.markdown('Trading Economics’ public country-list table supplies 10-year government yields; month-only references are retained without inventing a day. OECD’s current database supplies each country’s latest available combined statutory tax rate. Total Market uses the exact nonfinancial aggregate row in Damodaran’s U.S. workbook.')
    observations=[{'Input':'USD reference yield','Observation':us_row.get('as_of'),'Value':f'{us:.4%}','Manual':us_manual}]
    observations += [{'Input':f'Country {i+1} tax · '+(names[i] if location else countries[tax_code]),'Observation':(taxes.get(code,{}) if location else tax_row).get('as_of'),'Value':f'{side_taxes[i]:.4%}','Manual':side_tax_manuals[i]} for i,code in enumerate([country1,country2])]
    observations += [{'Input':f'Country {i+1} yield · '+names[i],'Observation':yield_rows[i].get('as_of'),'Value':f'{rates[i]:.4%}','Manual':rate_manual[i]} for i in range(2)]
    st.dataframe(pd.DataFrame(observations),hide_index=True,width='stretch')
