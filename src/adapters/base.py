"""Base adapter class for all benchmark tools"""

import shutil
from abc import ABC, abstractmethod
from typing import List, Tuple, Optional

from src.models import BenchmarkResult, PromptLogEntry, ToolEvidence


class BaseToolAdapter(ABC):
    """Abstract base for all tool adapters"""

    tool_name: str = ""

    @abstractmethod
    async def run(self, prompts: list) -> Tuple[List[BenchmarkResult], List[PromptLogEntry], Optional[ToolEvidence]]:
        """Run benchmark and return results, prompt logs, and raw evidence"""
        pass

    def is_available(self) -> bool:
        """Check if tool is installed and ready"""
        return True

    def get_version(self) -> str:
        """Get tool version string"""
        return "unknown"

    @staticmethod
    def check_binary(name: str) -> bool:
        """Check if a CLI binary exists in PATH"""
        return shutil.which(name) is not None
