# -*- coding: utf-8 -*-
"""
chk-NudeNet-local - File Handler
Managing image collection and validation
"""

import os
from pathlib import Path
from typing import List, Set
from config import SUPPORTED_EXTENSIONS

class FileHandler:
    def __init__(self, extensions: Set[str] = None):
        self.extensions = extensions or SUPPORTED_EXTENSIONS

    def validate_path(self, path_str: str) -> Path:
        """Validate if path exists and return Path object"""
        path = Path(path_str)
        if not path.exists():
            raise FileNotFoundError(f"Path does not exist: {path_str}")
        return path

    def is_image(self, file_path: Path) -> bool:
        """Check if file is a supported image"""
        return file_path.suffix.lower() in self.extensions

    def collect_images(self, target_path: Path, recursive: bool = False) -> List[Path]:
        """Collect image files from directory or single file"""
        if target_path.is_file():
            return [target_path] if self.is_image(target_path) else []
        
        images = []
        pattern = "**/*" if recursive else "*"
        for f in target_path.glob(pattern):
            if f.is_file() and self.is_image(f):
                images.append(f)
        
        # Sort by name for consistency
        return sorted(images, key=lambda x: x.name.lower())
