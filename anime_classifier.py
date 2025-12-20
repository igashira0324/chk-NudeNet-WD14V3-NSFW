# -*- coding: utf-8 -*-
"""
chk-NudeNet-local - Anime/Real Classifier
"""

import os
import urllib.request
from pathlib import Path
from typing import Dict
import numpy as np
import cv2
import onnxruntime as ort
from config import ANIME_MODEL_URL

class AnimeClassifier:
    def __init__(self, model_dir: str = None):
        if model_dir is None:
            model_dir = os.path.join(os.path.expanduser("~"), ".nudenet_classifier")
        
        os.makedirs(model_dir, exist_ok=True)
        self.model_path = os.path.join(model_dir, "anime_real_cls.onnx")
        
        if not os.path.exists(self.model_path):
            print(f"Downloading anime classifier model to {self.model_path}...")
            urllib.request.urlretrieve(ANIME_MODEL_URL, self.model_path)
            
        # Initialize ONNX session with GPU support (fallback to CPU if failed)
        try:
            providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
            self.session = ort.InferenceSession(self.model_path, providers=providers)
        except Exception as e:
            print(f"Warning: CUDA initialization failed for AnimeClassifier, falling back to CPU. Error: {e}")
            self.session = ort.InferenceSession(self.model_path, providers=['CPUExecutionProvider'])
        self.input_name = self.session.get_inputs()[0].name
        
    def classify(self, image_array: np.ndarray) -> Dict[str, float]:
        """
        Classify image as anime or real
        Returns: { 'anime': float, 'real': float }
        """
        # Preprocessing for MobileNetV3 (Expected: 384x384)
        img = cv2.resize(image_array, (384, 384))
        img = img.astype(np.float32) / 255.0
        
        # Mean/Std normalization (ImageNet standards)
        mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
        img = (img - mean) / std
        
        # HWC to CHW
        img = np.transpose(img, (2, 0, 1))
        img = np.expand_dims(img, axis=0)
        
        # Inference
        outputs = self.session.run(None, {self.input_name: img})
        logits = outputs[0][0]
        
        # Softmax
        exp_logits = np.exp(logits - np.max(logits))
        probs = exp_logits / exp_logits.sum()
        
        # Labels for deepghs/anime_real_cls: [anime, real]
        # (Based on standard classification order for this model)
        return {
            'anime': float(probs[0]),
            'real': float(probs[1])
        }
