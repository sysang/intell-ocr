"""Record Director communication, authority, and stop observations; never send or stop a run."""
import re
from urllib.parse import unquote

import consultations
import hub_publication
import knowledge
from evidence import TASK_ID, attempt_open, digest, file_sha, ident, require, text, verify_artifacts

MESSAGE = 'record-director-message'
DELIVERY = 'record-director-delivery'
REPLY = 'record-director-reply'
FILE = 'file-director-record'
STOP = 'request-director-stop'
STOPPED = 'record-director-stop-reconciliation'
ACTIONS = (MESSAGE, DELIVERY, REPLY, FILE, STOP, STOPPED)
BRIEF = 'director-brief.md'
OUTCOMES = ('resume-within-authority', 'narrow', 'authorize-resources', 'stop')
TRIGGERS = ('charter', 'authority', 'resources', 'essential-information', 'exhausted-recovery')


def entries(state):
    return [row for row in state['decisions'] if 'opened' in row]


def get(state, key):
    row = next((row for row in entries(state) if row['id'] == key), None)
    require(row is not None, 'unknown managed Director decision ID')
    return row


def receipt(state, row, field):
    return state['operations'][row[field]] if field in row else None


def request(state, row):
    return receipt(state, row, 'opened')['message']


def outcome(state, row):
    reply = receipt(state, row, 'authorization')
    return request(state, row)['options'][reply['reply']['option']]['outcome'] if reply else None


def delivery(state, row):
    observed = receipt(state, row, 'delivery')
    return observed['delivery']['status'] if observed else request(state, row).get('delivery')


def content_tip(row):
    # Filing and status are derived from the immutable communication receipts.
    return digest({k: row[k] for k in ('id', 'opened', 'delivery', 'latest_reply', 'authorization', 'superseded_by') if k in row})


def marker(row):
    return f"<!-- director-record {row['id']} {content_tip(row)} -->"


def path_for(key):
    return f'decisions/{key}.md'


def scope_shape(value):
    require(isinstance(value, dict), 'provide an exact Director decision scope')
    if value.get('kind') == 'project':
        require(set(value) == {'kind'}, 'invalid project scope')
    else:
        ids = value.get('task_ids')
        require(set(value) == {'kind', 'task_ids'} and value['kind'] == 'tasks' and isinstance(ids, list) and ids and
                all(isinstance(key, str) and TASK_ID.fullmatch(key) for key in ids) and ids == sorted(set(ids)),
                'task scope needs sorted unique exact Beads task IDs')


def observe(root, artifacts):
    verify_artifacts(root, artifacts)
    require(all(not (root / p).resolve().is_relative_to(root / knowledge.HUB) and
                not (root / p).resolve().is_relative_to(root / hub_publication.STAGING) and
                (root / p).resolve() != root / 'project-state.json' for p in artifacts),
            'pin independent communication/observation files outside the hub, staging, and live ledger')


def message(state, p, root, op_id):
    common = {'id', 'tag', 'delivery', 'artifacts'}
    require(p.get('delivery') in ('sent', 'pending'), 'record observed delivery or explicitly pending filing/delivery')
    observe(root, p.get('artifacts'))
    if p.get('tag') == 'FYI':
        require(set(p) == common | {'summary', 'next_step'} and all(text(p[k]) for k in ('summary', 'next_step')),
                'FYI must record the incident or change and the Lead-owned next step')
        row = {'id': p['id'], 'tag': p['tag'], 'status': 'closed', 'opened': op_id}
    else:
        required = common | {'trigger', 'scope', 'ask', 'why_now', 'options', 'recommendation', 'without_reply'}
        require(p.get('tag') == 'DECISION-REQUIRED' and required <= p.keys() <= required | {'deadline', 'supersedes'} and
                p['trigger'] in TRIGGERS and all(text(p[k]) for k in ('ask', 'why_now', 'without_reply')) and
                ('deadline' not in p or text(p['deadline'])), 'incomplete Director decision request')
        scope_shape(p['scope'])
        require(p['trigger'] not in ('resources', 'charter') or p['scope']['kind'] == 'project',
                'resource and charter authorization are project-wide')
        options = p['options']
        require(isinstance(options, dict) and options and all(ident(k) and isinstance(o, dict) and
                set(o) == {'consequence', 'outcome'} and text(o['consequence']) and o['outcome'] in OUTCOMES
                for k, o in options.items()), 'give named options with consequences and explicit outcomes')
        require(p['scope']['kind'] == 'project' or all(o['outcome'] not in ('stop', 'authorize-resources') for o in options.values()),
                'project stop and additional resources need project-wide authority')
        require(all((o['outcome'] != 'resume-within-authority' if p['trigger'] == 'resources' else
                     o['outcome'] != 'authorize-resources') for o in options.values()),
                'extra resources require a resource decision; resource exhaustion needs narrowing, more resources, or a stop')
        recommendation = p['recommendation']
        require(isinstance(recommendation, dict) and set(recommendation) == {'option', 'basis', 'change_if'} and
                ident(recommendation['option']) and recommendation['option'] in options and
                text(recommendation['basis']) and text(recommendation['change_if']), 'record a recommendation and what would change it')
        row = {'id': p['id'], 'tag': p['tag'], 'status': 'open', 'opened': op_id}
        if 'supersedes' in p:
            old = get(state, p['supersedes'])
            prior = request(state, old)
            require(old['status'] == 'open' and not outcome(state, old) and prior.get('scope') == p['scope'] and
                    prior.get('trigger') == p['trigger'], 'supersession cannot change scope, authority boundary, or an authorized decision')
            old.update(status='superseded', superseded_by=p['id'])
        if p['scope']['kind'] == 'project' and state['lifecycle']['status'] != 'hold':
            state['lifecycle'].update(status='hold', hold_reason=f"Director decision required: {p['id']}")
    state['decisions'].append(row)
    return {'record_id': p['id'], 'message': p}


