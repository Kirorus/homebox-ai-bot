import os
from PIL import Image
import pytest

from services.image_service import ImageService


class TestImageService:
    def test_validate_and_get_info(self, tmp_path):
        svc = ImageService()
        p = tmp_path / "img.jpg"
        Image.new("RGB", (100, 50), color=(1, 2, 3)).save(p, format="JPEG")

        ok, msg = svc.validate_image(str(p))
        assert ok and msg == ""

        info = svc.get_image_info(str(p))
        assert info.get("width") == 100
        assert info.get("format") == "JPEG"

    def test_resize_and_optimize(self, tmp_path):
        svc = ImageService()
        big = tmp_path / "big.jpg"
        Image.new("RGB", (3000, 1500), color=(9, 9, 9)).save(big, format="JPEG")

        resized = svc.resize_image_if_needed(str(big), max_size=512)
        assert os.path.exists(resized)
        assert resized != str(big)

        optimized = svc.optimize_image(str(big))
        assert os.path.exists(optimized)

        # Cleanup temp files produced by service
        svc.cleanup_temp_files([resized, optimized])
        assert not os.path.exists(resized) or not os.path.exists(optimized)


