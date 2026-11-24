"""Credential-free smoke test of bootstrap and tool registration in pinned Pi, not agent runs."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[2]
NAMES = {'bd_create', 'bd_get', 'bd_query', 'bd_update', 'bd_close', 'bd_reopen',
         'bd_ready', 'bd_blocked', 'bd_dependency'}


class BootstrapTest(unittest.TestCase):
    @unittest.skipUnless(shutil.which('pi') and shutil.which('bd'), 'requires installed Pi and Beads')
    def test_bound_host_and_child_tool_registration(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp).resolve()
            cli = repo / 'tools/research-ops/research.py'
            shutil.copytree(REPO / 'tools/research-ops', cli.parent, ignore=shutil.ignore_patterns('__pycache__'))
            for path in ('.pi/extensions/beads-tools', '.pi/agents'):
                shutil.copytree(REPO / path, repo / path, ignore=shutil.ignore_patterns('__pycache__'))
            shutil.copy2(REPO / '.pi/settings.json', repo / '.pi/settings.json')
            env = {k: os.environ[k] for k in ('PATH', 'LANG') if k in os.environ}
            env.update(HOME=str(repo), PI_CODING_AGENT_DIR=str(repo / '.pi-home'))
            subprocess.run(['git', 'init', '-q'], cwd=repo, env=env, check=True)
            out = subprocess.run([sys.executable, '-B', cli, 'init', 'pilot', '--question', 'Fixture?',
                                  '--objective', 'Verify local wiring'], cwd=repo, env=env, check=True,
                                 text=True, capture_output=True, timeout=25)
            project = Path(json.loads(out.stdout)['path'])
            self.assertTrue((project / 'src/experiments').is_dir())
            state = json.loads((project / 'project-state.json').read_text())
            self.assertTrue((project / state['identity']['charter_ref']).is_file())
            self.assertFalse((repo / '.beads').exists())
            p = subprocess.run([sys.executable, '-B', cli.with_name('ledger.py'), 'validate',
                                project / 'project-state.json'], cwd=repo, env=env, check=True, text=True,
                               capture_output=True, timeout=10)
            self.assertTrue(json.loads(p.stdout)['valid'])
            installed = Path.home() / '.pi/agent/npm/node_modules/pi-subagents'
            if (installed / 'package.json').is_file():
                lead_cli = [sys.executable, '-B', cli, '--subagents', installed]
                opts = {'cwd': repo, 'env': env, 'text': True, 'capture_output': True, 'timeout': 30}
                preflight = subprocess.run([*lead_cli, 'preflight', 'pilot'], check=True, **opts)
                self.assertEqual(len(json.loads(preflight.stdout)['definitions']), 7)
                blocked = subprocess.run([*lead_cli, 'lead', 'pilot', '--model', 'unused/local-fixture',
                                          '--enable-delegation'], **opts)
                self.assertEqual(blocked.returncode, 1, blocked.stdout + blocked.stderr)
                self.assertIn('attestation.json', json.loads(blocked.stdout)['refused'])
            probe_file = repo / 'probe.json'
            probe = repo / 'probe.ts'
            probe.write_text('''import { writeFileSync } from 'node:fs';
export default function(pi) {
  pi.on('session_start', (_e, ctx) => {
    writeFileSync(process.env.PROBE_FILE, JSON.stringify({ tools: pi.getAllTools().filter(t => t.name.startsWith('bd_')),
      prompt: ctx.getSystemPrompt().includes('research-lead-host:v1') }));
  });
}
''')
            tool = repo / '.pi/extensions/beads-tools/index.ts'
            lead = repo / '.pi/agents/research-lead/agent.md'
            pi = shutil.which('pi')
            # Exec preserves the process ID, just like research.py lead. No model turn or remote call.
            starter = ('import os,sys; os.environ["RESEARCH_LEAD_PID"]=str(os.getpid()); '
                       'os.execv(sys.argv[1], sys.argv[1:])')
            for mode in ('host', 'spawned-child', 'unbound'):
                with self.subTest(mode=mode):
                    probe_file.unlink(missing_ok=True)
                    launch_env = dict(env, PROBE_FILE=str(probe_file))
                    if mode != 'unbound':
                        launch_env['RESEARCH_LEAD_CONFIG'] = str(project / 'research-config.json')
                    if mode == 'spawned-child':
                        launch_env['PI_SUBAGENT_CHILD'] = '1'
                    p = subprocess.run([sys.executable, '-c', starter, pi, '--no-extensions', '--no-mcp',
                                        '--no-session', '--mode', 'rpc', '--extension', str(tool), '--extension', str(probe),
                                        '--append-system-prompt', str(lead)],
                                       input='{"id":"test","type":"get_state"}\n', text=True, capture_output=True,
                                       cwd=repo, env=launch_env, timeout=20)
                    self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
                    self.assertTrue(probe_file.exists(), p.stdout + p.stderr)
                    report = json.loads(probe_file.read_text())
                    self.assertEqual({t['name'] for t in report['tools']}, NAMES if mode == 'host' else set(),
                                     p.stdout + p.stderr)
                    self.assertTrue(all(t['exposure'] == 'model-only' for t in report['tools']))
                    self.assertTrue(report['prompt'])
            # Inspect the same runtime callable registry used by codemode, not just the declaration metadata.
            sdk = Path(pi).resolve().parents[1] / 'index.js'
            sdk_probe = repo / 'sdk-probe.mjs'
            sdk_probe.write_text(f'''import {{createAgentSession, DefaultResourceLoader, SessionManager}} from {json.dumps(sdk.as_uri())};
process.env.RESEARCH_LEAD_PID = String(process.pid);
const loader = new DefaultResourceLoader({{cwd: process.cwd(), agentDir: process.env.PI_CODING_AGENT_DIR,
  noExtensions: true, additionalExtensionPaths: [{json.dumps(str(tool))}]}});
await loader.reload();
const {{session}} = await createAgentSession({{resourceLoader: loader, sessionManager: SessionManager.inMemory()}});
try {{
  console.log(JSON.stringify({{active: session.getActiveToolNames(), callable: session.getCallableToolNames()}}));
}} finally {{ session.dispose(); }}
''')
            p = subprocess.run(['node', sdk_probe], cwd=repo, text=True, capture_output=True, timeout=15,
                               env=dict(env, RESEARCH_LEAD_CONFIG=str(project / 'research-config.json')))
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            tools = json.loads(p.stdout.splitlines()[-1])
            self.assertTrue(NAMES <= set(tools['active']), tools)
            self.assertFalse(NAMES & set(tools['callable']), tools)


if __name__ == '__main__':
    unittest.main()
