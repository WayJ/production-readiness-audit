#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Validate evidence records, calculate scores, and render an offline report.

This program does not scan the reviewed codebase or execute its scripts.
Python 3.10+; standard library only. Paths are independent of the current directory.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import copy
import json
import math
import re
import sys
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP, ROUND_FLOOR
from pathlib import Path
from typing import Any

VERSION = "0.2.0"
SKILL = Path(__file__).resolve().parents[1]
ASSETS = SKILL / "assets"
MAX_INPUT_BYTES = 8 * 1024 * 1024
IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}\Z")


class AuditError(ValueError):
    """Invalid input or unsafe output operation, with a user-actionable message."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AuditError(message)


def no_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        require(key not in result, f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def read_json(path: Path) -> dict[str, Any]:
    require(path.is_file(), f"Input file not found: {path}")
    require(path.stat().st_size <= MAX_INPUT_BYTES, "Input exceeds the 8 MiB limit.")
    def reject_constant(value: str) -> None:
        raise AuditError(f"Non-finite JSON number is not allowed: {value}")
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"),
                           object_pairs_hook=no_duplicate_keys,
                           parse_constant=reject_constant)
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise AuditError(f"Invalid UTF-8 JSON in {path.name}: {exc}") from exc
    require(isinstance(value, dict), "The JSON root must be an object.")
    return value


def get_rubric() -> dict[str, Any]:
    return read_json(ASSETS / "scoring-rubric.json")

def get_policy() -> dict[str, Any]:
    return read_json(ASSETS / "scoring-policy.json")


def nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def strings(value: Any, label: str, *, allow_empty: bool = True) -> list[str]:
    require(isinstance(value, list), f"{label} must be an array.")
    require(all(nonempty(v) for v in value), f"{label} must contain nonempty strings.")
    require(allow_empty or bool(value), f"{label} must not be empty.")
    require(len(value) == len(set(value)), f"{label} contains duplicate values.")
    return value


def indexed(value: Any, label: str) -> dict[str, dict[str, Any]]:
    require(isinstance(value, list), f"{label} must be an array.")
    result: dict[str, dict[str, Any]] = {}
    for item in value:
        require(isinstance(item, dict), f"Each {label} entry must be an object.")
        ident = item.get("id")
        require(isinstance(ident, str) and bool(IDENTIFIER.fullmatch(ident)),
                f"{label}: invalid id {ident!r}.")
        require(ident not in result, f"Duplicate {label} id: {ident}")
        result[ident] = item
    return result


def number(value: Any, label: str) -> Decimal:
    require(type(value) in (int, float) and 0 < value <= 100 and math.isfinite(value),
            f"{label} must be a finite number, not a boolean.")
    result = Decimal(str(value))
    require(result > 0 and result.as_tuple().exponent >= -2,
            f"{label} must be positive with at most two decimal places.")
    return result


def plain(value: Decimal) -> int | float:
    return int(value) if value == value.to_integral_value() else float(value)



def validate_rules(rubric: dict[str, Any], policy: dict[str, Any]) -> None:
    """Rule sources are independently versioned; criterion counts are never hard-coded."""
    require(nonempty(rubric.get('rubric_version')), 'rubric_version is required.')
    dims = indexed(rubric.get('dimensions'), 'dimensions')
    require(bool(dims), 'At least one dimension is required.')
    total = Decimal(0)
    seen: set[str] = set()
    for dim in dims.values():
        require(nonempty(dim.get('name')), f"Dimension {dim['id']}: name required.")
        total += number(dim.get('weight'), f"Dimension {dim['id']}.weight")
        criteria = indexed(dim.get('criteria'), f"Dimension {dim['id']} criteria")
        require(bool(criteria), 'Each dimension must have at least one criterion.')
        for c in criteria.values():
            require(c['id'] not in seen, f"Duplicate criterion: {c['id']}")
            seen.add(c['id'])
            require('weight' not in c and 'points' not in c, 'Criteria must not have weights or points.')
            for key in ('title', 'requirement', 'proof', 'applicability', 'pass_condition',
                        'fail_condition', 'deduplication'):
                require(nonempty(c.get(key)), f"Criterion {c['id']}: {key} required.")
            require(type(c.get('critical_review')) is bool, 'critical_review must be boolean.')
    require(total == 100, f'Dimension weights must total 100; got {total}.')
    require(nonempty(policy.get('policy_version')), 'policy_version is required.')
    require(policy.get('mode') == 'dimension_deductions', 'Unsupported scoring mode.')
    require(type(policy.get('dimension_base')) is int and policy['dimension_base'] == 100,
            'Dimension base must be integer 100.')
    penalties = policy.get('severity_deductions')
    require(isinstance(penalties, dict) and set(penalties) == {'low', 'medium', 'high', 'critical'},
            'Policy must define low/medium/high/critical deductions.')
    amounts = [number(penalties[k], 'Severity deduction') for k in ('low', 'medium', 'high', 'critical')]
    require(amounts == sorted(amounts), 'Penalties must be nondecreasing with severity.')
    grades = policy.get('grades', {})
    require(isinstance(grades, dict), 'grades must be an object.')
    good, passed = number(grades.get('good'), 'grades.good'), number(grades.get('pass'), 'grades.pass')
    require(good > passed, 'Good threshold must exceed pass threshold.')
    cap = number(policy.get('blocker_cap'), 'blocker_cap')
    require(cap < passed, 'Blocker cap must be below the pass threshold.')
    require(policy.get('dimension_na_policy') == 'exclude_and_normalize', 'Unsupported NA policy.')
    for b in indexed(policy.get('blocker_rules'), 'blocker rules').values():
        for key in ('title', 'condition'):
            require(nonempty(b.get(key)), f'Blocker {key} required.')
        refs = strings(b.get('dimensions'), 'Blocker dimensions', allow_empty=False)
        require(set(refs) <= set(dims), 'Blocker rule refers to an unknown dimension.')


def validate(data: dict[str, Any], rubric: dict[str, Any] | None = None,
             policy: dict[str, Any] | None = None) -> dict[str, Any]:
    """Validate real evidence links; never accept caller-authored score or penalty values."""
    rubric = get_rubric() if rubric is None else rubric
    policy = get_policy() if policy is None else policy
    validate_rules(rubric, policy)
    require(isinstance(data, dict), 'Audit must be an object.')
    d = copy.deepcopy(data)
    d.pop('summary', None)
    allowed = {'schema_version', 'rubric_version', 'policy_version', 'baseline_ready', 'meta',
               'conclusion', 'baseline', 'checks', 'findings', 'evidence'}
    require(set(d) <= allowed, f'Unknown top-level fields: {sorted(set(d)-allowed)}')
    require(d.get('schema_version') == '2.0', 'Unsupported schema_version: expected 2.0; v1 inputs need re-review.')
    require(d.get('rubric_version') == rubric['rubric_version'], 'rubric_version mismatch.')
    require(d.get('policy_version') == policy['policy_version'], 'policy_version mismatch.')
    require(type(d.get('baseline_ready')) is bool, 'baseline_ready must be boolean.')
    meta = d.get('meta')
    require(isinstance(meta, dict), 'meta must be an object.')
    for key in ('title', 'project', 'version', 'reviewed_at', 'snapshot', 'environment'):
        require(nonempty(meta.get(key)), f'meta.{key} is required.')
    require(type(meta.get('is_demo')) is bool, 'meta.is_demo must explicitly be boolean.')
    meta['template_version'] = '3.0'
    require(nonempty(d.get('conclusion')), 'conclusion is required.')
    baseline = d.get('baseline')
    require(isinstance(baseline, dict), 'baseline must be an object.')
    strings(baseline.get('scope'), 'baseline.scope', allow_empty=not d['baseline_ready'])
    strings(baseline.get('limitations'), 'baseline.limitations', allow_empty=False)
    conditions = indexed(baseline.get('conditions'), 'conditions')
    flows = indexed(baseline.get('key_flows'), 'key_flows')
    require(not (set(conditions) & set(flows)), 'Condition and flow ids must be distinct.')
    if d['baseline_ready']:
        require(bool(conditions) and bool(flows), 'A ready baseline needs conditions and key_flows.')
        require(meta['snapshot'].strip().casefold() not in {'tbd', 'unknown', '待确认', '待建立'},
                'A ready baseline needs a concrete snapshot.')
    for c in conditions.values():
        for key in ('label', 'value', 'status', 'source'):
            require(nonempty(c.get(key)), f"Condition {c['id']}: {key} required.")
    for f in flows.values():
        for key in ('name', 'expected', 'status'):
            require(nonempty(f.get(key)), f"Flow {f['id']}: {key} required.")
    scope_ids = set(conditions) | set(flows)
    evidence = indexed(d.get('evidence'), 'evidence')
    for e in evidence.values():
        for key in ('method', 'location', 'expected', 'observed', 'limitations'):
            require(nonempty(e.get(key)), f"Evidence {e['id']}: {key} required.")
        require(type(e.get('is_demo')) is bool, f"Evidence {e['id']}: is_demo must be boolean.")
        require(meta['is_demo'] or not e['is_demo'], 'Real reports cannot include demo evidence.')
    def evidence_refs(item: dict[str, Any], label: str, required: bool = False) -> None:
        refs = strings(item.get('evidence_ids'), label+'.evidence_ids', allow_empty=not required)
        require(set(refs) <= set(evidence), f'{label}: missing evidence reference.')
    for f in flows.values():
        evidence_refs(f, 'Flow '+f['id'])
    dims = {dim['id']: dim for dim in rubric['dimensions']}
    criteria = {c['id']: {**c, 'dimension_id': dim['id']}
                for dim in rubric['dimensions'] for c in dim['criteria']}
    blockers = {b['id']: b for b in policy['blocker_rules']}
    findings = indexed(d.get('findings'), 'findings')
    roots: set[str] = set()
    finding_allowed = {'id','title','type','dimension_id','status','severity','severity_reason',
                       'blocker','blocker_rule_id','blocker_reason','cause','trigger','impact','scope',
                       'locations','evidence_ids','suggestion','acceptance','reproduction','priority',
                       'root_cause_key','criterion_ids'}
    for f in findings.values():
        fid = f['id']
        require(set(f) <= finding_allowed, f'Finding {fid}: unknown fields; deductions must come from policy.')
        for key in ('title','cause','trigger','impact','suggestion','acceptance','root_cause_key','severity_reason'):
            require(nonempty(f.get(key)), f'Finding {fid}: {key} required.')
        root = f['root_cause_key'].strip().casefold()
        require(root not in roots, f'Duplicate root cause: {root}; merge the findings instead of double charging.')
        roots.add(root)
        require(f.get('status') in {'confirmed','unknown'}, f'Finding {fid}: invalid status.')
        require(f.get('type') in {'vulnerability','bug','architecture','organization','verification'},
                f'Finding {fid}: invalid type.')
        require(f.get('dimension_id') in dims, f'Finding {fid}: invalid dimension_id.')
        require(f.get('severity') in policy['severity_deductions'], f'Finding {fid}: invalid severity.')
        related = strings(f.get('criterion_ids'), f'Finding {fid}.criterion_ids', allow_empty=False)
        require(set(related) <= set(criteria), f'Finding {fid}: unknown criterion.')
        require(any(criteria[x]['dimension_id'] == f['dimension_id'] for x in related),
                f'Finding {fid}: at least one criterion must belong to the primary dimension.')
        require(type(f.get('blocker')) is bool, f'Finding {fid}: blocker must be boolean.')
        if f['blocker']:
            rule_id = f.get('blocker_rule_id')
            require(f['status'] == 'confirmed', 'Unknown findings cannot be confirmed blockers.')
            require(rule_id in blockers, f'Finding {fid}: blocker_rule_id must name a policy rule.')
            require(f['dimension_id'] in blockers[rule_id]['dimensions'], 'Blocker rule/dimension mismatch.')
            require(nonempty(f.get('blocker_reason')), 'A blocker requires an evidence-based reason.')
        else:
            require(f.get('blocker_rule_id') is None and not f.get('blocker_reason'),
                    'Non-blockers must not carry an active blocker rule or reason.')
        for key in ('scope','locations'):
            strings(f.get(key), f'Finding {fid}.{key}', allow_empty=False)
        if 'reproduction' in f:
            strings(f['reproduction'], f'Finding {fid}.reproduction')
        evidence_refs(f, 'Finding '+fid, f['status'] == 'confirmed')
    checks = indexed(d.get('checks'), 'checks')
    seen_criteria: set[str] = set()
    linked: dict[str,set[str]] = {fid:set() for fid in findings}
    check_allowed = {'id','criterion','status','reason','scope_refs','evidence_ids','finding_ids',
                     'critical','requirement'}  # last two are overwritten, not trusted
    for cid, c in checks.items():
        require(set(c) <= check_allowed, f'Check {cid}: unknown fields; per-check weights are not supported.')
        criterion = c.get('criterion')
        require(criterion in criteria, f'Check {cid}: unknown criterion {criterion!r}.')
        rule = criteria[criterion]
        seen_criteria.add(criterion)
        require(c.get('status') in {'pass','fail','unknown','na'}, f'Check {cid}: invalid status.')
        require(nonempty(c.get('reason')), f'Check {cid}: reason required, including unknown/NA.')
        refs = strings(c.get('scope_refs'), f'Check {cid}.scope_refs', allow_empty=False)
        require(set(refs) <= scope_ids, f'Check {cid}: missing baseline reference.')
        c['critical'] = rule['critical_review']
        c['requirement'] = rule['title']
        evidence_refs(c, 'Check '+cid, c['status'] in {'pass','fail'})
        ids = strings(c.get('finding_ids'), f'Check {cid}.finding_ids')
        require(set(ids) <= set(findings), f'Check {cid}: missing finding.')
        require(c['status'] not in {'pass','na'} or not ids, 'Pass/NA checks cannot link findings.')
        require(c['status'] != 'fail' or bool(ids), f'Check {cid}: failed check needs a finding.')
        for fid in ids:
            f = findings[fid]
            require(criterion in f['criterion_ids'], f'Check {cid}: finding must link this criterion.')
            require(f['status'] == ('confirmed' if c['status']=='fail' else 'unknown'),
                    f'Check {cid}: finding/check evidence status mismatch.')
            if c['status'] == 'fail':
                require(bool(set(c['evidence_ids']) & set(f['evidence_ids'])),
                        'Failed check and finding must share supporting evidence.')
            linked[fid].add(criterion)
    require(seen_criteria == set(criteria), f'Missing criteria: {sorted(set(criteria)-seen_criteria)}; include unknowns.')
    for fid, f in findings.items():
        require(linked[fid] == set(f['criterion_ids']), f'Finding {fid}: every related criterion needs a matching check.')
    return d


def rounded(value: Decimal) -> int | float:
    return plain(value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))


def digest(value: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':')).encode('utf-8')).hexdigest()


def calculate(data: dict[str, Any], rubric: dict[str, Any] | None = None,
              policy: dict[str, Any] | None = None) -> dict[str, Any]:
    rubric = get_rubric() if rubric is None else rubric
    policy = get_policy() if policy is None else policy
    d = validate(data, rubric, policy)
    findings, checks = d['findings'], d['checks']
    rollup: dict[str,str] = {}
    critical_unknowns: list[str] = []
    for dim in rubric['dimensions']:
        for rule in dim['criteria']:
            states = {c['status'] for c in checks if c['criterion']==rule['id']}
            state = 'unknown' if 'unknown' in states else 'fail' if 'fail' in states else 'pass' if 'pass' in states else 'na'
            rollup[rule['id']] = state
            if state=='unknown' and rule['critical_review']:
                critical_unknowns.append(rule['id'])
    dimensions: list[dict[str,Any]] = []
    active_weight = Decimal(0)
    weighted_total = Decimal(0)
    reviewed_total = 0
    for dim in rubric['dimensions']:
        states = [rollup[c['id']] for c in dim['criteria']]
        counts = {s:states.count(s) for s in ('pass','fail','unknown','na')}
        applicable = len(states)-counts['na']
        reviewed = counts['pass']+counts['fail']
        relevant = [f for f in findings if f['dimension_id']==dim['id'] and f['status']=='confirmed']
        raw_penalty = sum((Decimal(str(policy['severity_deductions'][f['severity']])) for f in relevant), Decimal(0))
        deduction = min(Decimal(100), raw_penalty)
        candidate = Decimal(100)-deduction
        status = ('not_applicable' if applicable==0 else 'unreviewed' if reviewed==0 and not relevant else
                  'partial' if counts['unknown'] else 'complete')
        if applicable:
            active_weight += Decimal(str(dim['weight']))
            weighted_total += candidate*Decimal(str(dim['weight']))
        reviewed_total += reviewed
        dimensions.append({'id':dim['id'],'name':dim['name'],'weight':dim['weight'],'status':status,
                           'score':plain(candidate) if status=='complete' and d['baseline_ready'] else None,
                           'provisional_score':plain(candidate) if status in {'partial','complete'} else None,
                           'raw_deduction':plain(raw_penalty),'deducted':plain(deduction),
                           'applicable':applicable,'reviewed':reviewed,'unknown':counts['unknown'],'na':counts['na'],
                           'coverage':round(100*reviewed/applicable,2) if applicable else None,
                           'finding_ids':[f['id'] for f in relevant]})
    applicable_count = sum(x['applicable'] for x in dimensions)
    unknown_count = sum(x['unknown'] for x in dimensions)
    scoreable = d['baseline_ready'] and active_weight>0 and (reviewed_total>0 or any(x['deducted'] for x in dimensions))
    status = 'complete' if scoreable and not unknown_count else 'partial' if scoreable else 'unscored'
    raw = weighted_total/active_weight if scoreable else None
    blockers = [f['id'] for f in findings if f['status']=='confirmed' and f['blocker']]
    cap = Decimal(str(policy['blocker_cap'])) if blockers else None
    result = min(raw,cap) if raw is not None and cap is not None else raw
    # Grade uses the underlying Decimal, never a rounded display that crosses a boundary.
    if status=='complete':
        grade = '良好' if result >= policy['grades']['good'] else '合格' if result>=policy['grades']['pass'] else '不合格'
    else:
        grade = '不合格（确认阻断；审查未完成）' if blockers else '暂不能判定'
    for dim in dimensions:
        effective = Decimal(str(dim['weight']))/active_weight if active_weight and dim['applicable'] else Decimal(0)
        dim['effective_weight']=rounded(effective*100)
        dim['weighted_deduction']=rounded(Decimal(str(dim['deducted']))*effective)
        dim['contribution']=rounded(Decimal(str(dim['provisional_score']))*effective) if dim['provisional_score'] is not None else None
    deductions = []
    for f in findings:
        points = Decimal(str(policy['severity_deductions'][f['severity']])) if f['status']=='confirmed' else Decimal(0)
        dim = next(x for x in dimensions if x['id']==f['dimension_id'])
        impact = points*Decimal(str(dim['weight']))/active_weight if active_weight else Decimal(0)
        deductions.append({'id':f['id'],'points':plain(points),'weighted_impact_before_cap':rounded(impact),
                           'policy_basis':f"{f['severity']}: {policy['severity_deductions'][f['severity']]} / 100"})
    total_deduction = sum((Decimal(str(x['deducted']))*Decimal(str(x['weight'])) for x in dimensions if x['applicable']),Decimal(0))/active_weight if active_weight else Decimal(0)
    score_display = lambda value: plain(value.quantize(Decimal('0.01'), rounding=ROUND_FLOOR))
    d['summary']={'status':status,'score':score_display(result) if status=='complete' else None,
                  'provisional_upper':rounded(result) if status=='partial' else None,
                  'raw_score':score_display(raw) if raw is not None else None,'grade':grade,
                  'blocker_cap':plain(cap) if cap is not None else None,
                  'confirmed_blockers':blockers,'critical_unknowns':critical_unknowns,
                  'applicable_criteria':applicable_count,'reviewed_criteria':reviewed_total,
                  'unknown_count':unknown_count,'na_count':sum(x['na'] for x in dimensions),
                  'coverage':round(100*reviewed_total/applicable_count,2) if applicable_count else None,
                  'weighted_deduction':rounded(total_deduction),
                  'excluded_dimensions':[x['id'] for x in dimensions if not x['applicable']],
                  'active_weight':plain(active_weight),'dimensions':dimensions,'finding_deductions':deductions,
                  'rubric_sha256':digest(rubric),'policy_sha256':digest(policy),
                  'rule_snapshot':{'rubric':rubric,'policy':policy}}
    return d


def render(data: dict[str, Any], rubric: dict[str, Any] | None = None,
           policy: dict[str, Any] | None = None) -> str:
    normalized = calculate(data,rubric,policy)
    payload = json.dumps(normalized,ensure_ascii=False,indent=2,allow_nan=False)
    payload = (payload.replace('&','\\u0026').replace('<','\\u003c').replace('>','\\u003e')
               .replace('\u2028','\\u2028').replace('\u2029','\\u2029'))
    template = (ASSETS/'report.template.html').read_text(encoding='utf-8')
    require(template.count('__AUDIT_DATA_JSON__')==1, 'Template needs exactly one data marker.')
    scripts = re.findall(r'<script>(.*?)</script>', template, flags=re.S)
    require(len(scripts) == 1, 'Template must contain one executable inline script.')
    script_hash = base64.b64encode(hashlib.sha256(scripts[0].encode('utf-8')).digest()).decode('ascii')
    template, replacements = re.subn(r"'sha256-[A-Za-z0-9+/=]+'", "'sha256-"+script_hash+"'", template, count=1)
    require(replacements == 1, 'Template must contain a pinned script CSP hash.')
    return template.replace('__AUDIT_DATA_JSON__',payload)


def blank(project: str, snapshot: str='待确认', rubric: dict[str,Any] | None=None,
          policy: dict[str,Any] | None=None) -> dict[str,Any]:
    rubric = get_rubric() if rubric is None else rubric
    policy = get_policy() if policy is None else policy
    validate_rules(rubric,policy)
    require(nonempty(project),'Project must not be empty.')
    return {'schema_version':'2.0','rubric_version':rubric['rubric_version'],'policy_version':policy['policy_version'],
            'baseline_ready':False,'meta':{'title':'软件工程质量与上线审查报告','project':project,'version':'draft-1',
            'reviewed_at':datetime.now(timezone.utc).isoformat(timespec='seconds'),'snapshot':snapshot,
            'environment':'待确认','is_demo':False,'template_version':'3.0'},
            'conclusion':'尚未执行审查。基线、检查结论和证据均待建立，不构成上线判断。',
            'baseline':{'scope':['既有功能范围待确认，不默认增加功能。'],
                        'conditions':[{'id':'C-001','label':'使用条件','value':'待确认','status':'待确认','source':'尚未提供'}],
                        'key_flows':[{'id':'F-001','name':'核心业务链待梳理','expected':'待确认','status':'未验证','evidence_ids':[]}],
                        'limitations':['初始化草稿：没有执行代码审查或运行测试，不包含已确认缺陷。']},
            'checks':[{'id':c['id'],'criterion':c['id'],'status':'unknown','reason':'尚未检查，需取得适用证据。',
                       'scope_refs':['C-001'],'evidence_ids':[],'finding_ids':[]}
                      for dim in rubric['dimensions'] for c in dim['criteria']],
            'findings':[],'evidence':[]}


def generate_schema(rubric:dict[str,Any],policy:dict[str,Any])->dict[str,Any]:
    """Editor schema is generated from the same rule IDs used by the runtime."""
    validate_rules(rubric,policy)
    text={'type':'string','minLength':1}
    ident={'type':'string','pattern':r'^[A-Za-z0-9][A-Za-z0-9_.-]{0,79}$'}
    def array(item:dict[str,Any]=text, minimum:int=0)->dict[str,Any]:
        return {'type':'array','items':item,'uniqueItems':True,'minItems':minimum}
    def obj(props:dict[str,Any],optional:tuple[str,...]=(),extra:bool=False)->dict[str,Any]:
        return {'type':'object','properties':props,'required':[x for x in props if x not in optional],
                'additionalProperties':extra}
    criterion={'enum':[c['id'] for d in rubric['dimensions'] for c in d['criteria']]}
    dimension={'enum':[d['id'] for d in rubric['dimensions']]}
    check=obj({'id':ident,'criterion':criterion,'status':{'enum':['pass','fail','unknown','na']},
               'reason':text,'scope_refs':array(text,1),'evidence_ids':array(),'finding_ids':array(),
               'critical':{'type':'boolean'},'requirement':text},('critical','requirement'))
    finding=obj({'id':ident,'title':text,'type':{'enum':['vulnerability','bug','architecture','organization','verification']},
                 'dimension_id':dimension,'status':{'enum':['confirmed','unknown']},
                 'severity':{'enum':list(policy['severity_deductions'])},'severity_reason':text,
                 'blocker':{'type':'boolean'},'blocker_rule_id':{'enum':[None]+[b['id'] for b in policy['blocker_rules']]},
                 'blocker_reason':{'type':'string'},'cause':text,'trigger':text,'impact':text,'scope':array(text,1),
                 'locations':array(text,1),'evidence_ids':array(),'suggestion':text,'acceptance':text,
                 'reproduction':array(),'priority':text,'root_cause_key':text,'criterion_ids':array(criterion,1)},
                ('reproduction','priority','blocker_rule_id','blocker_reason'))
    props={'schema_version':{'const':'2.0'},'rubric_version':{'const':rubric['rubric_version']},
           'policy_version':{'const':policy['policy_version']},'baseline_ready':{'type':'boolean'},
           'meta':obj({**{k:text for k in ('title','project','version','reviewed_at','snapshot','environment')},
                       'is_demo':{'type':'boolean'},'template_version':text},('template_version',),True),
           'conclusion':text,
           'baseline':obj({'scope':array(),'limitations':array(text,1),
                           'conditions':array(obj({'id':ident,**{k:text for k in ('label','value','status','source')}})),
                           'key_flows':array(obj({'id':ident,**{k:text for k in ('name','expected','status')},'evidence_ids':array()}))}),
           'checks':array(check,1),'findings':array(finding),
           'evidence':array(obj({'id':ident,**{k:text for k in ('method','location','expected','observed','limitations')},'is_demo':{'type':'boolean'}})),
           'summary':{'type':'object','description':'Derived; discarded and recalculated by the runtime.'}}
    return {'$schema':'https://json-schema.org/draft/2020-12/schema',
            'title':'Production Readiness Audit v2.0 — generated, do not hand edit',
            'description':'Editor structure only; runtime also checks rule coverage, evidence, root causes and blockers.',
            **obj(props,('summary',))}


def generated_files(rubric:dict[str,Any],policy:dict[str,Any])->dict[Path,str]:
    j=lambda x:json.dumps(x,ensure_ascii=False,indent=2)+'\n'
    draft=blank('待审查项目',rubric=rubric,policy=policy)
    draft['meta']['reviewed_at']='待审查（初始化模板）'
    lines=['# 技术指标目录（自动生成）','',f"量表 {rubric['rubric_version']} · 策略 {policy['policy_version']}",
           '', '由 assets/scoring-rubric.json 生成。指标没有分值，新增不调整其他指标。',
           '修改源文件后运行 `python scripts/review.py sync-rules`；不要手工编辑本文件。','']
    for dim in rubric['dimensions']:
        lines.extend([f"## {dim['id']} · {dim['name']}（维度权重 {dim['weight']}%）",''])
        for c in dim['criteria']:
            lines.extend([f"### {c['id']} · {c['title']}",'',
                          f"关键验证：{'是' if c['critical_review'] else '否'}（不自动等同于失败即阻断）。",''])
            for k,label in [('applicability','适用条件'),('requirement','技术要求'),('proof','验证与证据'),
                            ('pass_condition','通过条件'),('fail_condition','失败条件'),('deduplication','去重')]:
                lines.append(f"**{label}**：{c[k]}\n")
    return {ASSETS/'audit.schema.json':j(generate_schema(rubric,policy)),
            ASSETS/'audit.blank.json':j(draft),SKILL/'references/diagnostic-checks.md':'\n'.join(lines)+'\n'}


def sync_rules(check:bool=False)->list[str]:
    generated=generated_files(get_rubric(),get_policy())
    stale=[str(p.relative_to(SKILL)) for p,t in generated.items() if not p.exists() or p.read_text(encoding='utf-8')!=t]
    if check:
        require(not stale,'Generated files are stale; run sync-rules: '+', '.join(stale))
    else:
        for path,text in generated.items():
            save(path,text,force=True)
    return stale


def ensure_output(path:Path,force:bool,input_path:Path|None=None)->None:
    require(input_path is None or path.resolve()!=input_path.resolve(),'Output must not overwrite the input.')
    require(not path.is_symlink(),'Refusing to write through a symbolic link.')
    require(force or not path.exists(),f'Output exists: {path}; choose another name or explicitly use --force.')
    require(not path.exists() or path.is_file(),f'Output is not a regular file: {path}')


def save(path:Path,content:str,force:bool=False,input_path:Path|None=None)->None:
    ensure_output(path,force,input_path)
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w' if force else 'x',encoding='utf-8',newline='\n') as stream:
        stream.write(content)
        if not content.endswith('\n'):
            stream.write('\n')


def main(argv:list[str]|None=None)->int:
    for stream in (sys.stdout,sys.stderr):
        if hasattr(stream,'reconfigure'):
            stream.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser(description='Validate evidence, apply dimension deductions and render offline HTML. No scanning.')
    parser.add_argument('--version',action='version',version=VERSION)
    commands=parser.add_subparsers(dest='command',required=True)
    sync=commands.add_parser('sync-rules',help='Generate schema, blank input and criterion documentation.')
    sync.add_argument('--check',action='store_true',help='Fail if generated files are stale; do not write.')
    for command in ('init','validate','score','render'):
        p=commands.add_parser(command)
        p.add_argument('--rubric',type=Path,help='Optional frozen rubric JSON; default is bundled rules.')
        p.add_argument('--policy',type=Path,help='Optional frozen scoring policy JSON.')
        if command=='init':
            p.add_argument('--project',required=True)
            p.add_argument('--snapshot',default='待确认')
        else:
            p.add_argument('--input',type=Path,required=True)
        if command in ('init','render'):
            p.add_argument('--output',type=Path,required=True)
            p.add_argument('--force',action='store_true')
        if command=='render':
            p.add_argument('--json-output',type=Path)
    args=parser.parse_args(argv)
    try:
        if args.command=='sync-rules':
            stale=sync_rules(args.check)
            print('Generated rule files are synchronized.' if args.check else f'Synchronized 3 generated files ({len(stale)} changed).')
            return 0
        rubric=read_json(args.rubric) if args.rubric else get_rubric()
        policy=read_json(args.policy) if args.policy else get_policy()
        if args.command=='init':
            data=blank(args.project,args.snapshot,rubric,policy)
            save(args.output,json.dumps(data,ensure_ascii=False,indent=2),args.force)
            print(f'Created unreviewed draft: {args.output}')
            return 0
        data=read_json(args.input)
        calculated=calculate(data,rubric,policy)
        if args.command=='validate':
            print(f"Valid: {len(calculated['checks'])} checks; evidence truth still requires review.")
        elif args.command=='score':
            print(json.dumps(calculated['summary'],ensure_ascii=False,indent=2))
        else:
            require(args.output.suffix.lower()=='.html','Report output must have .html extension.')
            ensure_output(args.output,args.force,args.input)
            if args.json_output:
                require(args.json_output.resolve()!=args.output.resolve(),'HTML and JSON outputs must differ.')
                require(args.json_output.suffix.lower()=='.json','JSON output must have .json extension.')
                ensure_output(args.json_output,args.force,args.input)
            save(args.output,render(data,rubric,policy),args.force,args.input)
            if args.json_output:
                save(args.json_output,json.dumps(calculated,ensure_ascii=False,indent=2),args.force,args.input)
            s=calculated['summary']
            print(f"Wrote {args.output} | {s['status']} | score={s['score']} | provisional upper={s['provisional_upper']} | coverage={s['coverage']}%")
        return 0
    except (AuditError,OSError,RecursionError,TypeError,KeyError) as exc:
        print(f'Error: {exc}',file=sys.stderr)
        return 2


if __name__=='__main__':
    raise SystemExit(main())
