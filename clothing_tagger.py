# -*- coding: utf-8 -*-
"""
chk-NudeNet-local - Clothing Tagger (WD14)
High-precision clothing/pose classification using ONNX
"""

import os
import cv2
import numpy as np
import onnxruntime as ort
import urllib.request
import pandas as pd
from pathlib import Path
from PIL import Image
from typing import Dict, List, Tuple, Any

class ClothingTagger:
    def __init__(self, model_url: str, tags_url: str):
        self.model_path = Path.home() / ".gemini" / "models" / "wd_eva02_large_v3.onnx"
        self.tags_path = Path.home() / ".gemini" / "models" / "wd_eva02_large_v3_tags.csv"
        self.model_path.parent.mkdir(parents=True, exist_ok=True)

        self._ensure_model_exists(model_url, tags_url)
        
        # Initialize session with GPU support (fallback to CPU if failed)
        try:
            providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
            self.session = ort.InferenceSession(str(self.model_path), providers=providers)
        except Exception as e:
            print(f"Warning: CUDA initialization failed for ClothingTagger, falling back to CPU. Error: {e}")
            self.session = ort.InferenceSession(str(self.model_path), providers=['CPUExecutionProvider'])
            
        self.input_name = self.session.get_inputs()[0].name
        
        # Load tags
        self.tags_df = pd.read_csv(self.tags_path)
        # Category 0: General, 4: Character, 9: Rating
        self.tags = self.tags_df[self.tags_df['category'] == 0]['name'].tolist()
        self.tag_indices = self.tags_df[self.tags_df['category'] == 0].index.tolist()

    def _ensure_model_exists(self, model_url: str, tags_url: str):
        if not self.model_path.exists():
            print(f"Downloading high-precision clothing tagger model (~1.3GB)...")
            urllib.request.urlretrieve(model_url, self.model_path)
        if not self.tags_path.exists():
            print(f"Downloading tags data...")
            urllib.request.urlretrieve(tags_url, self.tags_path)

    def _preprocess(self, img: np.ndarray) -> np.ndarray:
        """WD14 specific preprocessing (448x448 with padding) - Closer to official implementation"""
        # Convert BGR to RGB
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(img_rgb)
        
        # Scaling while maintaining aspect ratio
        w, h = pil_img.size
        size = 448
        if w > h:
            new_w = size
            new_h = int(h * (size / w))
        else:
            new_h = size
            new_w = int(w * (size / h))
            
        pil_img = pil_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        
        # Padding with white to 448x448
        new_img = Image.new("RGB", (size, size), (255, 255, 255))
        new_img.paste(pil_img, ((size - new_w) // 2, (size - new_h) // 2))
        
        # To float32 and [0, 255] range (V3 ONNX often expects 0-255)
        img_array = np.array(new_img).astype(np.float32)
        
        # Add batch dimension [1, 448, 448, 3]
        return np.expand_dims(img_array, axis=0)

    def predict(self, img: np.ndarray) -> Dict[str, float]:
        """Predict tags and return a dictionary of {tag: score}"""
        if img is None:
            return {}
            
        print(f"DEBUG: Processing image with shape: {img.shape}")
        input_data = self._preprocess(img)
        outputs = self.session.run(None, {self.input_name: input_data})
        probs = outputs[0][0]
        
        if not hasattr(self, '_logged_info'):
            print(f"DEBUG: Model prediction array length: {len(probs)}")
            self._logged_info = True

        # Map indices to tags and filter by score > 0.1
        result = {}
        for idx in self.tag_indices:
            if idx >= len(probs): continue
            score = float(probs[idx])
            if score > 0.1:
                tag = self.tags_df.iloc[idx]['name']
                clean_tag = tag.replace('_', ' ')
                result[clean_tag] = score
        
        if result:
            top_tags = sorted(result.items(), key=lambda x: x[1], reverse=True)[:10]
            print(f"DEBUG: Tagger results (Top 10) -> {top_tags}")
        
        return result
