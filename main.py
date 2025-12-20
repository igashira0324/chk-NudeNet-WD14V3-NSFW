# -*- coding: utf-8 -*-
"""
chk-NudeNet-local - Main Entry Point
Supports CLI and GUI
"""

import argparse
import sys
from pathlib import Path
from typing import List, Dict, Any

from file_handler import FileHandler
from nudenet_client import NudeNetClient, NudeNetClientError
from scorer import Scorer
from gui import launch_gui
from config import VERDICT_ICONS

try:
    from colorama import init, Fore, Style
    init()
    HAS_COLORAMA = True
except ImportError:
    HAS_COLORAMA = False
    class Fore: RED = GREEN = YELLOW = CYAN = WHITE = RESET = ''
    class Style: BRIGHT = RESET_ALL = ''

def print_result(filename: str, result: Any):
    """Print a single result to console"""
    color = {
        'SAFE': Fore.GREEN,
        'LOW_RISK': Fore.YELLOW,
        'MODERATE': Fore.YELLOW,
        'HIGH_RISK': Fore.RED,
        'UNSAFE': Fore.RED + Style.BRIGHT
    }.get(result.verdict, Fore.WHITE)
    
    icon = result.verdict_icon
    print(f"\n{Fore.CYAN}--- {filename} ---{Style.RESET_ALL}")
    status_str = f"{result.verdict}({result.total_score:.1f})"
    print(f"  Status: {color}{icon} {status_str}{Style.RESET_ALL}")
    print(f"  Style:  {Fore.WHITE}{result.primary_style}{Style.RESET_ALL}")
    print(f"  Details: {result.labels_summary}")

def main():
    parser = argparse.ArgumentParser(description='chk-NudeNet-local: On-Premise NSFW Checker')
    parser.add_argument('path', nargs='?', help='Path to image or directory')
    parser.add_argument('--gui', '-g', action='store_true', help='Launch GUI')
    parser.add_argument('--recursive', '-r', action='store_true', help='Recursive scan')
    
    args = parser.parse_args()

    # Launch GUI if requested or no path provided
    if args.gui or args.path is None:
        launch_gui()
        return

    # CLI Mode
    file_handler = FileHandler()
    try:
        target = file_handler.validate_path(args.path)
    except FileNotFoundError as e:
        print(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")
        sys.exit(1)

    images = file_handler.collect_images(target, args.recursive)
    if not images:
        print(f"No images found in {target}")
        return

    print(f"Processing {len(images)} images...")

    try:
        client = NudeNetClient()
        scorer = Scorer()
    except NudeNetClientError as e:
        print(f"{Fore.RED}Initialization Error: {e}{Style.RESET_ALL}")
        sys.exit(1)

    for img_path in images:
        try:
            analysis_result = client.analyze_image(img_path)
            res = scorer.score(analysis_result)
            print_result(img_path.name, res)
        except Exception as e:
            print(f"{Fore.RED}Error processing {img_path.name}: {e}{Style.RESET_ALL}")

if __name__ == "__main__":
    main()
