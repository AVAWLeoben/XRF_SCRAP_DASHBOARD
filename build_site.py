"""Build the complete static site; generated app is the Pages entry point."""
from pathlib import Path
from panel.io.convert import convert_app
import shutil
from image_assets import publish_images

if __name__ == '__main__':
    Path('dist').mkdir(exist_ok=True)
    publish_images('data/Object_Images', 'dist')
    convert_app('app.py', dest_path='dist', runtime='pyodide-worker',
                requirements=[line.strip() for line in Path('requirements-browser.txt').read_text().splitlines()
                              if line.strip() and not line.startswith('#')],
                resources=['xrf_core.py', 'theme.py', 'data/Dashboard_Daten_20.05.26_NORMALIZED.xlsx',
                               'data/objektgroessen_von_fotos.xlsx'],
                prerender=True, verbose=True)
    output = Path('dist')
    if not (output / 'app.html').is_file() or not (output / 'app.js').is_file():
        raise RuntimeError('Panel conversion did not produce the expected HTML and worker')
    shutil.copyfile('object_preview.js', output / 'object_preview.js')
    html = (output / 'app.html').read_text()
    html = html.replace('</body>', '<script src="./object_preview.js" defer></script>\n</body>')
    (output / 'app.html').write_text(html)
    (output / 'index.html').write_text(html)
    (output / '.nojekyll').touch()
