#!/usr/bin/env python3
"""Bootstrap and launch a single project in the main Pi session. No scheduler."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import sys

import consultations
import durable
from evidence import FIXED, file_sha, ident, require, text, texts, verify_artifacts

REPO = Path(__file__).resolve().parents[2]
LEAD = REPO / '.pi/agents/research-lead/agent.md'
TASK_TOOLS = REPO / '.pi/extensions/beads-tools/index.ts'
LEDGER_TOOLS = REPO / '.pi/extensions/research-ledger-tools/index.ts'
LEDGER_TOOL_FILES = [REPO / '.pi/extensions/research-ledger-tools' / name for name in
                     ('index.ts', 'canonical-json.ts', 'gate.ts', 'cli.ts', 'process.ts', 'project-files.ts', 'schemas.ts')]
READ = {'read', 'grep', 'find', 'ls', 'structured_output'}
ROLE_TOOL_CEILINGS = {
    'research-advisor': READ,
    'engineering-worker': READ | {'edit', 'write', 'bash', 'subagent', 'codemode'},
    'harness-architector': READ, 'backend-architector': READ, 'frontend-architector': READ,
    'okf-reader': READ | {'bash'}, 'okf-writer': READ | {'bash', 'edit', 'write'},
}


def project_path(name):
    require(re.fullmatch(r'[a-z][a-z0-9-]{0,63}', name), 'use a lowercase project slug')
    p = REPO / 'research-projects' / name
    require(p.resolve() == p, 'project path cannot be a symlink')
    return p


def executable(candidate):
    path = shutil.which(candidate)
    require(path, f'executable not found: {candidate}')
    # Keep the invocation path for package-manager shims whose basename matters.
    return str(Path(path).absolute())


def command(args, **kwargs):
    proc = subprocess.run(args, capture_output=True, text=True, timeout=25, **kwargs)
    require(proc.returncode == 0, f'{Path(args[0]).name} failed: {proc.stderr[-600:]}')
    return proc.stdout.strip()


def initialization(a):
    p = project_path(a.project)
    bd = executable(a.bd)
    require(re.match(r'^bd version 0\.49\.6(?: |$)', command([bd, '--version'])), 'requires Beads v0.49.6')
    charter_ref = 'change-and-progress-logs/charter/research-charter.md'
    require(text(a.question), 'a director question is required')
    state = durable.new_state(a.project, a.objective, a.outer_limit, a.inner_limit, charter_ref, a.stagnation_cycles)
    p.mkdir(parents=True, exist_ok=False)
    env = {k: os.environ[k] for k in ('HOME', 'PATH', 'USER', 'LANG') if k in os.environ}
    env.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL='/dev/null')
    database = p / '.beads/beads.db'
    prefix = a.project.replace('-', '')[:32]
    env['BEADS_DIR'] = str(database.parent)
    command([bd, '--db', str(database), '--no-daemon', '--no-auto-import', '--no-auto-flush', 'init',
             '--quiet', '--backend=sqlite', f'--prefix={prefix}', '--skip-hooks', '--skip-merge-driver'], cwd=p, env=env)
    with database.open('rb') as f:
        require(f.read(16) == b'SQLite format 3\x00', 'Beads did not initialize the bound SQLite database')
    hub = p / 'change-and-progress-logs'
    for child in ('change-and-progress-logs/charter', 'change-and-progress-logs/planning', 'change-and-progress-logs/reviews',
                  'change-and-progress-logs/decisions', 'literature', 'src/methods', 'src/tests', 'src/evals',
                  'src/experiments', 'src/configs', 'reports', 'manifests', 'runtime'):
        (p / child).mkdir(parents=True)
    (hub / 'index.md').write_text('---\nokf_version: "0.2"\n---\n# Research governance\n\n'
        '- [Research charter](charter/research-charter.md)\n', encoding='utf-8')
    # `bd init` may seed generic tracker instructions. Research policy owns this project.
    (p / 'AGENTS.md').write_text('# Research project\n\nUse the Research Lead contract and root blueprint. '
                                'Beads is an operational backlog, not evidence authority.\n'
                                'Use the managed OKF publication protocol for hub Markdown; writers edit only their staging copy.\n',
                                encoding='utf-8')
    (p / charter_ref).write_text('---\ntype: research-charter\n---\n# Research charter\n\n## Director question\n\n' + a.question +
        '\n\n## Success criteria\n\n' + ''.join(f'- {o}\n' for o in a.objective) +
        '\n## Before protocol approval\n\nRecord scope, non-goals, resource caps, risks, and assumptions with the Director.\n', encoding='utf-8')
    durable.save(p / 'project-state.json', state)
    durable.save(p / 'research-config.json', {'id': a.project, 'bd': bd, 'python': sys.executable,
        'backend': 'sqlite', 'beadsVersion': '0.49.6', 'database': '.beads/beads.db'})
    return {'project': a.project, 'path': str(p), 'task_prefix': prefix, 'runtime_attested': False}


def binding(p):
    cfg = json.loads((p / 'research-config.json').read_text())
    require(cfg['id'] == p.name and cfg['database'] == '.beads/beads.db' and cfg['backend'] == 'sqlite' and
            cfg['beadsVersion'] == '0.49.6' and Path(cfg['bd']).is_absolute(), 'invalid project binding')
    db = p / cfg['database']
    require(db.resolve() == db and db.is_file(), 'bound SQLite database is missing or redirected')
    with sqlite3.connect(db.as_uri() + '?mode=ro', uri=True) as conn:
        require(conn.execute("select 1 from sqlite_master where type='table' and name='issues'").fetchone(),
                'bound SQLite database has no Beads issues table')
    return cfg


def fingerprint(paths):
    return {str(p): file_sha(p) for p in paths if p.is_file()}


def preflight(p, pi, subagents):
    cfg = binding(p)
    require(command([pi, '--version']).splitlines()[-1] == '1.6.0', 'requires Pi 1.6.0')
    require(re.match(r'^bd version 0\.49\.6(?: |$)', command([cfg['bd'], '--version'])), 'requires Beads v0.49.6')
    pkg = subagents.resolve(strict=True)
    require(json.loads((pkg / 'package.json').read_text())['version'] == '0.89.2', 'requires pi-subagents 0.89.2')
    files = [LEAD, TASK_TOOLS, TASK_TOOLS.with_name('adapter.ts'), *LEDGER_TOOL_FILES,
             REPO / '.pi/settings.json', pkg / 'package.json',
             pkg / 'index.js', Path(pi).resolve(), Path(cfg['bd']).resolve(), p / 'research-config.json',
             REPO / '.pi/agents/okf-reader/validate_result.py',
             REPO / '.pi/agents/okf-writer/validate_okf.py',
             *(Path(__file__).with_name(name) for name in ('research.py', 'ledger.py', 'durable.py', 'gates.py',
                                                         'knowledge.py', 'hub_publication.py', 'gate_artifacts.py', 'gate_checkpoints.py', 'director.py', 'snapshot_schema.py',
                                                         'project-state.schema.json', 'requirements.txt'))]
    definitions = {}
    for name in sorted(FIXED):
        source = REPO / '.pi/agents' / name / 'agent.md'
        require(f'\nname: {name}\n' in source.read_text().split('\n---', 1)[0], f'wrong definition: {name}')
        definitions[name] = str(source)
        files.append(source)
    require(all(x.is_file() for x in files), 'missing required runtime files')
    return {'pi': '1.6.0', 'pi_subagents': '0.89.2', 'beads': '0.49.6', 'backend': 'sqlite',
            'definitions': definitions, 'fingerprints': fingerprint(files), 'scope': 'installed files, not live resolution'}


def verify_smoke(p, current):
    record = json.loads((p / 'runtime/attestation.json').read_text())
    require(record.get('fingerprints') == current['fingerprints'] and text(record.get('operator')),
            'missing or stale operator attestation for this installation')
    roles = record.get('roles', {})
    require(set(roles) == FIXED, 'require exactly seven fixed-role smoke observations')
    seen = set()
    for name, r in roles.items():
        require(r.get('definition') == current['definitions'][name] and ident(r.get('run_id')) and r['run_id'] not in seen
                and text(r.get('requested_model')) and r['requested_model'] == r.get('resolved_model') and
                '/' in r['resolved_model'] and text(r.get('override_source')) and r.get('completed') is True and
                texts(r.get('effective_tools')) and r.get('fresh_context') is True, f'incomplete runtime evidence: {name}')
        observed = set(r['effective_tools'])
        require('read' in observed and observed <= ROLE_TOOL_CEILINGS[name], f'unapproved effective capability: {name}')
        seen.add(r['run_id'])
        verify_artifacts(p, r.get('artifacts'))
    for check in ('writer_confinement', 'worker_nested_edges', 'codemode_boundary', 'exact_restart_correlation',
                  'hard_cutoff_and_process_exit', 'fresh_context_and_models', 'okf_publication_recovery'):
        verify_artifacts(p, record.get('probes', {}).get(check))
    return {'operator': record['operator'], 'roles': roles, 'scope': 'operator observations with hash checks; not a sandbox'}


def exec_lead(project, pi, args, env):
    # Keep the lock across the exec into Pi; a second launcher cannot bind the
    # same project until this host exits. Never delete/recreate the lock inode.
    fd = os.open(project / '.research-lead.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError('another Research Lead session owns this project') from exc
        os.set_inheritable(fd, True)
        os.execve(pi, args, env)
    finally:
        os.close(fd)


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--pi', default='pi')
    cli.add_argument('--subagents', type=Path, default=Path.home() / '.pi/agent/npm/node_modules/pi-subagents')
    sub = cli.add_subparsers(dest='action', required=True)
    init = sub.add_parser('init')
    init.add_argument('project')
    init.add_argument('--question', required=True)
    init.add_argument('--objective', required=True, action='append')
    init.add_argument('--bd', default='bd')
    init.add_argument('--outer-limit', type=int, default=4)
    init.add_argument('--inner-limit', type=int, default=3)
    init.add_argument('--stagnation-cycles', type=int, default=2)
    for name in ('preflight', 'smoke-roster', 'lead'):
        parser = sub.add_parser(name)
        parser.add_argument('project')
        if name == 'lead':
            parser.add_argument('--model', required=True, help='exact operator-selected provider/model')
            parser.add_argument('--resume', help='explicit Pi session path/ID; state is still reloaded')
            parser.add_argument('--enable-delegation', action='store_true', help='requires current operator runtime evidence')
            parser.add_argument('--rpc', action='store_true', help='launch Pi in RPC mode')
    a = cli.parse_args()
    try:
        if a.action == 'init':
            print(json.dumps(initialization(a), indent=2))
            return 0
        p = project_path(a.project)
        pi = executable(a.pi)
        report = preflight(p, pi, a.subagents)
        if a.action == 'preflight':
            print(json.dumps(report, indent=2))
        elif a.action == 'smoke-roster':
            print(json.dumps(verify_smoke(p, report), indent=2))
        else:
            require('/' in a.model, 'select an exact provider/model')
            from ledger import check_invariants, load_state
            state = load_state(p / 'project-state.json')
            problems = check_invariants(state)
            require(not problems, '; '.join(problems))
            if a.enable_delegation:
                consultations.require_policy(state, p)
                verify_smoke(p, report)
            env = dict(os.environ, RESEARCH_LEAD_CONFIG=str(p / 'research-config.json'),
                       RESEARCH_LEAD_PID=str(os.getpid()), RESEARCH_DELEGATION='enabled' if a.enable_delegation else 'disabled')
            require(not env.get('PI_SUBAGENT_CHILD'), 'launcher is operator/Lead-only')
            os.chdir(REPO)
            args = [pi, '--model', a.model, '--append-system-prompt', str(LEAD), '--append-system-prompt',
                    f'Bound project: {p}. Delegation: {env["RESEARCH_DELEGATION"]}. Reload its project state before acting.',
                    '--extension', str(TASK_TOOLS), '--extension', str(LEDGER_TOOLS)]
            if not a.enable_delegation:
                args += ['--no-extensions', '--no-mcp', '--exclude-tools',
                         'subagent,subagents_enable,subagent_supervisor,bg_wait,contact_supervisor']
            if a.resume: args += ['--session', a.resume]
            if a.rpc: args += ['--mode', 'rpc']
            exec_lead(p, pi, args, env)
        return 0
    except (ValueError, OSError, KeyError, TypeError, AttributeError, sqlite3.Error, subprocess.TimeoutExpired) as exc:
        print(json.dumps({'refused': str(exc)}))
        return 1


if __name__ == '__main__':
    sys.exit(main())
