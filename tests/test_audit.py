# SPDX-License-Identifier: MIT
"""Synthetic regression tests; these do not audit a customer application."""
from __future__ import annotations
import base64
import copy
import hashlib
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from common import load_core
m=load_core()

class AuditTests(unittest.TestCase):
    def setUp(self):
        self.d=m.read_json(ROOT/'examples/audit.demo.json')
        self.r=m.get_rubric();self.p=m.get_policy()
    def score(self):return m.calculate(self.d,self.r,self.p)['summary']
    def check(self,ident):return next(c for c in self.d['checks'] if c['criterion']==ident)
    def clean(self):
        self.d['findings']=[]
        for c in self.d['checks']:
            c.update(status='pass',finding_ids=[],evidence_ids=['E-001'])
    def add_clone(self,index=0,n=1):
        original=self.d['findings'][index]
        for i in range(n):
            f=copy.deepcopy(original);f['id']=f'G-extra-{i}';f['root_cause_key']=f'independent-{i}'
            f['blocker']=False;f['blocker_rule_id']=None;f['blocker_reason']=''
            self.d['findings'].append(f)
            for cid in f['criterion_ids']:self.check(cid)['finding_ids'].append(f['id'])
    def test_demo_raw_91(self):self.assertEqual(self.score()['raw_score'],91)
    def test_demo_capped_59(self):self.assertEqual(self.score()['score'],59)
    def test_demo_deduction_9(self):self.assertEqual(self.score()['weighted_deduction'],9)
    def test_nine_dimensions(self):self.assertEqual(len(self.score()['dimensions']),9)
    def test_dimension_security_80(self):self.assertEqual(self.score()['dimensions'][1]['score'],80)
    def test_complete_coverage(self):self.assertEqual(self.score()['coverage'],100)
    def test_count_blockers(self):self.assertEqual(len(self.score()['confirmed_blockers']),2)
    def test_all_pass_100(self):self.clean();self.assertEqual(self.score()['score'],100)
    def test_all_pass_grade(self):self.clean();self.assertEqual(self.score()['grade'],'良好')
    def test_no_blockers_raw_retained(self):
        for f in self.d['findings']:f.update(blocker=False,blocker_rule_id=None,blocker_reason='')
        self.assertEqual(self.score()['score'],91)
    def test_critical_review_failure_not_automatic_blocker(self):
        for f in self.d['findings']:f.update(blocker=False,blocker_rule_id=None,blocker_reason='')
        self.assertEqual(self.score()['confirmed_blockers'],[])
    def test_new_empty_draft_unscored(self):
        s=m.calculate(m.blank('测试'))['summary'];self.assertIsNone(s['score']);self.assertIsNone(s['provisional_upper'])
    def test_ready_but_all_unknown_unscored(self):
        self.clean()
        for c in self.d['checks']:c.update(status='unknown',evidence_ids=[])
        self.assertEqual(self.score()['status'],'unscored')
    def test_unreviewed_dimension_not_100(self):
        self.clean()
        for c in self.d['checks']:
            if c['criterion'].startswith('D'):c.update(status='unknown',evidence_ids=[])
        dim=self.score()['dimensions'][3];self.assertIsNone(dim['score']);self.assertIsNone(dim['provisional_score'])
    def test_partial_no_final_score(self):
        self.d=m.read_json(ROOT/'examples/audit.partial.json');self.assertIsNone(self.score()['score'])
    def test_partial_upper_59(self):
        self.d=m.read_json(ROOT/'examples/audit.partial.json');self.assertEqual(self.score()['provisional_upper'],59)
    def test_unknown_no_deduction(self):
        self.d=m.read_json(ROOT/'examples/audit.partial.json');self.assertEqual(self.score()['weighted_deduction'],9)
    def test_critical_unknown_retained(self):
        self.d=m.read_json(ROOT/'examples/audit.partial.json');self.assertIn('I2',self.score()['critical_unknowns'])
    def test_one_root_multiple_criteria_once(self):
        f=self.d['findings'][0];new='B2' if 'B2' not in f['criterion_ids'] else 'B1'
        f['criterion_ids'].append(new);c=self.check(new);c.update(status='fail',finding_ids=[f['id']],evidence_ids=f['evidence_ids'])
        self.assertEqual(self.score()['raw_score'],91)
    def test_independent_roots_same_criterion_each_deduct(self):
        self.add_clone();self.assertEqual(self.score()['raw_score'],87)
    def test_dimension_floor_zero(self):
        self.add_clone(n=7);dim=self.score()['dimensions'][1]
        self.assertEqual(dim['score'],0);self.assertEqual(dim['deducted'],100);self.assertGreater(dim['raw_deduction'],100)
    def test_reordering_does_not_change_score(self):
        before=self.score()['raw_score'];self.d['findings'].reverse();self.d['checks'].reverse();self.assertEqual(before,self.score()['raw_score'])
    def test_duplicate_root_rejected(self):
        self.add_clone();self.d['findings'][-1]['root_cause_key']=self.d['findings'][0]['root_cause_key']
        with self.assertRaisesRegex(m.AuditError,'Duplicate root'):self.score()
    def test_duplicate_root_casefold_rejected(self):
        self.add_clone();self.d['findings'][-1]['root_cause_key']=' '+self.d['findings'][0]['root_cause_key'].upper()+' '
        with self.assertRaises(m.AuditError):self.score()
    def test_duplicate_check_id_rejected(self):
        self.d['checks'].append(copy.deepcopy(self.d['checks'][0]))
        with self.assertRaisesRegex(m.AuditError,'Duplicate'):self.score()
    def test_missing_criterion_rejected(self):
        self.d['checks'].pop()
        with self.assertRaisesRegex(m.AuditError,'Missing criteria'):self.score()
    def test_unknown_criterion_rejected(self):
        self.d['checks'][0]['criterion']='NOT-A-RULE'
        with self.assertRaises(m.AuditError):self.score()
    def test_per_check_weight_rejected(self):
        self.d['checks'][0]['weight']=4
        with self.assertRaisesRegex(m.AuditError,'weights'):self.score()
    def test_per_finding_manual_penalty_rejected(self):
        self.d['findings'][0]['points']=0
        with self.assertRaisesRegex(m.AuditError,'policy'):self.score()
    def test_manual_summary_ignored(self):
        self.d['summary']={'score':100};self.assertEqual(self.score()['score'],59)
    def test_finding_evidence_required(self):
        self.d['findings'][0]['evidence_ids']=[]
        with self.assertRaises(m.AuditError):self.score()
    def test_check_evidence_required(self):
        self.d['checks'][0]['evidence_ids']=[]
        with self.assertRaises(m.AuditError):self.score()
    def test_missing_evidence_link_rejected(self):
        self.d['findings'][0]['evidence_ids']=['MISSING']
        with self.assertRaises(m.AuditError):self.score()
    def test_missing_scope_link_rejected(self):
        self.d['checks'][0]['scope_refs']=['MISSING']
        with self.assertRaises(m.AuditError):self.score()
    def test_root_location_required(self):
        self.d['findings'][0]['locations']=[]
        with self.assertRaises(m.AuditError):self.score()
    def test_severity_reason_required(self):
        self.d['findings'][0]['severity_reason']=''
        with self.assertRaises(m.AuditError):self.score()
    def test_blocker_rule_required(self):
        self.d['findings'][0]['blocker_rule_id']=None
        with self.assertRaises(m.AuditError):self.score()
    def test_blocker_reason_required(self):
        self.d['findings'][0]['blocker_reason']=''
        with self.assertRaises(m.AuditError):self.score()
    def test_unknown_cannot_block(self):
        self.d['findings'][0]['status']='unknown'
        with self.assertRaises(m.AuditError):self.score()
    def test_blocker_dimension_mismatch(self):
        self.d['findings'][0]['blocker_rule_id']='NO-RECOVERY'
        with self.assertRaises(m.AuditError):self.score()
    def test_criterion_primary_dimension_required(self):
        self.d['findings'][0]['dimension_id']='I'
        with self.assertRaises(m.AuditError):self.score()
    def test_unlinked_finding_rejected(self):
        f=self.d['findings'][0]
        for c in self.d['checks']:
            if f['id'] in c['finding_ids']:c.update(status='pass',finding_ids=[])
        with self.assertRaisesRegex(m.AuditError,'matching check'):self.score()
    def test_fail_without_finding_rejected(self):
        self.check('A1').update(status='fail',finding_ids=[])
        with self.assertRaises(m.AuditError):self.score()
    def test_real_report_cannot_use_synthetic_evidence(self):
        self.d['meta']['is_demo']=False
        with self.assertRaisesRegex(m.AuditError,'demo evidence'):self.score()
    def test_baseline_not_ready_unscored(self):
        self.d['baseline_ready']=False;self.assertEqual(self.score()['status'],'unscored')
    def test_old_schema_rejected(self):
        self.d['schema_version']='1.0'
        with self.assertRaisesRegex(m.AuditError,'re-review'):self.score()
    def test_policy_version_mismatch(self):
        self.d['policy_version']='old'
        with self.assertRaises(m.AuditError):self.score()
    def test_rubric_version_mismatch(self):
        self.d['rubric_version']='old'
        with self.assertRaises(m.AuditError):self.score()
    def test_policy_bool_not_number(self):
        self.p['severity_deductions']['low']=True
        with self.assertRaises(m.AuditError):self.score()
    def test_dimension_weight_sum_enforced(self):
        self.r['dimensions'][0]['weight']=19
        with self.assertRaisesRegex(m.AuditError,'total 100'):self.score()
    def test_criterion_cannot_have_weight(self):
        self.r['dimensions'][0]['criteria'][0]['weight']=1
        with self.assertRaisesRegex(m.AuditError,'must not have weights'):self.score()
    def test_critical_penalty_monotonic(self):
        self.p['severity_deductions']['critical']=2
        with self.assertRaises(m.AuditError):self.score()
    def test_blocker_cap_must_fail_grade(self):
        self.p['blocker_cap']=60
        with self.assertRaises(m.AuditError):self.score()
    def test_split_checks_do_not_inflate_coverage(self):
        c=copy.deepcopy(self.check('A1'));c['id']='A1.second';self.d['checks'].append(c)
        self.assertEqual(self.score()['applicable_criteria'],27)
    def test_split_with_unknown_not_completed(self):
        c=copy.deepcopy(self.check('A1'));c.update(id='A1.pending',status='unknown',evidence_ids=[])
        self.d['checks'].append(c);self.assertEqual(self.score()['reviewed_criteria'],26)
    def test_new_rule_requires_no_weight_reallocation(self):
        c=copy.deepcopy(self.r['dimensions'][3]['criteria'][0]);c['id']='D4'
        self.r['dimensions'][3]['criteria'].append(c)
        check=copy.deepcopy(self.check('D2'));check.update(id='D4',criterion='D4',status='pass',finding_ids=[])
        self.d['checks'].append(check);self.assertEqual(self.score()['raw_score'],91)
        self.assertEqual(sum(d['weight'] for d in self.r['dimensions']),100)
    def test_new_unknown_rule_preserves_existing_deductions(self):
        c=copy.deepcopy(self.r['dimensions'][3]['criteria'][0]);c['id']='D4';self.r['dimensions'][3]['criteria'].append(c)
        check=copy.deepcopy(self.check('D2'));check.update(id='D4',criterion='D4',status='unknown',finding_ids=[],evidence_ids=[])
        self.d['checks'].append(check);self.assertEqual(self.score()['weighted_deduction'],9);self.assertIsNone(self.score()['score'])
    def test_schema_contains_new_rule_automatically(self):
        c=copy.deepcopy(self.r['dimensions'][3]['criteria'][0]);c['id']='D4';self.r['dimensions'][3]['criteria'].append(c)
        schema=m.generate_schema(self.r,self.p)
        self.assertIn('D4',schema['properties']['checks']['items']['properties']['criterion']['enum'])
    def test_blank_new_rule_is_unknown(self):
        c=copy.deepcopy(self.r['dimensions'][3]['criteria'][0]);c['id']='D4';self.r['dimensions'][3]['criteria'].append(c)
        new=m.blank('new',rubric=self.r,policy=self.p);self.assertEqual(new['checks'][-1]['status'],'unknown');self.assertEqual(len(new['checks']),28)
    def test_generated_rules_in_sync(self):m.sync_rules(check=True)
    def test_digest_changes_with_policy(self):
        first=self.score()['policy_sha256'];self.p['severity_deductions']['low']=4
        self.assertNotEqual(first,self.score()['policy_sha256'])
    def test_rule_snapshots_embedded(self):self.assertEqual(self.score()['rule_snapshot']['rubric'],self.r)
    def test_individual_na_does_not_reweight(self):
        self.check('A1').update(status='na',evidence_ids=[],reason='Synthetic scope excludes this behavior.')
        self.assertEqual(self.score()['active_weight'],100);self.assertEqual(self.score()['raw_score'],91)
    def test_whole_na_dimension_disclosed(self):
        for c in self.d['checks']:
            if c['criterion'].startswith('G'):c.update(status='na',evidence_ids=[],reason='Synthetic scope exclusion.')
        self.assertEqual(self.score()['active_weight'],95);self.assertEqual(self.score()['excluded_dimensions'],['G'])
    def test_all_na_not_full_score(self):
        self.clean()
        for c in self.d['checks']:c.update(status='na',evidence_ids=[],reason='Synthetic exclusion.')
        self.assertIsNone(self.score()['score'])
    def test_na_reason_required(self):
        self.check('A1').update(status='na',reason='')
        with self.assertRaises(m.AuditError):self.score()
    def test_unknown_finding_not_deducted(self):
        f=self.d['findings'][0];f.update(status='unknown',blocker=False,blocker_rule_id=None,blocker_reason='')
        for cid in f['criterion_ids']:self.check(cid)['status']='unknown'
        self.assertEqual(self.score()['weighted_deduction'],5)
    def test_single_dimension_thresholds(self):
        self.clean();self.r['dimensions']=self.r['dimensions'][:1];self.r['dimensions'][0]['weight']=100
        self.p['blocker_rules']=[];self.d['checks']=[c for c in self.d['checks'] if c['criterion'].startswith('A')]
        f=copy.deepcopy(m.read_json(ROOT/'examples/audit.demo.json')['findings'][0])
        f.update(dimension_id='A',criterion_ids=['A1'],blocker=False,blocker_rule_id=None,blocker_reason='')
        self.d['findings']=[f];self.check('A1').update(status='fail',finding_ids=[f['id']],evidence_ids=f['evidence_ids'])
        for penalty,grade in [(20,'良好'),(40,'合格'),(41,'不合格')]:
            with self.subTest(penalty=penalty):
                self.p['severity_deductions']['high']=penalty;self.p['severity_deductions']['critical']=100
                self.assertEqual(self.score()['grade'],grade)
    def test_final_score_does_not_round_into_higher_grade(self):
        self.clean();self.r['dimensions'][0]['weight']=99.99;self.r['dimensions'][1]['weight']=0.01
        self.r['dimensions']=self.r['dimensions'][:2];self.p['blocker_rules']=[]
        self.d['checks']=[c for c in self.d['checks'] if c['criterion'][0] in {'A','B'}]
        f=copy.deepcopy(m.read_json(ROOT/'examples/audit.demo.json')['findings'][0])
        f.update(dimension_id='A',criterion_ids=['A1'],blocker=False,blocker_rule_id=None,blocker_reason='')
        self.d['findings']=[f];self.check('A1').update(status='fail',finding_ids=[f['id']],evidence_ids=f['evidence_ids'])
        self.p['severity_deductions']['high']=40.01;self.p['severity_deductions']['critical']=100
        self.assertEqual(self.score()['grade'],'不合格');self.assertLess(self.score()['score'],60)
    def test_site_mock_matches_current_demo_scores(self):
        summary=self.score()
        expected=[str(summary['raw_score']),str(summary['weighted_deduction']),str(summary['score'])]
        for rel in ('site/index.html','site/en/index.html'):
            text=(ROOT/rel).read_text(encoding='utf-8')
            block=text.split('<div class="calculation">',1)[1].split('<div class="mini-bars">',1)[0]
            self.assertEqual(re.findall(r'<b>([0-9.]+)</b>',block),expected)
    def test_html_injection_escaped(self):
        self.d['findings'][0]['title']='</script><script>alert(1)</script>'
        rendered=m.render(self.d)
        self.assertNotIn('</script><script>alert(1)</script>',rendered)
        self.assertIn('\\u003c/script\\u003e',rendered)
    def test_csp_hash_matches_executable_script(self):
        html=m.render(self.d);script=re.findall(r'<script>(.*?)</script>',html,re.S)[0]
        encoded=base64.b64encode(hashlib.sha256(script.encode()).digest()).decode()
        self.assertIn("'sha256-"+encoded+"'",html)
    def test_indicator_titles_use_rubric_names_not_repeated_ids(self):
        """待验证卡片与检查表格的指标标题必须是量表名称，不能重复编号。"""
        html=m.render(self.d)
        script=re.findall(r'<script>(.*?)</script>',html,re.S)[0]
        self.assertNotIn("esc(check.id)+' · '+esc(check.criterion)",script)
        self.assertIn("esc(check.id)+' · '+esc(check.requirement)",script)
        rubric={c['id']:c['title'] for d in self.r['dimensions'] for c in d['criteria']}
        for check in self.d['checks']:
            self.assertEqual(check['criterion'],check['id'])
            self.assertIn(rubric[check['id']],json.dumps(m.calculate(self.d)['checks'],ensure_ascii=False))
    def test_input_not_mutated(self):
        before=copy.deepcopy(self.d);m.calculate(self.d);self.assertEqual(self.d,before)
    def test_scored_output_roundtrips(self):self.assertEqual(m.calculate(m.calculate(self.d))['summary']['score'],59)
    def test_duplicate_json_keys_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'x.json';p.write_text('{"a":1,"a":2}')
            with self.assertRaises(m.AuditError):m.read_json(p)
    def test_nan_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'x.json';p.write_text('{"a":NaN}')
            with self.assertRaises(m.AuditError):m.read_json(p)
    def test_non_object_root_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'x.json';p.write_text('[]')
            with self.assertRaises(m.AuditError):m.read_json(p)
    def test_utf8_bom_supported(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'x.json';p.write_text('{"名":"值"}',encoding='utf-8-sig');self.assertEqual(m.read_json(p),{'名':'值'})
    def test_output_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'x';m.save(p,'first')
            with self.assertRaises(m.AuditError):m.save(p,'second')
    def test_output_cannot_replace_input(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'x';p.write_text('original')
            with self.assertRaises(m.AuditError):m.save(p,'changed',True,p)

if __name__=='__main__':unittest.main()
