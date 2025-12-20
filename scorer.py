# -*- coding: utf-8 -*-
"""
chk-NudeNet-local - Scorer
Categorization and Scoring logic
"""

from typing import List, Dict, Any
from dataclasses import dataclass
from config import CATEGORY_MAP, THRESHOLDS, VERDICT_ICONS

@dataclass
class CategoryScore:
    display_score: float  # Displayed in the UI (max, average, etc.)
    max_score: float      # Used for total score calculation (usually max)
    label_info: str = ""  # Special string for UI (like Face gender)

@dataclass
class ScoringResult:
    categories: Dict[str, CategoryScore]
    total_score: float  # 0 to 100
    verdict: str
    verdict_icon: str
    labels_summary: str
    primary_style: str = "着衣"  # e.g., 裸, 水着, 下着, スカート, 着衣
    all_tags: str = ""         # Full list of detected WD14 tags

class Scorer:
    def __init__(self):
        self.category_map = CATEGORY_MAP
        self.thresholds = THRESHOLDS

    def score(self, analysis_result: Dict[str, Any]) -> ScoringResult:
        """
        Score NudeNet detections based on categories
        """
        detections = analysis_result.get('detections', [])
        style = analysis_result.get('style', {'anime': 0.0, 'real': 0.0})
        label_max_scores = {}
        for det in detections:
            label = det['label']
            score = det['score']
            if label not in label_max_scores or score > label_max_scores[label]:
                label_max_scores[label] = score

        category_results = {}
        for cat in ['FEMALE_BREAST', 'GENITALIA', 'ANUS', 'BUTTOCKS']:
            labels = self.category_map.get(cat, [])
            val = max([label_max_scores.get(l, 0.0) for l in labels]) if labels else 0.0
            category_results[cat] = CategoryScore(max_score=val, display_score=val)

        b_val = max(label_max_scores.get('BELLY_EXPOSED', 0.0), label_max_scores.get('BELLY_COVERED', 0.0))
        f_val = max(label_max_scores.get('FEET_EXPOSED', 0.0), label_max_scores.get('FEET_COVERED', 0.0))
        a_val = max(label_max_scores.get('ARMPITS_EXPOSED', 0.0), label_max_scores.get('ARMPITS_COVERED', 0.0))
        avg_other = (b_val + f_val + a_val) / 3.0
        max_other = max(b_val, f_val, a_val)
        category_results['OTHER_REGIONS'] = CategoryScore(max_score=max_other, display_score=avg_other)

        f_face = label_max_scores.get('FACE_FEMALE', 0.0)
        m_face = label_max_scores.get('FACE_MALE', 0.0)
        style_label = "アニメ" if style['anime'] > style['real'] else "実写"
        style_score = max(style['anime'], style['real'])
        if f_face >= m_face and f_face > 0:
            face_info = f"女({f_face:.1f}),{style_label}({style_score:.1f})"
            face_max = f_face
        elif m_face > f_face:
            face_info = f"男({m_face:.1f}),{style_label}({style_score:.1f})"
            face_max = m_face
        else:
            face_info = f"{style_label}({style_score:.1f})"
            face_max = style_score
        category_results['FACE'] = CategoryScore(max_score=face_max, display_score=face_max, label_info=face_info)

        # Verdict calculation
        restricted_regions = ['FEMALE_BREAST', 'GENITALIA', 'ANUS']
        relevant_vals = [category_results[cat].max_score for cat in restricted_regions]
        max_any_score = max(relevant_vals) if relevant_vals else 0.0
        total_score = round(max_any_score * 100, 1)

        verdict = 'SAFE'
        if total_score >= self.thresholds['UNSAFE'] * 100:
            verdict = 'UNSAFE'
        elif total_score >= self.thresholds['HIGH_RISK'] * 100:
            verdict = 'HIGH_RISK'
        elif total_score >= self.thresholds['MODERATE'] * 100:
            verdict = 'MODERATE'
        elif total_score >= self.thresholds['LOW_RISK'] * 100:
            verdict = 'LOW_RISK'

        verdict_icon = VERDICT_ICONS.get(verdict, '❓')
        
        # Primary Style Detection (WD14-based)
        from config import STYLE_TAG_MAP
        clothing_tags = analysis_result.get('clothing_tags', {}) if analysis_result else {}
        
        # Obscene Tag List
        obscene_tags = STYLE_TAG_MAP.get('裸', [])
        
        # Initial Style
        primary_style = "着衣"
        best_score = 0.0

        # 1. Absolute Priority: High Confidence Obscene/Nude Tags (Aggressive Override)
        # Priority 1a: Nipples (>=92%) or Pussy (>=90%) -> 裸
        n_score = clothing_tags.get('nipples', 0.0)
        p_score = clothing_tags.get('pussy', 0.0)
        if n_score >= 0.92:
            primary_style = f"裸({n_score*100:.1f}%)"
            best_score = n_score
        elif p_score >= 0.90:
            primary_style = f"裸({p_score*100:.1f}%)"
            best_score = p_score
        
        # Priority 1b: High Confidence Underwear (>=90%) -> 下着
        # (This should override "Japanese Clothes" or other clothing if confidence is very high)
        elif clothing_tags.get('panties', 0.0) >= 0.90:
            s = clothing_tags.get('panties')
            primary_style = f"下着({s*100:.1f}%)"
            best_score = s
        elif clothing_tags.get('underwear', 0.0) >= 0.90:
            s = clothing_tags.get('underwear')
            primary_style = f"下着({s*100:.1f}%)"
            best_score = s

        # 2. Secondary Priority: Obscene Keywords (BDSM, Cum, etc.)
        if best_score == 0.0:
            max_obscene_score = 0.0
            obscene_found_count = 0
            for tag in obscene_tags:
                score = clothing_tags.get(tag, 0.0)
                if score > 0.4:
                    obscene_found_count += 1
                    if score > max_obscene_score:
                        max_obscene_score = score
            
            # If multiple obscene tags or one very high confidence obscene tag
            if max_obscene_score > 0.85 or (obscene_found_count >= 2 and max_obscene_score > 0.5):
                primary_style = f"裸({max_obscene_score*100:.1f}%)"
                best_score = max_obscene_score

        # 3. Regular Styles and fallback
        if best_score == 0.0:
            # Check regular Nipples/Pussy with lower threshold
            if max(n_score, p_score) > 0.6:
                primary_style = f"裸({max(n_score, p_score)*100:.1f}%)"
                best_score = max(n_score, p_score)
            else:
                # Regular Styles (Japanese clothes, etc.)
                for style_name, tags in STYLE_TAG_MAP.items():
                    if style_name == '裸': continue
                    style_max = max([clothing_tags.get(t, 0.0) for t in tags] + [0.0])
                    if style_max > 0.5 and style_max > best_score:
                        best_score = style_max
                        primary_style = f"{style_name}({style_max*100:.1f}%)"

        # 4. Final Fallback to NudeNet Score if NudeNet thinks it's UNSAFE but WD14 missed it
        if total_score > 70 and "裸" not in primary_style:
            primary_style = f"裸({total_score:.1f}%)"

        # Formatting summary
        filtered_labels = {l: s for l, s in label_max_scores.items() if not l.startswith('FACE_')}
        simplified_labels = []
        for l, s in filtered_labels.items():
            simple_l = l.replace('FEMALE_', '').replace('MALE_', '').replace('MAN_', '').replace('_EXPOSED', '')
            simplified_labels.append((simple_l, s))
        sorted_labels = sorted(simplified_labels, key=lambda x: x[1], reverse=True)
        details_list = [f"{l}({s*100:.1f}%)" for l, s in sorted_labels[:5] if s > 0.1]
        
        # --- Check for "鬼滅の刃" (Demon Slayer) Special Label ---
        ds_tags = ['demon slayer uniform', 'weapon', 'sword', 'japanese clothes']
        # Condition: If 3 or more of the above tags have confidence > 0.6
        if len([t for t in ds_tags if clothing_tags.get(t, 0.0) > 0.6]) >= 3:
            details_list.insert(0, "【鬼滅の刃】")
            
        summary = ", ".join(details_list)
        
        sorted_clothing = sorted(clothing_tags.items(), key=lambda x: x[1], reverse=True)
        all_tags_str = ", ".join([f"{t}({s*100:.1f}%)" for t, s in sorted_clothing[:30]])

        return ScoringResult(
            categories=category_results, total_score=total_score, verdict=verdict,
            verdict_icon=verdict_icon, labels_summary=summary, primary_style=primary_style,
            all_tags=all_tags_str
        )
