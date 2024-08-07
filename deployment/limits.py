from __future__ import annotations

import os
from pathlib import Path

import psutil
from loguru import logger


class MemoryLimit:
    def __init__(self, current_usage: int, max_usage: int | None):
        self.current_usage = current_usage
        self.max_usage = max_usage

    @property
    def current_mib(self):
        return self.current_usage // (1024 * 1024)

    @property
    def max_usage_mib(self):
        return self.max_usage // (1024 * 1024) if self.max_usage else None

    def __str__(self):
        max_usage_str = '%d MiB' % self.max_usage_mib if self.max_usage_mib else 'no limit'
        return f"Current Usage: {self.current_mib} MiB, Max Usage: {max_usage_str}"

    def usage_ratio(self) -> float | None:
        if not self.max_usage:
            return None
        return self.current_usage / self.max_usage

    def as_dict(self):
        return {
            'current_usage_mib': self.current_mib,
            'limit_mib': self.max_usage,
        }

    @classmethod
    def from_cgroup(cls) -> MemoryLimit | None:
        cgroup_path = Path("/sys/fs/cgroup")
        if not cgroup_path.exists():
            return None

        current_file = cgroup_path / "memory.current"
        if not current_file.exists():
            return None
        max_file = cgroup_path / "memory.max"
        try:
            current_usage = int(current_file.read_text().strip())
            if max_file.exists():
                max_usage_str = max_file.read_text().strip()
                max_usage = int(max_usage_str) if max_usage_str != "max" else None
            else:
                max_usage = None
            return cls(current_usage, max_usage)
        except Exception:
            logger.exception("Unable to get memory information")
            return None

    @classmethod
    def from_psutil(cls, pid: int | None = None) -> MemoryLimit:
        process = psutil.Process(pid or os.getpid())
        memory_info = process.memory_info()
        current_usage = memory_info.rss  # Resident Set Size
        max_usage = psutil.virtual_memory().total  # Total system memory

        return cls(current_usage, max_usage)

    @classmethod
    def get(cls) -> MemoryLimit:
        return MemoryLimit.from_cgroup() or MemoryLimit.from_psutil()
