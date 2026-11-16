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

class UITests(unittest.TestCase):
    def test_defaults_and_overrides(self):
        a=AppTest.from_file('app.py',default_timeout=30).run()
        self.assertFalse(a.exception)
        self.assertEqual(a.selectbox[0].value,'Software (System & Application)')
        self.assertEqual(a.selectbox[1].value,'USA')
        self.assertEqual(a.metric[0].value,a.metric[4].value)
        a.selectbox[1].set_value('COL').run()
        a.radio[0].set_value('Selected country').run()
        self.assertFalse(a.exception)
        before=[m.value for m in a.metric[:4]]
        a.toggle(key='on_foreign_spread_COL').set_value(True).run()
        a.number_input(key='value_foreign_spread_COL').set_value(4.0).run()
        self.assertFalse(a.exception)
        self.assertEqual(before,[m.value for m in a.metric[:4]])
        a.toggle(key='on_foreign_spread_COL').set_value(False).run()
        a.selectbox[1].set_value('USA').run()
        a.radio[0].set_value('United States').run()
        self.assertEqual(a.metric[0].value,a.metric[4].value)
    def test_missing_data_requires_override(self):
        a=AppTest.from_file('app.py',default_timeout=30).run()
        a.selectbox[1].set_value('ATA').run()
        self.assertFalse(a.exception)
        self.assertTrue(a.info)
        a.toggle(key='on_yield_ATA').set_value(True).run()
        a.number_input(key='value_yield_ATA').set_value(5.0).run()
        self.assertFalse(a.exception)
        self.assertEqual(len(a.metric),8)

if __name__=='__main__': unittest.main(verbosity=2)

