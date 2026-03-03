import os
import tempfile

import pytest

from app.services.file_service import FileService


class TestFileService:

    async def test_list_files_empty_dir(self, tmp_path):
        svc = FileService()
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("app.services.file_service.settings", type("S", (), {"FILE_DIR": str(tmp_path)})())
            mp.setattr("app.infrastructure.cache.files_cache._data", None)
            result = await svc.list_files()
        assert result == []

    async def test_list_files_with_files(self, tmp_path):
        (tmp_path / "a.txt").write_text("hello")
        (tmp_path / "b.txt").write_text("world")

        svc = FileService()
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("app.services.file_service.settings", type("S", (), {"FILE_DIR": str(tmp_path)})())
            mp.setattr("app.infrastructure.cache.files_cache._data", None)
            result = await svc.list_files()

        assert len(result) == 2
        names = [f["name"] for f in result]
        assert "a.txt" in names
        assert "b.txt" in names
        assert result[0]["size"] > 0

    async def test_list_files_pagination(self, tmp_path):
        for i in range(5):
            (tmp_path / f"file_{i}.txt").write_text(f"content {i}")

        svc = FileService()
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("app.services.file_service.settings", type("S", (), {"FILE_DIR": str(tmp_path)})())
            mp.setattr("app.infrastructure.cache.files_cache._data", None)
            result = await svc.list_files(skip=2, limit=2)

        assert len(result) == 2

    async def test_list_files_nonexistent_dir(self):
        svc = FileService()
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("app.services.file_service.settings", type("S", (), {"FILE_DIR": "/nonexistent/path"})())
            mp.setattr("app.infrastructure.cache.files_cache._data", None)
            result = await svc.list_files()
        assert result == []

    async def test_file_exists_true(self, tmp_path):
        (tmp_path / "exists.txt").write_text("data")

        svc = FileService()
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("app.services.file_service.settings", type("S", (), {"FILE_DIR": str(tmp_path)})())
            result = await svc.file_exists("exists.txt")
        assert result is True

    async def test_file_exists_false(self, tmp_path):
        svc = FileService()
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("app.services.file_service.settings", type("S", (), {"FILE_DIR": str(tmp_path)})())
            result = await svc.file_exists("nonexistent.txt")
        assert result is False

    async def test_file_exists_path_traversal(self, tmp_path):
        svc = FileService()
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("app.services.file_service.settings", type("S", (), {"FILE_DIR": str(tmp_path)})())
            result = await svc.file_exists("../../etc/passwd")
        assert result is False
