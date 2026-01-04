"""
System prompt management service.

Loads and manages system prompts from markdown files in the prompts/ directory.
Each prompt file uses YAML frontmatter for metadata (title, description) and
markdown body for the actual prompt content.

Features:
- File-based storage with mtime caching for hot-reload
- Protected default prompt that cannot be edited/deleted
- CRUD operations for custom prompts
"""
import os
import re
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Protected default prompt - cannot be edited or deleted
DEFAULT_PROMPT_ID = 'default_system_prompt'
DEFAULT_PROMPT = {
    'id': DEFAULT_PROMPT_ID,
    'title': 'Helpful Assistant',
    'description': 'A general-purpose helpful AI assistant',
    'content': 'You are a helpful assistant.',
    'protected': True
}


class PromptService:
    """Service for loading and parsing system prompts from markdown files."""

    def __init__(self):
        self._cache = {}
        self._cache_mtime = {}

    def _get_prompts_dir(self):
        """Get the prompts directory path relative to project root."""
        # Go up from chat_rag_explorer to project root, then into prompts/
        return Path(__file__).parent.parent / "prompts"

    def _parse_frontmatter(self, content):
        """
        Parse YAML frontmatter from markdown content.

        Returns tuple of (metadata_dict, body_content).
        Frontmatter is expected between --- delimiters at file start.
        """
        pattern = r'^---\s*\n(.*?)\n---\s*\n?(.*)$'
        match = re.match(pattern, content, re.DOTALL)

        if match:
            frontmatter_raw = match.group(1)
            body = match.group(2)

            # Simple YAML parsing for title/description
            metadata = {}
            for line in frontmatter_raw.split('\n'):
                line = line.strip()
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip().strip('"\'')
                    metadata[key] = value

            return metadata, body.strip()

        return {}, content.strip()

    def _load_prompt_file(self, file_path, request_id=None):
        """Load and parse a single prompt file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            metadata, body = self._parse_frontmatter(content)

            # Generate ID from filename (without extension)
            prompt_id = file_path.stem

            return {
                'id': prompt_id,
                'title': metadata.get('title', prompt_id),
                'description': metadata.get('description', ''),
                'content': body
            }
        except Exception as e:
            log_prefix = f"[{request_id}] " if request_id else ""
            logger.error(f"{log_prefix}Failed to load prompt file {file_path}: {e}")
            return None

    def get_prompts(self, request_id=None):
        """
        Get all available prompts from the prompts directory.

        Returns list of prompt objects with id, title, description, content.
        Uses file mtime-based caching to avoid re-reading unchanged files.
        Always includes the protected default prompt.
        """
        log_prefix = f"[{request_id}] " if request_id else ""
        prompts_dir = self._get_prompts_dir()

        # Start with the protected default prompt
        prompts = [DEFAULT_PROMPT.copy()]

        if not prompts_dir.exists():
            logger.warning(f"{log_prefix}Prompts directory does not exist: {prompts_dir}")
            return prompts

        for file_path in prompts_dir.glob('*.md'):
            try:
                mtime = file_path.stat().st_mtime
                prompt_id = file_path.stem

                # Skip if somehow a file has the default prompt ID
                if prompt_id == DEFAULT_PROMPT_ID:
                    continue

                # Check cache validity
                if (prompt_id in self._cache and
                    prompt_id in self._cache_mtime and
                    self._cache_mtime[prompt_id] == mtime):
                    prompts.append(self._cache[prompt_id])
                    continue

                # Load and cache
                prompt = self._load_prompt_file(file_path, request_id)
                if prompt:
                    prompt['protected'] = False
                    self._cache[prompt_id] = prompt
                    self._cache_mtime[prompt_id] = mtime
                    prompts.append(prompt)

            except Exception as e:
                logger.error(f"{log_prefix}Error processing {file_path}: {e}")

        # Sort by title
        prompts.sort(key=lambda p: p['title'].lower())

        logger.debug(f"{log_prefix}Loaded {len(prompts)} prompts from {prompts_dir}")
        return prompts

    def get_prompt_by_id(self, prompt_id, request_id=None):
        """
        Get a specific prompt by its ID.

        Returns prompt object or None if not found.
        """
        log_prefix = f"[{request_id}] " if request_id else ""

        # Return protected default prompt if requested
        if prompt_id == DEFAULT_PROMPT_ID:
            return DEFAULT_PROMPT.copy()

        prompts_dir = self._get_prompts_dir()
        file_path = prompts_dir / f"{prompt_id}.md"

        if not file_path.exists():
            logger.warning(f"{log_prefix}Prompt not found: {prompt_id}")
            return None

        try:
            mtime = file_path.stat().st_mtime

            # Check cache validity
            if (prompt_id in self._cache and
                prompt_id in self._cache_mtime and
                self._cache_mtime[prompt_id] == mtime):
                return self._cache[prompt_id]

            # Load and cache
            prompt = self._load_prompt_file(file_path, request_id)
            if prompt:
                prompt['protected'] = False
                self._cache[prompt_id] = prompt
                self._cache_mtime[prompt_id] = mtime

            return prompt

        except Exception as e:
            logger.error(f"{log_prefix}Error loading prompt {prompt_id}: {e}")
            return None

    def _format_prompt_file(self, title, description, content):
        """Format prompt data as markdown with YAML frontmatter."""
        return f'''---
title: "{title}"
description: "{description}"
---
{content}
'''

    def is_protected(self, prompt_id):
        """Check if a prompt ID is protected."""
        return prompt_id == DEFAULT_PROMPT_ID

    def save_prompt(self, prompt_id, title, description, content, request_id=None):
        """
        Save a prompt to file. Creates new or updates existing.

        Returns the saved prompt object or None on error.
        Rejects saving to protected prompt IDs.
        """
        log_prefix = f"[{request_id}] " if request_id else ""

        if self.is_protected(prompt_id):
            logger.warning(f"{log_prefix}Cannot save protected prompt: {prompt_id}")
            return None

        prompts_dir = self._get_prompts_dir()

        # Ensure prompts directory exists
        prompts_dir.mkdir(parents=True, exist_ok=True)

        file_path = prompts_dir / f"{prompt_id}.md"

        try:
            file_content = self._format_prompt_file(title, description, content)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(file_content)

            # Invalidate cache for this prompt
            if prompt_id in self._cache:
                del self._cache[prompt_id]
            if prompt_id in self._cache_mtime:
                del self._cache_mtime[prompt_id]

            logger.info(f"{log_prefix}Saved prompt: {prompt_id}")

            # Return the saved prompt
            return self._load_prompt_file(file_path, request_id)

        except Exception as e:
            logger.error(f"{log_prefix}Failed to save prompt {prompt_id}: {e}")
            return None

    def delete_prompt(self, prompt_id, request_id=None):
        """
        Delete a prompt file.

        Returns True on success, False on error.
        Rejects deleting protected prompts.
        """
        log_prefix = f"[{request_id}] " if request_id else ""

        if self.is_protected(prompt_id):
            logger.warning(f"{log_prefix}Cannot delete protected prompt: {prompt_id}")
            return False

        prompts_dir = self._get_prompts_dir()
        file_path = prompts_dir / f"{prompt_id}.md"

        if not file_path.exists():
            logger.warning(f"{log_prefix}Cannot delete, prompt not found: {prompt_id}")
            return False

        try:
            file_path.unlink()

            # Remove from cache
            if prompt_id in self._cache:
                del self._cache[prompt_id]
            if prompt_id in self._cache_mtime:
                del self._cache_mtime[prompt_id]

            logger.info(f"{log_prefix}Deleted prompt: {prompt_id}")
            return True

        except Exception as e:
            logger.error(f"{log_prefix}Failed to delete prompt {prompt_id}: {e}")
            return False


# Singleton instance
prompt_service = PromptService()