def matches_link(index, target):
    for value in re.findall(r'^\s*[-*+]\s+\[[^\]]+\]\(([^)]+)\)', index, re.M):
        if unquote(value.split('#', 1)[0]).removeprefix('./') == target:
            return True
    return False


def brief_marker(state):
    lc = state['lifecycle']
    context = {k: lc.get(k) for k in ('stage', 'status', 'outer_cycle', 'plan_version', 'hold_reason')}
    basis = [context, state['objectives'], state['progress_verdicts'], state['blockers'],
             [[content_tip(row), row.get('stop_reconciled')] for row in entries(state)]]
    return f'<!-- director-brief {digest(basis)} -->'


def require_brief(state, root):
    hub = root / knowledge.HUB
    brief, index = hub / BRIEF, hub / 'index.md'
    require(all(path.is_file() and path.resolve() == path for path in (brief, index)), 'publish the current standing Director brief')
    require(brief_marker(state) in brief.read_text(encoding='utf-8').splitlines(), 'standing Director brief is stale')
    require(matches_link(index.read_text(encoding='utf-8'), BRIEF), 'index must link the standing Director brief')


def indexed_files(root, row):
    hub = root / knowledge.HUB
    relative = path_for(row['id'])
    record, brief, index = hub / relative, hub / BRIEF, hub / 'index.md'
    require(all(path.is_file() and path.resolve() == path for path in (record, brief, index)),
            'Director filing requires the decision, standing brief, and root index')
    require(marker(row) in record.read_text(encoding='utf-8').splitlines(), 'Director filing does not match the current record version')
    links = index.read_text(encoding='utf-8')
    require(matches_link(links, relative) and matches_link(links, BRIEF), 'root index must link the exact Director record and standing brief')
    require(matches_link(brief.read_text(encoding='utf-8'), relative), 'standing brief must link the exact Director record')
    return file_sha(record)


def require_filed(state, row, root):
    filed = receipt(state, row, 'filing')
    require(filed and filed['content_tip'] == content_tip(row), f"Director record {row['id']} has unfiled changes")
    require(filed['record_sha256'] == indexed_files(root, row), f"Director record {row['id']} changed after filing")
    for report, field in ((request(state, row), 'artifacts'),
                          ((receipt(state, row, 'authorization') or {}).get('reply'), 'artifacts'),
                          ((receipt(state, row, 'delivery') or {}).get('delivery'), 'artifacts')):
        if report and field in report:
            observe(root, report[field])


def intersects(scope, *, task=None, gate=False, project=False):
    return scope['kind'] == 'project' or (not project and (gate or task in scope['task_ids']))


def require_work(state, root, *, task=None, gate=False, project=False, assessment_id=None, dispatch=False):
    for row in entries(state):
        if row['tag'] != 'DECISION-REQUIRED' or row['status'] == 'superseded':
            continue
        scope = request(state, row)['scope']
        if not intersects(scope, task=task, gate=gate, project=project):
            continue
        require(row['status'] == 'closed' and outcome(state, row) != 'stop', f"Director decision {row['id']} blocks this work")
        require_filed(state, row, root)
        if dispatch and scope['kind'] == 'tasks':
            assessment = state['operations'].get(assessment_id, {}) if ident(assessment_id) else {}
            require(assessment.get('revision', 0) > receipt(state, row, 'filing')['closed_revision'],
                    f"reassess the affected work after Director authorization {row['id']}")


def review_authority_basis(state):
    return [[row['status'], content_tip(row)] for row in entries(state) if row['tag'] == 'DECISION-REQUIRED']


