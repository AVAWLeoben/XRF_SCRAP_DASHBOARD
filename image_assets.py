"""Build public photo assets from BOX_OBJECTID filenames (no XRF mutation)."""
import json
from pathlib import Path
import re
import shutil
from urllib.parse import quote

PATTERN = re.compile(r'^\d+_(\d+)\.(jpg|jpeg|png|webp)$', re.IGNORECASE)

def publish_images(source, destination):
    source, destination = Path(source), Path(destination)
    images, ignored, selected = {}, [], []
    if source.exists():
        for path in sorted(source.iterdir()):
            if not path.is_file():
                continue
            match = PATTERN.fullmatch(path.name)
            if not match:
                ignored.append(path.name)
                continue
            key = str(int(match[1]))
            if key in images:
                raise ValueError(f'Duplicate photo for object {key}: {images[key]} and {path.name}')
            images[key] = 'data/Object_Images/' + quote(path.name)
            selected.append(path)
    target = destination / 'data/Object_Images'
    # Only clean generated image output, never the source folder.
    if target.resolve() == source.resolve():
        raise ValueError('Image output must differ from source')
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)
    for path in selected:
        shutil.copyfile(path, target / path.name)
    manifest = {'images': images, 'ignored_filenames': ignored,
                'id_rule': 'integer part of measurement ID; image lookup only'}
    (destination / 'image-index.json').write_text(json.dumps(manifest, indent=2))
    print(f'Published {len(images)} object photos; ignored {len(ignored)} filenames')
    return manifest
