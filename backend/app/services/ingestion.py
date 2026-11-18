"""Repository Ingestion Service: Safe ZIP parsing, GitHub extraction, and snapshot versioning."""
import os
import io
import zipfile
import hashlib
import logging
from datetime import datetime
from typing import List, Dict, Tuple, Optional
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.models.repository import Repository, RepositoryVersion, SourceFile, IndexingStatus, RepositorySource
from app.models.jobs import IndexingJob, JobType, JobStatus
from app.config import get_settings

logger = logging.getLogger("codesage.ingestion")
settings = get_settings()

LANGUAGE_EXTENSION_MAP = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".java": "java",
    ".json": "json",
    ".md": "markdown",
    ".html": "html",
    ".css": "css",
    ".sql": "sql",
    ".sh": "bash",
    ".yml": "yaml",
    ".yaml": "yaml",
}

IGNORED_DIRS = {
    ".git", ".svn", ".hg", "node_modules", "__pycache__", ".pytest_cache",
    ".mypy_cache", "venv", ".venv", "env", "dist", "build", "target", "bin",
    "obj", ".idea", ".vscode", ".next", ".nuxt", "coverage", ".tox"
}

IGNORED_EXTENSIONS = {
    ".exe", ".dll", ".so", ".dylib", ".bin", ".zip", ".tar", ".gz", ".7z",
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".mp4", ".mp3", ".wav",
    ".woff", ".woff2", ".ttf", ".eot", ".class", ".pyc", ".pyo", ".jar"
}

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB per individual file
MAX_TOTAL_UNCOMPRESSED = 500 * 1024 * 1024  # 500 MB max uncompressed
MAX_COMPRESSION_RATIO = 100.0  # Max compression ratio
MAX_FILES_COUNT = 10_000


