"""Account for committed implementation batches in the project workspace."""
from pathlib import Path
import subprocess

from evidence import GIT_HASH, attempt_open, require

INTEGRATE = 'record-inner-integration'
INTERRUPT = 'record-no-change-interruption'
SETTLEMENTS = (INTEGRATE, INTERRUPT)


def git(root, *args):
    result = subprocess.run(['git', '--no-replace-objects', '--no-optional-locks', '-C', str(root),
                             '-c', 'core.fsmonitor=false', *args], capture_output=True, timeout=10)
    require(result.returncode == 0, f'cannot verify implementation checkpoint ({args[0]})')
    return result.stdout


def head(root):
    commit = git(root, 'rev-parse', '--verify', 'HEAD^{commit}').decode('ascii').strip()
    require(GIT_HASH.fullmatch(commit), 'expected full Git implementation checkpoint')
    return commit


def require_first_parent(root, base, checkpoint):
    if base != checkpoint:
        lineage = git(root, 'rev-list', '--first-parent', '--parents', f'{base}..{checkpoint}').splitlines()
        require(lineage and lineage[-1].split()[1:2] == [base.encode('ascii')],
                'checkpoint must descend from the recorded base on the workspace first-parent history')


def source_commits(root, base, checkpoint):
    return git(root, 'log', '--first-parent', '--full-history', '--reverse', '--no-show-signature', '--no-follow',
               '--format=%H', f'{base}..{checkpoint}', '--', 'src/').decode('ascii').splitlines()


def require_clean_source(root):
    require(not git(root, 'status', '--porcelain=v1', '-z', '--untracked-files=all', '--ignore-submodules=none',
                    '--', 'src/'), 'reconcile uncommitted implementation changes under src/ first')


def require_settled_writers(state, root):
    for a in state['execution']['attempts'].values():
        if a['workspace'] and attempt_open(a):
            workspace = Path(a['workspace'])
            require(not (workspace.is_relative_to(root) or root.is_relative_to(workspace)),
                    'reconcile the outstanding workspace assignment before accounting for the inner attempt')


def begin(state, root, op_id):
    lc = state['lifecycle']
    require('pending_inner_attempt' not in lc, 'reconcile the pending inner attempt before starting another')
    require_settled_writers(state, root)
    base = head(root)
    require_clean_source(root)
    previous = (r for r in state['operations'].values() if r['group'] == 'lifecycle' and r['action'] in SETTLEMENTS)
    latest = max(previous, key=lambda r: r['revision'], default=None)
    if latest:
        require_first_parent(root, latest['checkpoint'], base)
    require(head(root) == base, 'workspace HEAD changed while recording the attempt base')
    pending = {'start_op_id': op_id, 'base_revision': base}
    lc['pending_inner_attempt'] = pending
    return {**pending, 'cycle': lc['outer_cycle']}


def settle(state, action, payload, root):
    lc = state['lifecycle']
    pending = lc.get('pending_inner_attempt')
    require(lc['stage'] == 'IMPLEMENTING' and pending and payload.get('start_op_id') == pending['start_op_id'],
            'settlement must name the current pending inner attempt start operation')
    require_settled_writers(state, root)
    checkpoint = head(root)
    require(payload.get('checkpoint') == checkpoint, 'settlement checkpoint must be the full current Git HEAD hash')
    base = pending['base_revision']
    require_first_parent(root, base, checkpoint)
    commits = source_commits(root, base, checkpoint)
    result = {**pending, 'cycle': lc['outer_cycle'], 'checkpoint': checkpoint, 'integration_commits': commits}
    if action == INTERRUPT:
        require(not commits, 'implementation changes were integrated; record the integration instead')
        require_clean_source(root)
    else:
        require(commits, 'no committed implementation changes under src/; do not charge an inner attempt')
        lc['inner_attempt'] += 1
        result['charged_inner_attempt'] = lc['inner_attempt']
    require(head(root) == checkpoint, 'workspace HEAD changed during reconciliation; inspect before retrying')
    del lc['pending_inner_attempt']
    return result
