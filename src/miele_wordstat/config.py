from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    data_root: Path
    yandex_search_api_key: str | None
    yandex_folder_id: str | None
    default_region: int
    max_requests_per_batch: int
    max_requests_per_minute: int
    max_spend_per_day: float

    @property
    def raw_dir(self) -> Path:
        return self.data_root / "raw" / "yandex_wordstat"

    @property
    def duckdb_path(self) -> Path:
        return self.data_root / "warehouse" / "duckdb" / "miele.duckdb"

    @property
    def parquet_dir(self) -> Path:
        return self.data_root / "warehouse" / "parquet"

    @property
    def exports_dir(self) -> Path:
        return self.data_root / "exports"

    @property
    def logs_dir(self) -> Path:
        return self.data_root / "logs"

    @property
    def state_dir(self) -> Path:
        return self.data_root / "state"

    @property
    def backups_dir(self) -> Path:
        return self.data_root / "backups"


def load_settings() -> Settings:
    load_dotenv()

    return Settings(
        data_root=Path(os.getenv("DATA_ROOT", "/mnt/miele-ssd/miele-data")),
        yandex_search_api_key=os.getenv("YANDEX_SEARCH_API_KEY"),
        yandex_folder_id=os.getenv("YANDEX_FOLDER_ID"),
        default_region=int(os.getenv("DEFAULT_REGION", "225")),
        max_requests_per_batch=int(os.getenv("MAX_REQUESTS_PER_BATCH", "200")),
        max_requests_per_minute=int(os.getenv("MAX_REQUESTS_PER_MINUTE", "30")),
        max_spend_per_day=float(os.getenv("MAX_SPEND_PER_DAY", "1000")),
    )
