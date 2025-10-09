import os
import time
from pathlib import Path

import pytest
from PIL import Image

from utils.file_utils import FileManager
from utils.validators import ImageValidator, InputValidator


class TestFileManager:
    def test_create_and_cleanup_temp_files(self, tmp_path):
        manager = FileManager()

        # Create files
        f1 = manager.create_temp_file(b"abc", prefix="temp_test", suffix=".bin")
        f2 = manager.create_temp_file(b"xyz", prefix="temp_test", suffix=".bin")
        assert os.path.exists(f1) and os.path.exists(f2)

        # Cleanup by pattern
        cleaned = manager.cleanup_temp_files("temp_test_*")
        assert cleaned >= 2
        assert not os.path.exists(f1) and not os.path.exists(f2)

    def test_cleanup_old_files(self):
        manager = FileManager()
        # Create an older file by adjusting mtime
        f = manager.create_temp_file(b"old", prefix="temp_old", suffix=".dat")
        assert os.path.exists(f)
        Path(f).touch(exist_ok=True)
        old_mtime = time.time() - 3 * 3600
        os.utime(f, (old_mtime, old_mtime))

        cleaned = manager.cleanup_old_files(max_age_hours=1)
        assert cleaned >= 1
        assert not os.path.exists(f)

    def test_get_and_format_file_size(self):
        manager = FileManager()
        f = manager.create_temp_file(b"a" * 1500, prefix="temp_sz", suffix=".bin")
        size = manager.get_file_size(f)
        assert size == 1500
        human = manager.format_file_size(size)
        assert human.endswith("KB") or human.endswith("B")

    def test_is_safe_path_and_ensure_directory(self, tmp_path):
        manager = FileManager()
        manager.ensure_directory(str(tmp_path))
        assert tmp_path.exists()

        safe_file = manager.create_temp_file(b"ok", prefix="temp_safe", suffix=".dat")
        assert manager.is_safe_path(safe_file)
        # unsafe path outside temp dir
        assert not manager.is_safe_path("/etc/passwd")


class TestImageValidator:
    def test_validate_nonexistent_file(self):
        validator = ImageValidator()
        ok, msg = validator.validate("/path/does/not/exist.jpg")
        assert not ok and "does not exist" in msg

    def test_validate_too_large(self, tmp_path):
        validator = ImageValidator(max_size_mb=0)  # force too large for any file > 0
        p = tmp_path / "img.jpg"
        p.write_bytes(b"data")
        ok, msg = validator.validate(str(p))
        assert not ok and "File too large" in msg

    def test_validate_format_and_dimensions(self, tmp_path):
        p = tmp_path / "img.png"
        # Create a large image to trigger dimension check
        img = Image.new("RGB", (5000, 10), color=(255, 0, 0))
        img.save(p, format="PNG")

        validator = ImageValidator(max_dimensions=4096)
        ok, msg = validator.validate(str(p))
        assert not ok and "Image too large" in msg

    def test_validate_ok_jpeg(self, tmp_path):
        p = tmp_path / "ok.jpg"
        img = Image.new("RGB", (100, 50), color=(0, 255, 0))
        img.save(p, format="JPEG")

        validator = ImageValidator()
        ok, msg = validator.validate(str(p))
        assert ok and msg == ""


class TestInputValidator:
    def test_validate_item_name(self):
        assert not InputValidator.validate_item_name("")[0]
        assert not InputValidator.validate_item_name(" ")[0]
        assert not InputValidator.validate_item_name("a" * 51)[0]
        assert not InputValidator.validate_item_name("bad:name")[0]
        assert InputValidator.validate_item_name("Good Name")[0]

    def test_validate_item_description(self):
        assert not InputValidator.validate_item_description("")[0]
        assert not InputValidator.validate_item_description(" ")[0]
        assert not InputValidator.validate_item_description("x" * 201)[0]
        assert InputValidator.validate_item_description("Nice")[0]

    def test_validate_location_and_user(self):
        assert not InputValidator.validate_location_id("")[0]
        assert not InputValidator.validate_location_id("bad id!")[0]
        assert InputValidator.validate_location_id("loc_123")[0]

        assert not InputValidator.validate_user_id(0)[0]
        assert InputValidator.validate_user_id(123)[0]

    def test_sanitize_filename_and_language_model(self):
        name = InputValidator.sanitize_filename('bad<>:"/\\|?*.txt')
        assert "_" in name and not any(c in name for c in '<>:"/\\|?*')

        longname = "a" * 120 + ".jpg"
        sanitized = InputValidator.sanitize_filename(longname)
        assert len(sanitized) <= 100

        ok, _ = InputValidator.validate_language_code("en")
        bad, msg = InputValidator.validate_language_code("it")
        assert ok and not bad

        okm, _ = InputValidator.validate_model_name("gpt-4o", ["gpt-4o", "gpt-3.5"])
        badm, _ = InputValidator.validate_model_name("bad", ["gpt-4o"]) 
        assert okm and not badm