def resources_to_reconcile(state):
    settled = {key for r in state['operations'].values() if r['group'] == 'lifecycle' and r['action'] == 'resolve-hold'
               for key in r.get('director_resume_ids', [])}
    return sorted(r['id'] for r in entries(state) if r['status'] != 'superseded' and
                  request(state, r).get('trigger') == 'resources' and r['id'] not in settled)


def require_resume(state, root, p):
    require_work(state, root, project=True)
    # Authorization is not evidence of a quota or of an applied narrowing.
    if outstanding := resources_to_reconcile(state):
        require(p.get('resource_decisions') == outstanding, 'name the filed resource decisions being applied before resuming')
        observe(root, p.get('reconciliation_artifacts'))
        return {'director_resume_ids': outstanding, 'reconciliation_artifacts': p['reconciliation_artifacts']}
    return {}


def filing_scope(state, p):
    paths = p.get('paths')
    permitted = {'index.md', BRIEF} | {path_for(r['id']) for r in entries(state)}
    require(entries(state) and isinstance(paths, list) and all(isinstance(path, str) and path in permitted for path in paths),
            'while on HOLD, only stage Director records, their index, and standing brief')


def unresolved(state):
    return {'assignments': [a['id'] for a in state['execution']['attempts'].values() if attempt_open(a)],
            'advisor_calls': sorted(consultations.attempts(state).keys() - consultations.settlements(state).keys()),
            'okf_publication': hub_publication.pending(state) is not None,
            'inner_attempt': 'pending_inner_attempt' in state['lifecycle']}


def view(state):
    return {'records': [{**r, 'path': f"{knowledge.HUB}/{path_for(r['id'])}", 'marker': marker(r),
                         'delivery_status': delivery(state, r), 'outcome': outcome(state, r),
                         'filing_matches_tip': bool(receipt(state, r, 'filing') and receipt(state, r, 'filing')['content_tip'] == content_tip(r))}
                        for r in entries(state)], 'unresolved': unresolved(state),
            'brief_marker': brief_marker(state), 'resources_to_reconcile': resources_to_reconcile(state)}


def advance(state, action, p, root, op_id):
    key = p.get('id')
    require(ident(key) and key not in ('index', 'log'), 'valid Director record ID required')
    if action in (MESSAGE, STOP):
        require(not any(row['id'] == key for row in state['decisions']), 'Director record ID already exists')
        if action == MESSAGE:
            return message(state, p, root, op_id)
        require(set(p) == {'id', 'reason'} and text(p['reason']), 'record the immediate stop reason')
        state['lifecycle'].update(status='hold', hold_reason=f'Director stop requested: {key}')
        state['decisions'].append({'id': key, 'tag': 'DECISION-REQUIRED', 'status': 'open', 'opened': op_id})
        return {'record_id': key, 'message': {**p, 'trigger': 'stop', 'scope': {'kind': 'project'},
                                            'options': {'stop': {'outcome': 'stop'}}}}
    row = get(state, key)
    req = request(state, row)
    if action == DELIVERY:
        require(set(p) == {'id', 'status', 'artifacts'} and p['status'] in ('sent', 'pending') and
                row['status'] != 'superseded' and req.get('trigger') != 'stop', 'invalid Director delivery observation')
        observe(root, p['artifacts'])
        require(delivery(state, row) != 'sent' or p['status'] == 'sent', 'do not downgrade observed delivery')
        row['delivery'] = op_id
        return {'record_id': key, 'delivery': p}
    if action == REPLY:
        kind = p.get('classification')
        base = {'id', 'classification', 'artifacts'}
        require(row['tag'] == 'DECISION-REQUIRED' and row['status'] == 'open' and 'authorization' not in row,
                'reply must target an open decision without a settled authorization')
        observe(root, p.get('artifacts'))
        if kind == 'authorization':
            require(set(p) == base | {'option', 'readback'} and ident(p['option']) and p['option'] in req['options'] and
                    text(p['readback']) and (req.get('trigger') == 'stop' or delivery(state, row) == 'sent'),
                    'authorization needs an exact option, observed delivery, and readback of effects')
            if req['options'][p['option']]['outcome'] == 'stop' and req['scope']['kind'] == 'project':
                if state['lifecycle']['status'] != 'suspended':
                    state['lifecycle'].update(status='hold', hold_reason=f'Director stop authorized: {key}')
            row['authorization'] = op_id
        else:
            require(kind in ('ambiguous', 'question', 'preference') and set(p) == base | {'next_step'} and text(p['next_step']),
                    'non-authorizing reply needs a concrete next step (a focused question if ambiguous)')
        row['latest_reply'] = op_id
        return {'record_id': key, 'reply': p}
    if action == FILE:
        require(set(p) == {'id', 'publication_id'}, 'filing needs the record and exact publication ID')
        hub_publication.require_idle(state)
        fingerprint = knowledge.hub_fingerprint(root)
        publication = knowledge.require_publication(state, fingerprint, p['publication_id'])
        sha = indexed_files(root, row)
        require_brief(state, root)
        require(knowledge.hub_fingerprint(root) == fingerprint, 'hub changed while checking Director filing')
        previous = receipt(state, row, 'filing')
        closed_revision = previous.get('closed_revision') if previous else None
        if row['status'] == 'open' and row.get('authorization'):
            if req.get('supersedes'):
                require_filed(state, get(state, req['supersedes']), root)
            if 'artifacts' in req:
                observe(root, req['artifacts'])
            observe(root, receipt(state, row, 'authorization')['reply']['artifacts'])
            if row.get('delivery'):
                observe(root, receipt(state, row, 'delivery')['delivery']['artifacts'])
            row['status'] = 'closed'
            closed_revision = state['revision'] + 1
        row['filing'] = op_id
        return {'record_id': key, 'publication_id': publication['op_id'], 'record_sha256': sha,
                'content_tip': content_tip(row), 'closed_revision': closed_revision}
    require(action == STOPPED and set(p) == {'id', 'summary', 'artifacts'} and text(p['summary']) and
            outcome(state, row) == 'stop' and req['scope']['kind'] == 'project' and not row.get('stop_reconciled'),
            'stop reconciliation needs an authorized project stop and observed evidence')
    observe(root, p['artifacts'])
    require(not any(unresolved(state).values()), 'managed launches, writers, or effects are still unresolved; do not claim they stopped')
    row['stop_reconciled'] = op_id
    return {'record_id': key, 'observation': p}


