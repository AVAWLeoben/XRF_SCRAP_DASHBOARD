"""Smoke-test the *live* Pyodide worker, not just prerendered HTML.

Run after build_site.py. Requires playwright and its Chromium installation.
The local URL includes a subdirectory to exercise GitHub project-page paths.
"""
import functools
import http.server
import json
import os
import threading
from pathlib import Path
from playwright.sync_api import sync_playwright

def main():
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(Path.cwd()))
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    errors = []
    try:
        with sync_playwright() as p:
            launch_options = {}
            if os.environ.get('BROWSER_EXECUTABLE'):
                launch_options['executable_path'] = os.environ['BROWSER_EXECUTABLE']
            browser = p.chromium.launch(**launch_options)
            page = browser.new_page(viewport={'width': 1440, 'height': 1000})
            page.on('pageerror', lambda e: errors.append(str(e)))
            with page.expect_worker(timeout=60000) as worker_info:
                page.goto(f'http://127.0.0.1:{server.server_port}/dist/index.html')
            worker = worker_info.value
            # Panel removes this only when the live Python document has rendered.
            page.wait_for_function("!document.body.classList.contains('pn-loading')", timeout=240000)
            code = '''
import json
assert len(x.DF_FULL) == 4731
assert len(x.CHEM_ELEMENTS) == 44
assert x.GOOD_PARTICLE_VALUE == 'Iron Particle'
assert len(tabs) == 6
assert abs(x.weighted_mean(x.DF_FULL.Cu, x.DF_FULL[x.GEWICHT_COL]) - 0.4986347309012205) < 1e-12
json.dumps({'pandas': pd.__version__, 'objects': len(x.DF_FULL), 'elements': len(x.CHEM_ELEMENTS)})
'''
            report = json.loads(worker.evaluate('(code) => self.pyodide.runPythonAsync(code)', code))
            # Exercise a real browser control and verify it reaches Python.
            page.locator('select').first.select_option(label='Iron Particle')
            page.wait_for_function("!document.body.classList.contains('pn-loading')")
            import time
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                value = worker.evaluate("self.pyodide.runPython('dist_particle.value')")
                if value == 'Iron Particle':
                    break
                page.wait_for_timeout(200)
            assert value == 'Iron Particle', value
            # Drive every tab and invoke its reactive callback in the worker.
            worker.evaluate('code => self.pyodide.runPythonAsync(code)', '''
cond_particle.value = 'All particles'
cond_group.value = 'Colour'
heat_mode.value = 'weighted_mean'
mass_scale.value = 'Linear'
morph_features.value = ['perimeter']
assert len(x.get_filtered_morphology_df('All particles', 'All')) == 5412
''')
            for i in range(6):
                worker.evaluate('code => self.pyodide.runPythonAsync(code)', f'tabs.active = {i}')
                page.wait_for_timeout(300)
            assert not errors, errors
            Path('artifacts').mkdir(exist_ok=True)
            Path('artifacts/browser_check.json').write_text(json.dumps(report, indent=2))
            print('Live browser test passed:', report)
            browser.close()
    finally:
        server.shutdown()

if __name__ == '__main__':
    main()
