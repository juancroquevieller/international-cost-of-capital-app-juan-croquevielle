import os
os.environ['CAPITAL_OFFLINE']='1'
import unittest
from dataclasses import replace
from decimal import Decimal, getcontext
from unittest.mock import patch
from finance import Inputs, calculate
from sources import snapshot, refresh, parse_yields, parse_spread
from streamlit.testing.v1 import AppTest

class FinanceTests(unittest.TestCase):
    def setUp(self): self.p=Inputs(.8,.35,.3,.065,.04,.12,.015)
    def test_class_example(self):
        r=calculate(self.p)
        for key,expected in dict(beta_e=1.0228571428571429,usd_equity=.1064857142857143,foreign_equity=.1916,usd_debt=.055,foreign_debt=.13615384615384615,usd_wacc=.085265,foreign_wacc=.16067).items(): self.assertAlmostEqual(r[key],expected,12)
    def test_independent_decimal(self):
        getcontext().prec=40
        D=Decimal
        beta=D('.8')*(1+(1-D('.35'))*D('.3')/D('.7'))
        re=D('.04')+beta*D('.065')
        rd=D('.04')+D('.015')
        factor=D('1.12')/D('1.04')
        foreign_re=(1+re)*factor-1
        foreign_rd=D('.12')+D('.015')*factor
        self.assertLess(abs(D('.7')*re+D('.3')*rd*D('.65')-D('.085265')),D('1e-35'))
        self.assertAlmostEqual(float(D('.7')*foreign_re+D('.3')*foreign_rd*D('.65')),.16067,14)
    def test_equal_yields(self):
        r=calculate(replace(self.p,foreign_yield=.04))
        for key in ['equity','debt','aftertax_debt','wacc']: self.assertAlmostEqual(r['usd_'+key],r['foreign_'+key],14)
    def test_zero_debt(self):
        r=calculate(replace(self.p,debt_share=0))
        for prefix in ['usd','foreign']: self.assertEqual(r[prefix+'_wacc'],r[prefix+'_equity'])
    def test_override_isolation(self):
        a,b=calculate(self.p),calculate(replace(self.p,foreign_spread=.04))
        for key in a:
            if key.startswith('usd_') or key=='foreign_equity': self.assertEqual(a[key],b[key])
        self.assertNotEqual(a['foreign_wacc'],b['foreign_wacc'])
    def test_invalid_inputs(self):
        for kwargs in [dict(debt_share=1),dict(tax=-.01),dict(us_yield=-1),dict(beta_u=float('nan')),dict(foreign_spread=-.1)]:
            with self.assertRaises(ValueError): calculate(replace(self.p,**kwargs))
    def test_negative_yield_valid(self): self.assertTrue(calculate(replace(self.p,foreign_yield=-.01)))
    def test_refresh_preserves_dates(self):
        old=snapshot()
        with patch('sources.fetch_one',side_effect=ValueError('offline')): new=refresh(old)
        for key in old:
            self.assertEqual(old[key]['retrieved_at'],new[key]['retrieved_at'])
            self.assertIn('refresh failed',new[key]['status'])
    def test_schema_rejection(self):
        for parser in [parse_yields,parse_spread]:
            with self.assertRaises(ValueError): parser('<html>Loading...</html>')


from finance import PairInputs, compare

