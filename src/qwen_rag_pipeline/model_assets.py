from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


DEFAULT_MODEL_ROOT = Path("models/qwen-rag")


@dataclass(frozen=True)
class ModelAsset:
    role: str
    repo_id: str
    revision: str
    directory_name: str

    def local_path(self, root: Path | str = DEFAULT_MODEL_ROOT) -> Path:
        return Path(root) / self.directory_name


# Pinned upstream revisions. Downloads are explicit and runtime loading is local-only.
EMBEDDING_ASSET = ModelAsset(
    role="embedding",
    repo_id="Qwen/Qwen3-Embedding-0.6B",
    revision="97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3",
    directory_name="Qwen3-Embedding-0.6B",
)
RERANKER_ASSET = ModelAsset(
    role="reranker",
    repo_id="Qwen/Qwen3-Reranker-0.6B",
    revision="e61197ed45024b0ed8a2d74b80b4d909f1255473",
    directory_name="Qwen3-Reranker-0.6B",
)
MODEL_ASSETS = (EMBEDDING_ASSET, RERANKER_ASSET)


def download_assets(
    *,
    model_root: Path | str = DEFAULT_MODEL_ROOT,
    assets: Iterable[ModelAsset] = MODEL_ASSETS,
    token: str | None = None,
    max_workers: int = 4,
) -> Path:
    try:
        from huggingface_hub import snapshot_download
    except ImportError as exc:  # pragma: no cover - optional install
        raise RuntimeError(
            "Qwen RAG model download requires huggingface-hub; "
            "install with: pip install -r requirements-qwen-rag.txt"
        ) from exc

    root = Path(model_root)
    root.mkdir(parents=True, exist_ok=True)
    downloaded: list[dict[str, str]] = []
    for asset in assets:
        target = asset.local_path(root)
        target.mkdir(parents=True, exist_ok=True)
        snapshot_download(
            repo_id=asset.repo_id,
            revision=asset.revision,
            local_dir=target,
            token=token,
            max_workers=max_workers,
        )
        downloaded.append(
            {
                **asdict(asset),
                "local_path": str(target),
            }
        )

    manifest = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "models": downloaded,
    }
    manifest_path = root / "model-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest_path


def require_model_path(asset: ModelAsset, root: Path | str = DEFAULT_MODEL_ROOT) -> Path:
    path = asset.local_path(root)
    required = (path / "config.json", path / "model.safetensors")
    missing = [item for item in required if not item.is_file()]
    if missing:
        raise FileNotFoundError(
            f"local {asset.role} model is missing under {path}; "
            "run: python scripts/download_qwen_rag_models.py"
        )
    return path
