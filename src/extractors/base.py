# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Base extractor class providing common functionality.
"""

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..config import Config


class BaseExtractor(ABC):
    """Abstract base class for metadata extractors."""

    def __init__(self, config: "Config", logger: logging.Logger | None = None):
        """
        Initialize extractor with configuration and logger.

        Args:
            config: Configuration object
            logger: Optional logger instance
        """
        self.config = config
        self.logger = logger or logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def extract(self) -> Any:
        """
        Extract metadata. Must be implemented by subclasses.

        Returns:
            Extracted metadata (type varies by subclass)
        """

    def debug(self, message: str):
        """
        Log debug message if debug mode is enabled.

        Args:
            message: Debug message to log
        """
        if self.config.DEBUG_MODE:
            self.logger.debug(message)

    def info(self, message: str):
        """
        Log info message.

        Args:
            message: Info message to log
        """
        self.logger.info(message)

    def warning(self, message: str):
        """
        Log warning message.

        Args:
            message: Warning message to log
        """
        self.logger.warning(message)

    def error(self, message: str, exception: Exception | None = None):
        """
        Log error message with optional exception.

        Args:
            message: Error message to log
            exception: Optional exception to log
        """
        if exception:
            self.logger.error(f"{message}: {exception!s}", exc_info=True)
        else:
            self.logger.error(message)