class PairTests(unittest.TestCase):
    def setUp(self): self.p=PairInputs(.8,.35,.3,.065,.04,.04,.12,.015)
    def test_original_class_example(self):
        r=compare(self.p)
        self.assertAlmostEqual(r['country1_wacc'],.085265,12)
        self.assertAlmostEqual(r['country2_wacc'],.16067,12)
    def test_swap_symmetry(self):
        p=replace(self.p,yield1=.06,yield2=.12,spread1=.02,spread2=.03)
        a=compare(p);b=compare(replace(p,yield1=p.yield2,yield2=p.yield1,spread1=p.spread2,spread2=p.spread1))
        for key in ['equity','debt','aftertax_debt','wacc','factor','spread']:
            self.assertEqual(a['country1_'+key],b['country2_'+key])
            self.assertEqual(a['country2_'+key],b['country1_'+key])
    def test_non_us_pair_ratio(self):
        r=compare(replace(self.p,yield1=.06))
        self.assertAlmostEqual((1+r['country2_equity'])/(1+r['country1_equity']),1.12/1.06,14)
    def test_side_override_isolation(self):
        a=compare(self.p)
        for side in [1,2]:
            b=compare(replace(self.p,**{f'spread{side}':.04}))
            other=3-side
            for key in ['equity','debt','aftertax_debt','wacc']:
                self.assertEqual(a[f'country{other}_'+key],b[f'country{other}_'+key])
            self.assertEqual(a[f'country{side}_equity'],b[f'country{side}_equity'])
            self.assertEqual(a['usd_wacc'],b['usd_wacc'])
    def test_equal_yields_and_zero_debt(self):
        r=compare(replace(self.p,yield1=.12,debt_share=0))
        self.assertEqual(r['country1_wacc'],r['country2_wacc'])
        for side in [1,2]: self.assertEqual(r[f'country{side}_wacc'],r[f'country{side}_equity'])
    def test_market_source(self):
        rows=snapshot()['betas']['rows'];market=next(r for r in rows if r['industry']=='Total Market')
        self.assertEqual(market['source_row'],'Total Market (without financials)')
        self.assertAlmostEqual(market['beta'],.877517,5)
        self.assertEqual(len(rows),95)

class LocationTests(unittest.TestCase):
    def setUp(self): self.p=PairInputs(.8,.35,.3,.065,.04,.04,.12,.015,tax1=.25,tax2=.35)
    def test_independent_location_arithmetic(self):
        r=compare(self.p)
        # Independent direct algebra, using distinct statutory taxes.
        for side,tax,yield_ in [(1,.25,.04),(2,.35,.12)]:
            beta=.8*(1+(1-tax)*3/7)
            equity=(1+.04+beta*.065)*(1+yield_)/1.04-1
            debt=yield_+.015*(1+yield_)/1.04
            self.assertAlmostEqual(r[f'country{side}_beta_e'],beta,14)
            self.assertAlmostEqual(r[f'country{side}_aftertax_debt'],debt*(1-tax),14)
            self.assertAlmostEqual(r[f'country{side}_wacc'],.7*equity+.3*debt*(1-tax),14)
        self.assertAlmostEqual(r['country1_wacc'],.088475,12)
        self.assertAlmostEqual(r['country2_wacc'],.16067,12)
    def test_same_taxes_reproduce_class(self):
        a=compare(replace(self.p,tax1=.35));b=compare(replace(self.p,tax1=None,tax2=None))
        for side in [1,2]:
            for metric in ['beta_e','equity','debt','aftertax_debt','wacc']:
                self.assertEqual(a[f'country{side}_{metric}'],b[f'country{side}_{metric}'])
    def test_tax_isolation_and_swap(self):
        a=compare(self.p);b=compare(replace(self.p,tax2=.1))
        for key in a:
            if key.startswith('country1_'): self.assertEqual(a[key],b[key])
        self.assertEqual(a['country2_debt'],b['country2_debt'])
        self.assertNotEqual(a['country2_equity'],b['country2_equity'])
        c=compare(replace(self.p,tax1=.35,tax2=.25,yield1=.12,yield2=.04))
        self.assertEqual(a['country1_wacc'],c['country2_wacc'])
        self.assertEqual(a['country2_wacc'],c['country1_wacc'])
    def test_zero_debt_tax_irrelevant_and_invalid_tax(self):
        a=compare(replace(self.p,debt_share=0));b=compare(replace(self.p,debt_share=0,tax1=.1,tax2=.9))
        for side in [1,2]: self.assertEqual(a[f'country{side}_wacc'],b[f'country{side}_wacc'])
        for tax in [-.1,1.1,float('nan')]:
            with self.assertRaises(ValueError): compare(replace(self.p,tax2=tax))