class IngestionService:
    @staticmethod
    def detect_language(file_path: str) -> str:
        """Map file extension to canonical language name."""
        ext = os.path.splitext(file_path)[1].lower()
        return LANGUAGE_EXTENSION_MAP.get(ext, "unknown")

    @staticmethod
    def is_safe_path(target_path: str) -> bool:
        """Prevent Zip-Slip directory traversal attacks."""
        norm = os.path.normpath(target_path)
        return not (norm.startswith("..") or os.path.isabs(norm) or "/../" in target_path or "\\..\\" in target_path)

    @classmethod
    def _validate_zip_archive(cls, zf: zipfile.ZipFile, compressed_size: int) -> List[zipfile.ZipInfo]:
        """Validate ZIP file structure against zip bombs and directory traversal."""
        infos = zf.infolist()
        if len(infos) > MAX_FILES_COUNT:
            raise ValueError(f"ZIP contains {len(infos)} files, exceeding limit of {MAX_FILES_COUNT}")

        total_uncompressed = 0
        valid_files = []

        for info in infos:
            if info.is_dir():
                continue

            cleaned_filename = info.filename.replace("\\", "/")
            if not cls.is_safe_path(cleaned_filename):
                raise ValueError(f"Path traversal detected in ZIP entry: {info.filename}")

            total_uncompressed += info.file_size
            if total_uncompressed > MAX_TOTAL_UNCOMPRESSED:
                raise ValueError(f"Archive exceeds maximum uncompressed size limit of {MAX_TOTAL_UNCOMPRESSED // (1024*1024)}MB")

            # Check compression ratio for bombs
            if info.compress_size > 0:
                ratio = info.file_size / info.compress_size
                if ratio > MAX_COMPRESSION_RATIO and info.file_size > 1024 * 1024:
                    raise ValueError(f"Suspicious compression ratio ({ratio:.1f}:1) detected for {info.filename}")

            ext = os.path.splitext(cleaned_filename)[1].lower()
            if ext in IGNORED_EXTENSIONS:
                continue

            parts = cleaned_filename.strip("/").split("/")
            if any(part in IGNORED_DIRS for part in parts):
                continue

            valid_files.append(info)

        return valid_files

    @classmethod
    async def ingest_zip(
        cls,
        repository_id: str,
        zip_bytes: bytes,
        upload_filename: str,
        db: AsyncSession,
    ) -> Tuple[RepositoryVersion, int]:
        """Safely extract ZIP bytes and create a new immutable RepositoryVersion."""
        upload_hash = hashlib.sha256(zip_bytes).hexdigest()

        # Update repository status to IN_PROGRESS
        await db.execute(
            update(Repository)
            .where(Repository.id == repository_id)
            .values(indexing_status=IndexingStatus.IN_PROGRESS)
        )

        try:
            zip_buffer = io.BytesIO(zip_bytes)
            with zipfile.ZipFile(zip_buffer, "r") as zf:
                valid_infos = cls._validate_zip_archive(zf, len(zip_bytes))

                # Find current version number
                stmt = select(RepositoryVersion.version_number).where(
                    RepositoryVersion.repository_id == repository_id
                ).order_by(RepositoryVersion.version_number.desc())
                latest_ver = (await db.execute(stmt)).scalars().first() or 0
                next_version_num = latest_ver + 1

                # Demote previous current versions
                await db.execute(
                    update(RepositoryVersion)
                    .where(RepositoryVersion.repository_id == repository_id)
                    .values(is_current=False)
                )

                version = RepositoryVersion(
                    repository_id=repository_id,
                    version_number=next_version_num,
                    upload_hash=upload_hash,
                    is_current=True,
                    file_count=0,
                    total_loc=0,
                )
                db.add(version)
                await db.flush()

                # Detect if ZIP has a single common top-level root directory (e.g. from GitHub zipballs)
                all_paths = [info.filename.replace("\\", "/").strip("/") for info in valid_infos]
                common_prefix = ""
                if all_paths:
                    first_dirs = [p.split("/")[0] for p in all_paths if "/" in p]
                    if len(first_dirs) == len(all_paths) and len(set(first_dirs)) == 1:
                        common_prefix = first_dirs[0] + "/"

                total_files = 0
                total_loc = 0
                lang_counts: Dict[str, Dict[str, int]] = {}

                for info in valid_infos:
                    clean_path = info.filename.replace("\\", "/").strip("/")
                    if common_prefix and clean_path.startswith(common_prefix):
                        clean_path = clean_path[len(common_prefix):]

                    if not clean_path:
                        continue

                    if info.file_size > MAX_FILE_SIZE:
                        continue

                    try:
                        raw_content = zf.read(info)
                    except Exception:
                        continue

                    # Attempt utf-8 decode
                    try:
                        text_content = raw_content.decode("utf-8")
                    except UnicodeDecodeError:
                        try:
                            text_content = raw_content.decode("latin-1")
                        except Exception:
                            continue

                    file_hash = hashlib.sha256(raw_content).hexdigest()
                    loc = len(text_content.splitlines())
                    language = cls.detect_language(clean_path)
                    file_name = os.path.basename(clean_path)

                    source_file = SourceFile(
                        version_id=version.id,
                        file_path=clean_path,
                        file_name=file_name,
                        language=language,
                        content=text_content,
                        content_hash=file_hash,
                        size_bytes=len(raw_content),
                        loc=loc,
                        is_parseable=language in {"python", "javascript", "typescript", "java"},
                    )
                    db.add(source_file)

                    total_files += 1
                    total_loc += loc
                    if language not in lang_counts:
                        lang_counts[language] = {"files": 0, "loc": 0}
                    lang_counts[language]["files"] += 1
                    lang_counts[language]["loc"] += loc

                # Determine primary language
                primary_lang = "other"
                if lang_counts:
                    primary_lang = max(lang_counts.items(), key=lambda x: x[1]["loc"])[0]

                version.file_count = total_files
                version.total_loc = total_loc
                import json
                version.language_stats = json.dumps(lang_counts)

                # Update repo metadata
                await db.execute(
                    update(Repository)
                    .where(Repository.id == repository_id)
                    .values(
                        total_files=total_files,
                        total_loc=total_loc,
                        primary_language=primary_lang,
                        indexing_status=IndexingStatus.PENDING,
                        last_indexed_at=datetime.utcnow(),
                    )
                )

                # Enqueue parsing & indexing job
                job = IndexingJob(
                    repository_id=repository_id,
                    version_id=version.id,
                    job_type=JobType.FILE_PARSING,
                    status=JobStatus.PENDING,
                    priority=10,
                    idempotency_key=f"parse_{version.id}",
                )
                db.add(job)

                await db.commit()
                await db.refresh(version)
                return version, total_files

        except Exception as e:
            logger.error(f"Error ingesting zip for repo {repository_id}: {str(e)}", exc_info=True)
            await db.execute(
                update(Repository)
                .where(Repository.id == repository_id)
                .values(indexing_status=IndexingStatus.FAILED)
            )
            await db.commit()
            raise

    @classmethod
    async def ingest_github(
        cls,
        repository_id: str,
        github_url: str,
        branch: str,
        token: Optional[str],
        db: AsyncSession,
    ) -> Tuple[RepositoryVersion, int]:
        """Download public or private repository from GitHub as a ZIP archive."""
        parts = github_url.rstrip("/").split("/")
        if len(parts) < 2:
            raise ValueError("Invalid GitHub URL format")
        owner, repo_name = parts[-2], parts[-1]
        if repo_name.endswith(".git"):
            repo_name = repo_name[:-4]

        archive_url = f"https://api.github.com/repos/{owner}/{repo_name}/zipball/{branch}"
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "CodeSage-Intelligence-Platform",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        elif settings.GITHUB_TOKEN:
            headers["Authorization"] = f"Bearer {settings.GITHUB_TOKEN}"

        async with httpx.AsyncClient(follow_redirects=True, timeout=120.0) as client:
            resp = await client.get(archive_url, headers=headers)
            if resp.status_code == 404:
                raise ValueError(f"GitHub repository {owner}/{repo_name} or branch '{branch}' not found or is private")
            if resp.status_code == 401 or resp.status_code == 403:
                raise ValueError(f"GitHub authentication error ({resp.status_code}). Provide a valid personal access token.")
            if resp.status_code != 200:
                raise ValueError(f"Failed to fetch archive from GitHub: HTTP {resp.status_code}")

            zip_bytes = resp.content

        return await cls.ingest_zip(
            repository_id=repository_id,
            zip_bytes=zip_bytes,
            upload_filename=f"{repo_name}-{branch}.zip",
            db=db,
        )
