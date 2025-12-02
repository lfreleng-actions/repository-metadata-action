# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Cache key generator extractor.
Generates cache keys based on repository and commit information.
"""


from ..models import CacheMetadata
from .base import BaseExtractor


class CacheExtractor(BaseExtractor):
    """Generates cache keys for workflow caching."""

    def extract(self) -> CacheMetadata:
        """
        Generate cache keys based on repository and commit.

        Returns:
            CacheMetadata object with cache key and restore key
        """
        self.debug("Generating cache keys")

        # Extract components for cache key
        owner = self.config.GITHUB_REPOSITORY_OWNER
        repo_name = self.config.GITHUB_REPOSITORY.split("/", 1)[1]
        ref_name = self.config.GITHUB_REF_NAME or "main"
        commit_sha = self.config.GITHUB_SHA

        # Generate full cache key: owner-repo-ref-sha
        cache_key = f"{owner}-{repo_name}-{ref_name}-{commit_sha}"

        # Generate restore key prefix: owner-repo-ref-
        # This allows restoring from any commit on the same ref
        cache_restore_key = f"{owner}-{repo_name}-{ref_name}-"

        self.debug(f"Cache key: {cache_key}")
        self.debug(f"Cache restore key prefix: {cache_restore_key}")

        return CacheMetadata(
            key=cache_key,
            restore_key=cache_restore_key
        )
