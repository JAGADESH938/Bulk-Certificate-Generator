import os
import uuid
from pathlib import Path
from typing import Union

from app.core.config import settings


class StorageService:
    """Handles filesystem storage for generated certificate PDF documents."""

    def __init__(self, base_storage_dir: Union[Path, str, None] = None) -> None:
        if base_storage_dir is None:
            self.base_dir = settings.storage_dir
        else:
            self.base_dir = Path(base_storage_dir).resolve()
        
        # Ensure base storage directory exists
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def get_certificate_file_path(
        self,
        job_id: Union[uuid.UUID, str],
        certificate_id: Union[uuid.UUID, str],
    ) -> Path:
        """Resolve and ensure parent directory for a certificate file."""
        job_dir = (self.base_dir / str(job_id)).resolve()
        
        # Guard against path traversal
        if not str(job_dir).startswith(str(self.base_dir)):
            raise ValueError("Invalid storage path: directory traversal attempt")
            
        job_dir.mkdir(parents=True, exist_ok=True)
        return (job_dir / f"{certificate_id}.pdf").resolve()

    def save_certificate_file(
        self,
        job_id: Union[uuid.UUID, str],
        certificate_id: Union[uuid.UUID, str],
        content: bytes,
    ) -> Path:
        """Write PDF byte contents directly to the destination path."""
        target_path = self.get_certificate_file_path(job_id, certificate_id)
        target_path.write_bytes(content)
        return target_path

    def file_exists(self, file_path: Union[str, Path, None]) -> bool:
        """Check if target certificate file exists on disk."""
        if not file_path:
            return False
        path = Path(file_path).resolve()
        return path.is_file()

    def delete_certificate_file(self, file_path: Union[str, Path]) -> bool:
        """Remove a certificate file from disk if it exists."""
        try:
            path = Path(file_path).resolve()
            if path.is_file():
                path.unlink()
                return True
        except OSError:
            pass
        return False


# Singleton instance
storage_service = StorageService()