def suspend(state, p, root):
    report = p.get('status_report')
    pins = p.get('artifacts')
    require(text(report) and isinstance(pins, dict) and report in pins, 'terminal suspension requires a pinned status report file')
    verify_artifacts(root, pins)
    key = p.get('director_decision')
    if key is not None:
        row = get(state, key)
        require(row['status'] == 'closed' and outcome(state, row) == 'stop' and request(state, row)['scope']['kind'] == 'project',
                'suspension requires a filed project stop authorization, not a pending request or a non-stop reply')
        require_filed(state, row, root)
        return {'director_decision': key, 'stop_reconciled': row.get('stop_reconciled'), 'report_artifacts': pins}
    require(not resources_to_reconcile(state) and not any(r['tag'] == 'DECISION-REQUIRED' and r['status'] != 'superseded' and
                    (request(state, r).get('trigger') == 'stop' or outcome(state, r) == 'stop') for r in entries(state)),
            'a Director resource or stop boundary cannot be converted without a filed human stop decision')
    return {'report_artifacts': pins}


def validate(state):
    rows = entries(state)
    require(len({row['id'] for row in state['decisions']}) == len(state['decisions']), 'duplicate Director record ID')
    bindings = {'opened': (MESSAGE, STOP), 'delivery': (DELIVERY,), 'latest_reply': (REPLY,),
                'authorization': (REPLY,), 'filing': (FILE,), 'stop_reconciled': (STOPPED,)}
    for row in rows:
        opened = receipt(state, row, 'opened')
        req = opened['message']
        require(req['id'] == row['id'] and (req.get('tag') == row['tag'] or
                (opened['action'] == STOP and row['tag'] == 'DECISION-REQUIRED' and req.get('trigger') == 'stop')),
                'invalid Director message binding')
        if row['tag'] == 'DECISION-REQUIRED':
            scope_shape(req['scope'])
            require(isinstance(req['options'], dict) and req['options'] and
                    all(option['outcome'] in OUTCOMES for option in req['options'].values()),
                    'invalid Director decision options')
        if req.get('trigger') != 'stop':
            require(delivery(state, row) in ('sent', 'pending'), 'invalid Director delivery state')
        for field, actions in bindings.items():
            if op := receipt(state, row, field):
                require(op['group'] == 'lifecycle' and op['action'] in actions and op['record_id'] == row['id'] and
                        op['revision'] >= opened['revision'], 'invalid Director receipt binding')
        if row.get('authorization'):
            require(receipt(state, row, 'authorization')['reply']['classification'] == 'authorization' and
                    row['authorization'] == row['latest_reply'] and outcome(state, row) in OUTCOMES,
                    'invalid Director authorization record')
        if row['status'] == 'closed' and row['tag'] == 'DECISION-REQUIRED':
            filing = receipt(state, row, 'filing')
            require(row.get('authorization') and filing and type(filing.get('closed_revision')) is int and
                    receipt(state, row, 'authorization')['revision'] < filing['closed_revision'] <= filing['revision'],
                    'closed Director decision lacks authorization or filing')
        if row.get('superseded_by'):
            replacement = get(state, row['superseded_by'])
            require(row['status'] == 'superseded' and request(state, replacement).get('supersedes') == row['id'],
                    'invalid Director supersession binding')
