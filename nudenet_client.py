import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
import cv2
import numpy as np

# Add common CUDA search paths for sd.webui environment
def add_cuda_to_path():
    if sys.platform != "win32":
        return
    
    # Try to find DLLs in the parent sd.webui directories
    possible_paths = [
        Path(__file__).parent.parent.parent.parent / "bin",
        Path(__file__).parent.parent.parent.parent / "cudnn" / "bin",
        Path("E:\\Sync_Connect_Plus\\sd.webui\\bin"),
        Path("E:\\Sync_Connect_Plus\\sd.webui\\cudnn\\bin"),
        # Discovered paths from other venvs
        Path("E:\\Sync_Connect_Plus\\sd.webui\\20230721SD1111\\stable-diffusion-webui\\venv\\Lib\\site-packages\\torch\\lib"),
        Path("E:\\Sync_Connect_Plus\\sd.webui\\system\\magic-animate-for-windows\\venv\\Lib\\site-packages\\torch\\lib"),
    ]
    
    venv_torch_lib = Path(os.path.dirname(sys.executable)) / "Lib" / "site-packages" / "torch" / "lib"
    if venv_torch_lib.exists():
        possible_paths.append(venv_torch_lib)

    for p in possible_paths:
        if p.exists():
            try:
                os.add_dll_directory(str(p))
            except Exception:
                pass

# Attempt to optimize paths BEFORE imports
try:
    add_cuda_to_path()
except Exception:
    pass

try:
    from nudenet import NudeDetector
except ImportError:
    NudeDetector = None

from anime_classifier import AnimeClassifier
from clothing_tagger import ClothingTagger
from config import CLOTHING_TAGGER_URL, CLOTHING_TAGS_URL

class NudeNetClientError(Exception):
    """Custom exception for NudeNet Client errors"""
    pass

class NudeNetClient:
    def __init__(self):
        # 1. NudeDetector Initialization
        self.detector = None
        if NudeDetector is not None:
            try:
                self.detector = NudeDetector()
            except Exception as e:
                print(f"Warning: Failed to initialize NudeDetector: {e}")
        
        # 2. Anime Classifier Initialization
        self.anime_cls = None
        try:
            self.anime_cls = AnimeClassifier()
        except Exception as e:
            print(f"Warning: Failed to initialize AnimeClassifier: {e}")

        # 3. Clothing Tagger Initialization
        self.clothing_tagger = None
        try:
            self.clothing_tagger = ClothingTagger(CLOTHING_TAGGER_URL, CLOTHING_TAGS_URL)
        except Exception as e:
            print(f"Warning: Failed to initialize ClothingTagger: {e}")

        if self.detector is None and self.anime_cls is None and self.clothing_tagger is None:
            raise NudeNetClientError("Failed to initialize ALL models. Please check your environment and logs.")

    def analyze_image(self, image_path: Path) -> Dict[str, Any]:
        """
        Analyze an image for NSFW content, style, and clothing tags
        ALWAYS returns a Dict to satisfy contract.
        """
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")
            
        try:
            # Read image as binary data to handle Japanese paths
            with open(image_path, 'rb') as f:
                image_data = f.read()
            
            # Decode image using OpenCV
            image_array = cv2.imdecode(np.frombuffer(image_data, np.uint8), cv2.IMREAD_COLOR)
            
            if image_array is None:
                raise NudeNetClientError(f"Failed to decode image: {image_path}")
            
            # 1. NudeNet Detection (Graceful skip if None)
            detections = []
            if self.detector:
                try:
                    results = self.detector.detect(image_array)
                    for r in results:
                        detections.append({
                            'box': r.get('box'),
                            'score': r.get('score'),
                            'label': r.get('class')
                        })
                except Exception as e:
                    print(f"Detection error for {image_path}: {e}")

            # 2. Anime/Real Classification (Graceful skip if None)
            style = {'anime': 0.0, 'real': 0.0}
            if self.anime_cls:
                try:
                    style = self.anime_cls.classify(image_array)
                except Exception as e:
                    print(f"Anime classification error: {e}")

            # 3. Clothing Tagging (Graceful skip if None)
            clothing_tags = {}
            if self.clothing_tagger:
                try:
                    clothing_tags = self.clothing_tagger.predict(image_array)
                except Exception as e:
                    print(f"Clothing tagging error: {e}")
            
            return {
                'detections': detections,
                'style': style,
                'clothing_tags': clothing_tags
            }
            
        except Exception as e:
            raise NudeNetClientError(f"Error during NudeNet inference: {e}")

if __name__ == "__main__":
    # Quick test if run directly
    import sys
    if len(sys.argv) > 1:
        client = NudeNetClient()
        res = client.analyze_image(Path(sys.argv[1]))
        import json
        print(json.dumps(res, indent=2))