class UITests(unittest.TestCase):
    def app(self):
        a=AppTest.from_file('app.py',default_timeout=30).run()
        self.assertFalse(a.exception)
        return a
    def test_defaults_and_two_non_us_countries(self):
        a=self.app()
        self.assertEqual(a.selectbox(key='industry').value,'Software (System & Application)')
        self.assertEqual(a.selectbox(key='country1').value,'USA')
        self.assertEqual(a.selectbox(key='country2').value,'USA')
        self.assertEqual(a.metric[0].value,a.metric[4].value)
        a.selectbox(key='country1').set_value('CHL').run()
        a.selectbox(key='country2').set_value('COL').run()
        a.radio(key='tax_country').set_value('COL').run()
        self.assertFalse(a.exception)
        self.assertNotEqual(a.metric[0].value,a.metric[4].value)
        before=[x.value for x in a.metric[:4]]
        a.toggle(key='on_spread2_COL').set_value(True).run()
        a.number_input(key='value_spread2_COL').set_value(4.).run()
        self.assertEqual(before,[x.value for x in a.metric[:4]])
    def test_total_market_and_manual_beta(self):
        a=self.app()
        a.selectbox(key='industry').set_value('Total Market').run()
        self.assertFalse(a.exception)
        self.assertEqual(len(a.dataframe[0].value),95)
        self.assertEqual(a.dataframe[0].value.iloc[0]['Industry'],'Total Market')
        original=a.dataframe[0].value.iloc[0]['Country 1 wacc (%)']
        a.toggle(key='on_beta_Total Market').set_value(True).run()
        a.number_input(key='value_beta_Total Market').set_value(1.5).run()
        self.assertFalse(a.exception)
        self.assertEqual(a.dataframe[0].value.iloc[0]['Country 1 wacc (%)'],original)
        self.assertNotEqual(float(a.metric[0].value.strip('%')),round(original,2))
    def test_missing_country_manual_input(self):
        a=self.app();a.selectbox(key='country1').set_value('ATA').run()
        self.assertTrue(a.info)
        a.toggle(key='on_yield1_ATA').set_value(True).run()
        a.number_input(key='value_yield1_ATA').set_value(5.).run()
        self.assertFalse(a.exception);self.assertEqual(len(a.metric),8)
    def test_us_reference_shared_and_tax_switch(self):
        a=self.app()
        a.toggle(key='on_us_yield').set_value(True).run()
        a.number_input(key='value_us_yield').set_value(4.).run()
        self.assertEqual(a.metric[0].value,a.metric[4].value)
        a.selectbox(key='country2').set_value('COL').run()
        a.radio(key='tax_country').set_value('COL').run()
        a.selectbox(key='country2').set_value('GBR').run()
        self.assertFalse(a.exception)
        self.assertIn(a.radio(key='tax_country').value,['USA','GBR'])

    def test_location_mode_tax_and_market(self):
        a=self.app();a.selectbox(key='country2').set_value('COL').run()
        original=[m.value for m in a.metric]
        a.radio(key='comparison_mode').set_value('Project location').run()
        self.assertFalse(a.exception)
        self.assertEqual(a.metric[0].value,original[0])
        self.assertNotEqual(a.metric[4].value,original[4])
        table=a.dataframe[0].value
        self.assertNotEqual(table.iloc[0]['Country 1 equity beta'],table.iloc[0]['Country 2 equity beta'])
        first=[m.value for m in a.metric[:4]]
        a.toggle(key='on_location_tax2_COL').set_value(True).run()
        a.number_input(key='value_location_tax2_COL').set_value(20.).run()
        self.assertEqual(first,[m.value for m in a.metric[:4]])
        self.assertNotEqual(table.iloc[0]['Country 2 wacc (%)'],a.dataframe[0].value.iloc[0]['Country 2 wacc (%)'])
        a.radio(key='comparison_mode').set_value('Class method').run()
        self.assertFalse(a.exception)
        self.assertEqual(original,[m.value for m in a.metric])
    def test_location_missing_tax_requires_override(self):
        a=self.app();a.radio(key='comparison_mode').set_value('Project location').run()
        a.selectbox(key='country1').set_value('ATA').run()
        a.toggle(key='on_yield1_ATA').set_value(True).run()
        a.number_input(key='value_yield1_ATA').set_value(5.).run()
        self.assertTrue(a.info);self.assertEqual(len(a.metric),0)
        a.toggle(key='on_location_tax1_ATA').set_value(True).run()
        a.number_input(key='value_location_tax1_ATA').set_value(25.).run()
        self.assertFalse(a.exception);self.assertEqual(len(a.metric),8)

if __name__=='__main__': unittest.main(verbosity=2)
