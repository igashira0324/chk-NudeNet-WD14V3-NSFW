# -*- coding: utf-8 -*-
"""
chk-NudeNet-local - Configuration
"""

# NudeNet Labels to Categorized Mappings
# User requested specific categories
CATEGORY_MAP = {
    'FEMALE_BREAST': [
        'FEMALE_BREAST_EXPOSED'
    ],
    'GENITALIA': [
        'FEMALE_GENITALIA_EXPOSED',
        'FEMALE_GENITALIA_COVERED',
        'MALE_GENITALIA_EXPOSED',
        'MALE_GENITALIA_COVERED'
    ],
    'BUTTOCKS': [
        'BUTTOCKS_EXPOSED',
        'BUTTOCKS_COVERED'
    ],
    'ANUS': [
        'ANUS_EXPOSED',
        'ANUS_COVERED'
    ],
    'OTHER_REGIONS': [
        'BELLY_EXPOSED',
        'BELLY_COVERED',
        'FEET_EXPOSED',
        'FEET_COVERED',
        'ARMPITS_EXPOSED',
        'ARMPITS_COVERED'
    ],
    'FACE': [
        'FACE_FEMALE',
        'FACE_MALE'
    ]
}

# Supported extensions
SUPPORTED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}

# Thresholds for Verdicts (based on max confidence in any NSFW category)
THRESHOLDS = {
    'UNSAFE': 0.8,
    'HIGH_RISK': 0.6,
    'MODERATE': 0.4,
    'LOW_RISK': 0.2
}

# Verdict Icons
VERDICT_ICONS = {
    'SAFE': '✅',
    'LOW_RISK': '⚠️',
    'MODERATE': '⚠️',
    'HIGH_RISK': '🔶',
    'UNSAFE': '🔴',
    'ERROR': '❌'
}

# Model URLs
NUDENET_MODEL_URL = "https://github.com/notAI-tech/NudeNet/releases/download/v3.0/640m.onnx"
ANIME_MODEL_URL = "https://huggingface.co/deepghs/anime_real_cls/resolve/main/mobilenetv3_v1.4_dist/model.onnx?download=true"
CLOTHING_TAGGER_URL = "https://huggingface.co/SmilingWolf/wd-vit-large-tagger-v3/resolve/main/model.onnx?download=true"
CLOTHING_TAGS_URL = "https://huggingface.co/SmilingWolf/wd-vit-large-tagger-v3/resolve/main/selected_tags.csv?download=true"

# Swimsuit/Clothing tags for primary style detection
STYLE_TAG_MAP = {
    '水着': [
        'swimsuit', 'bikini', 'one-piece swimsuit', 'school swimsuit', 
        'competition swimsuit', 'sling bikini', 'micro bikini', 'front-tie bikini', 
        'side-tie bikini', 'monokini', 'sukumizu', 'maillot', 'tankini',
        'bottomless swimsuit', 'collared swimsuit', 'striped swimsuit'
    ],
    '下着': [
        'underwear', 'bra', 'panties', 'lingerie', 'thong', 'undressing',
        'panties under leotard', 'bra visible', 'panties visible', 'lace-trimmed legwear'
    ],
    '制服': [
        'uniform', 'school uniform', 'serafuku', 'japanese school uniform', 'sailor uniform',
        'police uniform', 'nurse uniform', 'military uniform',
        'necktie', 'vest', 'blouse', 'shirt', 'ribbon', 'cardigan',
        'demon slayer uniform', 'haori'
    ],
    'メイド': [
        'maid', 'maid outfit', 'maid apron', 'maid uniform', 'maid headdress', 'apron'
    ],
    'ドレス/ワンピ': [
        'dress', 'wedding dress', 'sundress', 'nightgown', 'evening dress', 'prom dress'
    ],
    '和服': [
        'kimono', 'short kimono', 'yukata', 'haori', 'japanese clothes', 'obi', 'sash'
    ],
    'スカート': [
        'skirt', 'miniskirt', 'micro skirt', 'pleated skirt', 'pencil skirt', 'high-waist skirt'
    ],
    'ショートパンツ': [
        'shorts', 'short shorts', 'denim shorts', 'buruma', 'gym shorts'
    ],
    'シャツ/トップス': [
        'shirt', 't-shirt', 'top', 'blouse', 'sweater', 'hoodie', 'tank top', 'camisole',
        'off-shoulder shirt', 'halter top'
    ],
    'ズボン/パンツ': [
        'pants', 'jeans', 'trousers', 'leggings', 'slacks'
    ],
    '裸': [
        'nude', 'naked', 'topless', 'pussy', 'pubic hair', 'sex', 'hetero',
        'nipples', 'sex toy', 'dildo', 'bdsm', 'futanari', 'penis', 'uncensored', 'clitoris',
        'cum', 'cumdrip', 'bondage', 'masturbation', 'orgasm', 'ejaculation'
    ]
}

# UI Settings
UI_THEME = "Dark"
UI_COLOR_THEME = "blue"

# Color Definitions for GUI
# Category-specific color scheme (5-level for score-based columns)
CATEGORY_SCORE_COLORS = {
    'BREAST': {'SAFE': '#2ecc71', 'LOW_RISK': '#f1c40f', 'MODERATE': '#f39c12', 'HIGH_RISK': '#e67e22', 'UNSAFE': '#e74c3c', 'ERROR': 'gray'},
    'GENITALIA': {'SAFE': '#2ecc71', 'LOW_RISK': '#f1c40f', 'MODERATE': '#f39c12', 'HIGH_RISK': '#e67e22', 'UNSAFE': '#e74c3c', 'ERROR': 'gray'},
    'ANUS': {'SAFE': '#2ecc71', 'LOW_RISK': '#f1c40f', 'MODERATE': '#f39c12', 'HIGH_RISK': '#e67e22', 'UNSAFE': '#e74c3c', 'ERROR': 'gray'},
    'BUTTOCKS': {'SAFE': '#2ecc71', 'LOW_RISK': '#f1c40f', 'MODERATE': '#f39c12', 'HIGH_RISK': '#e67e22', 'UNSAFE': '#e74c3c', 'ERROR': 'gray'}
}

# Style-based color scheme (4-level for clothing-based columns)
STYLE_COLORS = {
    '裸': '#e74c3c',      # Red
    '下着': '#e67e22',    # Orange
    '水着': '#f1c40f',    # Yellow
    'その他': '#2ecc71'   # Green
}
