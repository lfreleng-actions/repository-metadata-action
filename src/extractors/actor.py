# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Actor metadata extractor.
Extracts information about the user who triggered the workflow.
"""


from ..models import ActorMetadata
from .base import BaseExtractor


class ActorExtractor(BaseExtractor):
    """Extracts actor (workflow trigger user) metadata."""

    def extract(self) -> ActorMetadata:
        """
        Extract actor metadata from environment.

        Returns:
            ActorMetadata object with actor information
        """
        self.debug("Extracting actor metadata")

        # Get actor name (always available)
        actor_name = self.config.GITHUB_ACTOR
        self.info(f"Actor: {actor_name}")

        # Get actor ID if available
        actor_id = None
        if self.config.GITHUB_ACTOR_ID:
            try:
                actor_id = int(self.config.GITHUB_ACTOR_ID)
                self.debug(f"Actor ID: {actor_id}")
            except (ValueError, TypeError) as e:
                self.warning(f"Failed to parse actor ID '{self.config.GITHUB_ACTOR_ID}': {e}")

        return ActorMetadata(
            name=actor_name,
            id=actor_id
        )
