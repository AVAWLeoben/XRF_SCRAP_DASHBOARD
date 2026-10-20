from pathlib import Path
import tempfile
import pytest
from image_assets import publish_images

def test_image_lookup_copy_and_integer_key():
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        source = root / 'input'
        source.mkdir()
        (source / '282_5422.jpg').write_bytes(b'test image bytes')
        (source / '4_85.JPG').write_bytes(b'another image')
        (source / 'readme.txt').write_text('ignored')
        manifest = publish_images(source, root / 'dist')
        assert manifest['images']['5422'] == 'data/Object_Images/282_5422.jpg'
        assert manifest['images']['85'] == 'data/Object_Images/4_85.JPG'
        assert (root / 'dist/data/Object_Images/282_5422.jpg').read_bytes() == b'test image bytes'
        (source / '283_5422.jpg').write_bytes(b'duplicate')
        with pytest.raises(ValueError, match='Duplicate photo'):
            publish_images(source, root / 'dist')

def test_missing_photo_directory_is_supported():
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        assert publish_images(root / 'absent', root / 'dist')['images'] == {}
