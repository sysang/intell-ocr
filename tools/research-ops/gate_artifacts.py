"""Mechanical gate-package checks derived from Blueprint v1.4 §§5.2–5.6."""
import hashlib
import json
from pathlib import PurePosixPath

from evidence import ident, require, text, texts

ROLES = {
    'protocol': ('charter', 'literature-review', 'hypotheses', 'methodology', 'evaluation-plan', 'roadmap'),
    'readiness': ('dependency-lock', 'environment', 'dataset-manifest', 'experiment-config', 'test-sources',
                  'reproduction', 'implementation-notes'),
    'complete': ('config-snapshot', 'raw-results', 'execution-metadata', 'analysis-scripts', 'metrics-and-figures',
                 'ablations', 'failure-taxonomy', 'attempt-notes'),
    'diagnosis': ('diagnosis-note',),
    'cycle': ('hypothesis-assessment', 'threats-to-validity', 'limitation-diagnosis', 'progress-verdict', 'cycle-decision'),
    'report': ('report', 'claim-evidence-matrix', 'reproduction', 'references', 'final-manifest', 'verification'),
}


def canonical_path(name):
    if not text(name):
        return False
    path = PurePosixPath(name)
    return bool(path.parts and not path.is_absolute() and '..' not in path.parts and name == path.as_posix())


def check(manifest, phase, root):
    root = root.resolve()
    artifacts, roles = manifest['artifacts'], manifest.get('artifact_roles')
    required = set(ROLES[phase])
    require(isinstance(roles, dict), 'manifest must declare artifact_roles')
    missing = required - roles.keys()
    extra = roles.keys() - required
    require(not (missing or extra), f'artifact_roles for {phase}: missing {sorted(missing)}, unexpected {sorted(extra)}')
    for role, path in roles.items():
        require(canonical_path(path) and path in artifacts, f'{role} must name a project-relative file hashed in artifacts')
        actual = root / path
        require(actual.resolve() == actual and actual.stat().st_size > 0, f'{role} must name a nonempty, non-redirected file')
    require(len(set(roles.values())) == len(required), 'required artifact roles must name distinct files')

    if phase == 'diagnosis':
        info = manifest.get('diagnosis')
        require(isinstance(info, dict) and set(info) == {'reason', 'gaps', 'rationale'} and
                info['reason'] in ('attempt-budget-exhausted', 'requires-plan-change') and
                texts(info['gaps']) and info['gaps'] and text(info['rationale']),
                'diagnosis-only packages must say why full evaluation is unavailable and list material gaps')
    elif phase == 'cycle':
        cycle_decision(manifest, root)
    elif phase == 'report':
        report_evidence(manifest, root)


def role_json(manifest, role, root):
    def unique_fields(pairs):
        record = {}
        for key, value in pairs:
            require(key not in record, f'{role} repeats JSON field {key}')
            record[key] = value
        return record

    path = manifest['artifact_roles'][role]
    data = (root / path).read_bytes()
    require(hashlib.sha256(data).hexdigest() == manifest['artifacts'][path], f'artifact drift: {path}')
    record = json.loads(data.decode('utf-8'), object_pairs_hook=unique_fields)
    require(isinstance(record, dict), f'{role} must be a JSON object')
    return record


def cycle_decision(manifest, root):
    record = role_json(manifest, 'cycle-decision', root)
    route = manifest.get('proposed_route')
    require(route in ('replan', 'report', 'stop', 'hold') and record.get('proposed_route') == route and
            ident(record.get('id')) and type(record.get('cycle')) is int and record['cycle'] >= 1 and
            text(record.get('plan_version')) and text(record.get('rationale')),
            'cycle decision must identify the cycle, active plan and exact route proposal with a rationale')
    evidence = record.get('evidence_refs')
    own_path = manifest['artifact_roles']['cycle-decision']
    require(texts(evidence) and evidence and all(p in manifest['artifacts'] and p != own_path for p in evidence),
            'cycle decision must cite evidence hashed in the submission')
    require('selected_route' not in record, 'the reviewed cycle document is a proposal, not a resolved route')
    if route == 'replan':
        require(text(manifest.get('next_plan')) and manifest['next_plan'] == record.get('next_plan') and
                manifest['next_plan'] != record['plan_version'] and text(manifest.get('replan_rationale')) and
                manifest['replan_rationale'] == record.get('replan_rationale'), 'cycle replan proposal does not match the decision record')
    return record


def report_evidence(manifest, root):
    roles, artifacts = manifest['artifact_roles'], manifest['artifacts']
    final = role_json(manifest, 'final-manifest', root).get('artifacts')
    main_paths = {path for role, path in roles.items() if role not in ('verification', 'final-manifest')}
    require(isinstance(final, dict) and main_paths <= final.keys() and
            all(path in artifacts and pin == artifacts[path] and path not in (roles['verification'], roles['final-manifest'])
                for path, pin in final.items()), 'final artifact manifest must pin the report artifacts and cited evidence')
    verified = role_json(manifest, 'verification', root)
    expected = {p: artifacts[p] for p in main_paths | {roles['final-manifest']}}
    require(verified.get('artifacts') == expected and text(verified.get('verifier')) and text(verified.get('method')),
            'report verification must name a verifier, method and exact mandatory report artifact hashes')


def check_context(state, manifest, root):
    phase, lc = manifest['phase'], state['lifecycle']
    if phase == 'protocol':
        require(manifest['artifact_roles']['charter'] == state['identity']['charter_ref'],
                'protocol must pin the active project charter')
    elif phase == 'diagnosis' and manifest['diagnosis']['reason'] == 'attempt-budget-exhausted':
        require(lc['inner_attempt'] >= state['policy']['inner_limit'], 'diagnosis claims an unspent inner-attempt budget')
    elif phase == 'cycle':
        proposal = cycle_decision(manifest, root)
        require(proposal['cycle'] == lc['outer_cycle'] and proposal['plan_version'] == lc['plan_version'],
                'cycle decision targets a different cycle or plan')
