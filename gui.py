# -*- coding: utf-8 -*-
"""
chk-NudeNet-local - Premium GUI (Japanese Path Support + Column-based Color)
Modern GUI based on CustomTkinter with Japanese path support and improved color scheme
"""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import customtkinter as ctk
import threading
import queue
import time
import csv
import json
import webbrowser
try:
    import psutil
    import GPUtil
    HAS_MONITOR = True
except ImportError:
    HAS_MONITOR = False
from pathlib import Path
from PIL import Image, ImageOps
from typing import List, Dict, Any, Optional

from config import SUPPORTED_EXTENSIONS, VERDICT_ICONS, UI_THEME, UI_COLOR_THEME, CATEGORY_MAP, CATEGORY_SCORE_COLORS, STYLE_COLORS
from nudenet_client import NudeNetClient, NudeNetClientError
from scorer import Scorer, ScoringResult
from file_handler import FileHandler

# Design Setup
ctk.set_appearance_mode(UI_THEME)
ctk.set_default_color_theme(UI_COLOR_THEME)

class ReferenceWindow(ctk.CTkToplevel):
    """Graphical Reference Window for NudeNet Categories"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title("NudeNet 判定カテゴリ・ガイド")
        self.geometry("900x700")
        self.attributes("-topmost", True)
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.scroll_frame = ctk.CTkScrollableFrame(self)
        self.scroll_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")

        ctk.CTkLabel(self.scroll_frame, text="ローカル NudeNet 判定カテゴリ一覧 (改良版)", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=(10, 20))

        # Categories Table
        table_frame = ctk.CTkFrame(self.scroll_frame)
        table_frame.pack(fill="x", padx=10, pady=10)

        headers = ["カテゴリ名", "判定基準 (ラベル)", "解説 / 判定の仕組み"]
        h_frame = ctk.CTkFrame(table_frame, fg_color="#333")
        h_frame.pack(fill="x")
        ctk.CTkLabel(h_frame, text=headers[0], font=ctk.CTkFont(weight="bold"), width=150).grid(row=0, column=0, padx=5, pady=5)
        ctk.CTkLabel(h_frame, text=headers[1], font=ctk.CTkFont(weight="bold"), width=300, anchor="w").grid(row=0, column=1, padx=5, pady=5, sticky="w")
        ctk.CTkLabel(h_frame, text=headers[2], font=ctk.CTkFont(weight="bold"), width=350, anchor="w").grid(row=0, column=2, padx=5, pady=5, sticky="w")

        ref_info = [
            ("胸 (BREAST)", "BREAST_EXPOSED", "女性の露出した乳部。"),
            ("性器 (GENITALIA)", "男女すべての隠部露出", "局部、陰毛、挿入等の直接的な露出。"),
            ("肛門 (ANUS)", "ANUS_EXPOSED", "肛門部分の直接的な露出。"),
            ("お屁股 (BUTTOCKS)", "BUTTOCKS_EXPOSED", "お屁股の直接的な露出。"),
            ("腹部/足/脇(Avg)", "BELLY, FEET, ARMPITS", "主要3部位の露出スコアの平均値。"),
            ("スタイル (WD14)", "10,000種以上のタグ", "高精度AI (WD14 V3) による衣服や状態の特定。"),
            ("性別,アニメ/実写", "FACE_FEMALE, etc.", "顔認識による性別判定と実写/アニメ分類。")
        ]

        for name, lbls, logic in ref_info:
            f = ctk.CTkFrame(table_frame, fg_color="transparent")
            f.pack(fill="x")
            ctk.CTkLabel(f, text=name, width=150, font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=5, pady=5)
            ctk.CTkLabel(f, text=lbls, width=300, anchor="w").grid(row=0, column=1, padx=5, pady=5, sticky="w")
            ctk.CTkLabel(f, text=logic, width=350, anchor="w", justify="left").grid(row=0, column=2, padx=5, pady=5, sticky="w")

        info_text = """
【判定ロジックの見直し (2025.12 改良版)】
1. スタイル判定 (最優先):
   ・WD14 V3 (ViT-Large) モデルにより、1万以上のタグから「水着」「制服」「下着」等を特定します。
   ・数値(%)はAIの確信度を表します。

2. NudeNetフォールバック (二次判定):
   ・衣類タグが見つからない場合、NudeNetの「部位が覆われている(COVERED)」判定をチェックします。
   ・これにより、タグが検知しにくいポーズでも「水着/下着」として判定可能です。

3. 部位別解析:
   ・各部位の数値は 0.0〜1.0 (100%) の露出スコアを表します。
   ・「着衣(100%)」は、NSFWリスクが極めて低い状態を示します。

 【アニメ/実写判定】
 ・WD14 V3タグ（anime, realistic等）の検出結果を優先し、NudeNetの判定を補正します。

 【性別判定 (WD14 V3)】
 ・NudeNetで顔が検出されない場合、WD14モデルによるタグ（1girl/1boy等）を使用して性別を推定します。
        """
        ctk.CTkLabel(self.scroll_frame, text=info_text, justify="left", font=ctk.CTkFont(size=12), text_color="#bdc3c7").pack(pady=20, padx=20, anchor="w")

class NudeNetGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("chk-NudeNet-local (On-Premise NSFW Checker) - 改良版")
        self.root.geometry("1550x850")

        # Instances
        try:
            self.client = NudeNetClient()
        except NudeNetClientError as e:
            messagebox.showerror("初期化エラー", str(e))
            self.client = None

        self.scorer = Scorer()
        self.file_handler = FileHandler()
        
        self.processing_queue = queue.Queue()
        self.is_running = False
        self.results = []
        
        self._setup_layout()

    def _setup_layout(self):
        # Grid Configuration
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        # --- Sidebar ---
        self.sidebar_frame = ctk.CTkFrame(self.root, width=320, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="NSFW Check", font=ctk.CTkFont(size=22, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.select_file_btn = ctk.CTkButton(self.sidebar_frame, text="ファイルを個別に選択", command=self._select_files)
        self.select_file_btn.grid(row=1, column=0, padx=20, pady=10)

        self.select_folder_btn = ctk.CTkButton(self.sidebar_frame, text="フォルダを一括選択", command=self._select_folder)
        self.select_folder_btn.grid(row=2, column=0, padx=20, pady=10)

        self.recursive_switch = ctk.CTkSwitch(self.sidebar_frame, text="サブフォルダも含める")
        self.recursive_switch.grid(row=3, column=0, padx=20, pady=10)

        # --- Sidebar Preview Panel (Expanded) ---
        self.preview_frame = ctk.CTkFrame(self.sidebar_frame, height=650, corner_radius=10, fg_color="#1a1a1a")
        self.preview_frame.grid(row=4, column=0, padx=15, pady=10, sticky="nsew")
        self.preview_frame.grid_propagate(False)
        
        self.preview_label = ctk.CTkLabel(self.preview_frame, text="プレビュー", font=ctk.CTkFont(size=13, weight="bold"), text_color="#3498db")
        self.preview_label.pack(pady=(5, 2))
        
        # Container for image to keep aspect ratio centered
        self.img_container = ctk.CTkFrame(self.preview_frame, fg_color="transparent", height=350)
        self.img_container.pack(fill="x", padx=5, pady=2)
        self.img_container.pack_propagate(False)

        self.preview_img_label = ctk.CTkLabel(self.img_container, text="画像を選択", text_color="#7f8c8d", font=ctk.CTkFont(size=11))
        self.preview_img_label.place(relx=0.5, rely=0.5, anchor="center")
        
        # Caption Detail Area
        self.caption_box = ctk.CTkTextbox(self.preview_frame, font=("Segoe UI Emoji", 12), fg_color="#0d0d0d")
        self.caption_box.pack(fill="both", expand=True, padx=10, pady=(5, 10))
        self.caption_box.configure(state="disabled")

        # Weights: Give Row 4 (Preview) weight to expand if needed, but fixed height 650
        self.sidebar_frame.grid_rowconfigure(4, weight=1) 
        self.sidebar_frame.grid_rowconfigure(5, weight=0)

        # Row 5+ are now empty or used for spacing
        self.sidebar_frame.grid_rowconfigure(5, weight=0)

        # --- Main Content ---
        self.main_content = ctk.CTkFrame(self.root, corner_radius=10)
        self.main_content.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        self.main_content.grid_columnconfigure(0, weight=1)
        self.main_content.grid_rowconfigure(0, weight=0) # Top Control
        self.main_content.grid_rowconfigure(1, weight=0) # Progress
        self.main_content.grid_rowconfigure(2, weight=1) # Table (Maximized)
        self.main_content.grid_rowconfigure(3, weight=0) # Bottom Control

        # Control Buttons
        self.top_ctrl = ctk.CTkFrame(self.main_content, height=50, fg_color="transparent")
        self.top_ctrl.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        
        self.start_btn = ctk.CTkButton(self.top_ctrl, text="▶ スキャンを開始", font=ctk.CTkFont(size=15, weight="bold"), 
                                      fg_color="#27ae60", hover_color="#2ecc71", command=self._start_analysis)
        self.start_btn.pack(side=tk.LEFT, padx=5)

        self.stop_btn = ctk.CTkButton(self.top_ctrl, text="■ 停止", font=ctk.CTkFont(size=15, weight="bold"),
                                     fg_color="#e67e22", hover_color="#d35400", command=self._stop_analysis)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        self.stop_btn.configure(state="disabled")

        self.clear_btn = ctk.CTkButton(self.top_ctrl, text="リストをクリア", fg_color="#c0392b", hover_color="#e74c3c", command=self._clear_list)
        self.clear_btn.pack(side=tk.LEFT, padx=5)

        self.deselect_btn = ctk.CTkButton(self.top_ctrl, text="選択解除", width=80, fg_color="#34495e", hover_color="#7f8c8d", command=self._deselect_all)
        self.deselect_btn.pack(side=tk.LEFT, padx=5)

        self.status_box = ctk.CTkFrame(self.top_ctrl, corner_radius=5, fg_color="#34495e")
        self.status_box.pack(side=tk.RIGHT, padx=(10, 5))
        
        self.status_label = ctk.CTkLabel(self.status_box, text="ステータス: 待機中", font=ctk.CTkFont(weight="bold"), text_color="white")
        self.status_label.pack(side=tk.RIGHT, padx=10, pady=2)


        if HAS_MONITOR:
            # Relocated Performance Monitor (Horizontal)
            self.perf_frame = ctk.CTkFrame(self.top_ctrl, fg_color="transparent")
            self.perf_frame.pack(side=tk.LEFT, padx=20)
            
            # CPU
            f_cpu = ctk.CTkFrame(self.perf_frame, fg_color="transparent")
            f_cpu.pack(side=tk.LEFT, padx=10)
            self.cpu_usage_label = ctk.CTkLabel(f_cpu, text="CPU: --%", font=ctk.CTkFont(size=10))
            self.cpu_usage_label.pack()
            self.cpu_usage_bar = ctk.CTkProgressBar(f_cpu, height=6, width=100)
            self.cpu_usage_bar.pack()
            self.cpu_usage_bar.set(0)
            
            # GPU
            f_gpu = ctk.CTkFrame(self.perf_frame, fg_color="transparent")
            f_gpu.pack(side=tk.LEFT, padx=10)
            self.gpu_usage_label = ctk.CTkLabel(f_gpu, text="GPU: --%", font=ctk.CTkFont(size=10))
            self.gpu_usage_label.pack()
            self.gpu_usage_bar = ctk.CTkProgressBar(f_gpu, height=6, width=100)
            self.gpu_usage_bar.pack()
            self.gpu_usage_bar.set(0)
            
            # VRAM
            f_vram = ctk.CTkFrame(self.perf_frame, fg_color="transparent")
            f_vram.pack(side=tk.LEFT, padx=10)
            self.vram_usage_label = ctk.CTkLabel(f_vram, text="VRAM: --%", font=ctk.CTkFont(size=10))
            self.vram_usage_label.pack()
            self.vram_usage_bar = ctk.CTkProgressBar(f_vram, height=6, width=100)
            self.vram_usage_bar.pack()
            self.vram_usage_bar.set(0)

            self._update_resource_usage()

        # Progress Bar
        self.progress_bar = ctk.CTkProgressBar(self.main_content)
        self.progress_bar.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 10))
        self.progress_bar.set(0)

        # Table
        self.table_frame = tk.Frame(self.main_content, bg="#2b2b2b")
        # Maximized Height: Reduce pady to allow list to stretch
        self.table_frame.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 2))
        
        try:
            style = ttk.Style()
            style.theme_use("default")
            style.configure("Treeview", background="#2b2b2b", foreground="white", fieldbackground="#2b2b2b", borderwidth=0, rowheight=35)
            style.map("Treeview", background=[('selected', '#3498db')])
            style.configure("Treeview.Heading", background="#333", foreground="white", relief="flat")
        except: pass

        # Columns
        # FullPath and AllTags are HIDDEN
        cols = ["Filename", "Status", "ReportStyle", "BREAST", "GENITALIA", "ANUS", "BUTTOCKS", "OTHER_REGIONS", "STYLE", "Details", "FullPath", "AllTags"]
        display_names = ["ファイル名", "判定(スコア)", "スタイル", "胸", "性器", "肛門", "お尻", "腹部/足/脇(Avg)", "性別,アニメ/実写", "詳細ラベル"]
        
        self.tree = ttk.Treeview(self.table_frame, columns=cols, show='headings', selectmode="extended")

        col_widths = {
            "Filename": 180, "Status": 110, "ReportStyle": 120,
            "BREAST": 55, "GENITALIA": 55, "ANUS": 55,
            "BUTTOCKS": 65, "OTHER_REGIONS": 120, "STYLE": 130,
            "Details": 450
        }
        for i, col in enumerate(cols):
            if col in ["FullPath", "AllTags"]:
                self.tree.column(col, width=0, stretch=False)
                continue
            
            self.tree.heading(col, text=display_names[i])
            # Only Allow Details and Style to stretch, others fixed
            stretch = True if col in ["Details", "STYLE", "ReportStyle"] else False
            self.tree.column(col, width=col_widths.get(col, 100), stretch=stretch, anchor=tk.CENTER if i > 0 and i < 9 else tk.W)

        scrollbar = ttk.Scrollbar(self.table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        h_scrollbar = ttk.Scrollbar(self.table_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscroll=scrollbar.set, xscroll=h_scrollbar.set)
        
        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")
        
        self.table_frame.grid_columnconfigure(0, weight=1)
        self.table_frame.grid_rowconfigure(0, weight=1)

        # --- Bottom Control (Footer) ---
        # Remove fixed height to allow auto-sizing and max list expansion
        self.bottom_ctrl = ctk.CTkFrame(self.main_content, fg_color="transparent")
        self.bottom_ctrl.grid(row=3, column=0, sticky="ew", padx=10, pady=(0, 5))

        # Buttons in bottom-right
        self.export_btn = ctk.CTkButton(self.bottom_ctrl, text="結果をエクスポート", width=120, fg_color="#2c3e50", command=self._export_results)
        self.export_btn.pack(side=tk.RIGHT, padx=5)

        self.ref_btn = ctk.CTkButton(self.bottom_ctrl, text="カテゴリ基準", width=100, fg_color="#34495e", command=self._show_reference)
        self.ref_btn.pack(side=tk.RIGHT, padx=5)

        # Bindings
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self.tree.bind("<Button-1>", self._handle_click_out)

        # Context Menu for deletion
        self.context_menu = tk.Menu(self.root, tearoff=0, bg="#333", fg="white", activebackground="#3498db")
        self.context_menu.add_command(label="選択した項目を削除", command=self._delete_selected)
        self.tree.bind("<Button-3>", self._show_context_menu)

        # Tags for Level-based coloring (Row-based fallback)
        levels = ['SAFE', 'LOW_RISK', 'MODERATE', 'HIGH_RISK', 'UNSAFE', 'ERROR']
        colors = {'SAFE': '#2ecc71', 'LOW_RISK': '#f1c40f', 'MODERATE': '#f39c12', 'HIGH_RISK': '#e67e22', 'UNSAFE': '#e74c3c', 'ERROR': 'gray'}
        
        for lvl in levels:
            self.tree.tag_configure(f"level_{lvl}", foreground=colors[lvl])
        
        # Helper to determine the overall level for a result
        def determine_overall_level(total_score, primary_style, categories):
            # 1. Check if UNSAFE
            if total_score >= 80 or "裸" in primary_style:
                return "UNSAFE"
            
            # 2. Check if HIGH_RISK
            if total_score >= 60 or "下着" in primary_style:
                return "HIGH_RISK"
            
            # 3. Check if MODERATE
            if total_score >= 40 or "水着" in primary_style:
                return "MODERATE"
            
            # 4. Check if LOW_RISK
            if total_score >= 20:
                return "LOW_RISK"
            
            return "SAFE"

        self.determine_overall_level = determine_overall_level

    def _update_status(self, text, state="idle"):
        """Update status label with color-coded background box"""
        colors = {
            "idle": "#34495e",    # Dark blue-gray
            "running": "#2980b9", # Bright blue
            "done": "#27ae60",    # Green
            "error": "#c0392b",   # Red
            "info": "#34495e"     # Grayish blue
        }
        self.status_box.configure(fg_color=colors.get(state, "#34495e"))
        self.status_label.configure(text=text)

    def _show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            if item not in self.tree.selection():
                self.tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)

    def _delete_selected(self):
        selected = self.tree.selection()
        if not selected: return
        for item in selected:
            self.tree.delete(item)
        self.results = [r for r in self.results if r['id'] not in selected]
        self._update_status(f"削除完了: {len(selected)} 件", "info")

    def _select_files(self):
        """Select files with Japanese path support"""
        files = filedialog.askopenfilenames(title="画像を選択", filetypes=[("画像ファイル", "*.jpg *.jpeg *.png *.gif *.webp *.bmp")])
        if files:
            for f in files:
                try:
                    f_path = Path(f)
                    resolved_path = f_path.resolve()
                    self.tree.insert("", tk.END, values=(f_path.name, "-", "-", "-", "-", "-", "-", "-", "-", "-", str(resolved_path)))
                except Exception as e:
                    self.tree.insert("", tk.END, values=(Path(f).name, "-", "-", "-", "-", "-", "-", "-", "-", "-", str(f)))
            self._update_status(f"準備完了: {len(self.tree.get_children())} 枚", "info")

    def _select_folder(self):
        """Select folder with Japanese path support"""
        folder = filedialog.askdirectory(title="フォルダを選択")
        if folder:
            try:
                folder_path = Path(folder)
                resolved_folder = folder_path.resolve()
                images = self.file_handler.collect_images(resolved_folder, self.recursive_switch.get())
                for f in images:
                    try:
                        resolved_path = f.resolve()
                        self.tree.insert("", tk.END, values=(f.name, "-", "-", "-", "-", "-", "-", "-", "-", "-", str(resolved_path)))
                    except Exception as e:
                        self.tree.insert("", tk.END, values=(f.name, "-", "-", "-", "-", "-", "-", "-", "-", "-", str(f)))
            except Exception as e:
                images = self.file_handler.collect_images(Path(folder), self.recursive_switch.get())
                for f in images:
                    self.tree.insert("", tk.END, values=(f.name, "-", "-", "-", "-", "-", "-", "-", "-", "-", str(f)))
            self._update_status(f"準備完了: {len(self.tree.get_children())} 枚", "info")

    def _clear_list(self):
        if self.is_running: return
        items = self.tree.get_children()
        if not items:
            messagebox.showwarning("警告", "リストが空です。")
            return
        if not messagebox.askyesno("確認", "リストのすべての項目をクリアしますか？"):
            return
        for item in items: self.tree.delete(item)
        self.results = []
        self.progress_bar.set(0)
        self._clear_preview()
        self._update_status("ステータス: 待機中", "idle")

    def _deselect_all(self):
        self.tree.selection_remove(self.tree.selection())
        self._clear_preview()

    def _handle_click_out(self, event):
        """Deselect if clicked in an empty area of the treeview"""
        if self.tree.identify_row(event.y) == "":
            self._deselect_all()

    def _clear_preview(self):
        self.preview_img_label.configure(image=None, text="画像を選択して下さい")
        self.caption_box.configure(state="normal")
        self.caption_box.delete("1.0", tk.END)
        self.caption_box.configure(state="disabled")
        self.current_preview_path = None

    def _on_tree_select(self, event):
        """Update preview image and captions when a row is selected"""
        selected = self.tree.selection()
        if not selected:
            self._clear_preview()
            return
            
        # Get data from selected item
        item = selected[0]
        values = self.tree.item(item, 'values')
        if not values or len(values) < 11: return
        
        path_str = values[10]
        style_text = values[2]
        details_text = values[9]
        sex_style = values[8]
        all_tags_text = values[11] if len(values) > 11 else ""

        # Configure tags for colors if not already done
        if not hasattr(self, "_tags_configured"):
            self.caption_box.tag_config("red", foreground="#e74c3c")   # Red
            self.caption_box.tag_config("yellow", foreground="#f1c40f") # Yellow
            self.caption_box.tag_config("green", foreground="#2ecc71")  # Green
            self.caption_box.tag_config("default", foreground="white")
            self._tags_configured = True

        # Update Caption Box
        self.caption_box.configure(state="normal")
        self.caption_box.delete("1.0", tk.END)
        
        
        # summary_top = f"【判定スタイル】\n{style_text}\n"
        # if sex_style != "-":
        #    summary_top += f"{sex_style}\n"
        # Removed as per user request, starting directly with Details
        summary_top = "【詳細カテゴリ】\n"
        
        self.caption_box.insert("end", summary_top)

        # Helper to get data
        def get_detail_data(text_line):
            # Returns (icon_char, color_tag, text_content)
            try:
                if "(" not in text_line or "%)" not in text_line:
                    return None, None, text_line
                    
                label_part = text_line.split("(")[0]
                score_part = text_line.split("(")[-1].replace("%)", "")
                score = float(score_part) / 100.0
                
                # Label Mapping
                jp_label = label_part
                if "BREAST" in label_part: jp_label = "胸"
                elif "GENITALIA" in label_part: jp_label = "性器"
                elif "ANUS" in label_part: jp_label = "肛門"
                elif "BUTTOCKS" in label_part: jp_label = "お尻"
                elif "BELLY" in label_part: jp_label = "腹部"
                elif "FEET" in label_part: jp_label = "足"
                elif "ARMPITS" in label_part: jp_label = "脇"
                
                # Icon Logic
                if score >= 0.8: return "● ", "red", f"{jp_label}({score_part}%)"
                if score >= 0.4: return "● ", "yellow", f"{jp_label}({score_part}%)"
                return "● ", "green", f"{jp_label}({score_part}%)"
            except: 
                return None, None, text_line

        details_lines = [line for line in details_text.split(', ') if line]
        
        if not details_lines or (len(details_lines) == 1 and details_lines[0] == "SAFE(0.0)"):
             self.caption_box.insert("end", "特になし\n")
        else:
            for line in details_lines:
                icon, color_tag, content = get_detail_data(line)
                if icon:
                    self.caption_box.insert("end", icon, color_tag)
                    self.caption_box.insert("end", f"{content}\n")
                else:
                    self.caption_box.insert("end", f"{line}\n")
        
        all_tags_lines = all_tags_text.replace(', ', '\n')
        self.caption_box.insert("end", f"\n【認知したすべてのタグ】\n{all_tags_lines}")
        
        self.caption_box.configure(state="disabled")

        if hasattr(self, 'current_preview_path') and self.current_preview_path == path_str:
            return
            
        self.current_preview_path = path_str
        self._update_preview(path_str)

    def _update_preview(self, path_str):
        try:
            path = Path(path_str)
            if not path.exists(): return
            
            # Use PIL to load and resize
            img = Image.open(path)
            original_size = img.size
            
            # Calculate aspect ratio manually to fit within sidebar container
            # Container width is fixed at sidebar width minus padding
            max_w = 280
            max_h = 250 # Safe height to avoid clipping
            
            ratio_w = max_w / original_size[0]
            ratio_h = max_h / original_size[1]
            scale = min(ratio_w, ratio_h)
            
            new_w = int(original_size[0] * scale)
            new_h = int(original_size[1] * scale)
            
            # Resize
            img = img.resize((new_w, new_h), Image.LANCZOS)
            
            # Use the resized image's own size for the CTkImage
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(img.width, img.height))
            
            # File info
            file_size_mb = path.stat().st_size / (1024 * 1024)
            # Display ORIGINAL dimensions
            info_text = f"プレビュー（{original_size[0]}x{original_size[1]}）：{file_size_mb:.1f}MB"
            
            self.preview_label.configure(text=info_text)
            self.preview_img_label.configure(image=ctk_img, text="")
            self.preview_img_label.image = ctk_img # Keep reference
            
        except Exception as e:
            print(f"Preview error: {e}")
            self._clear_preview()
            self.preview_img_label.configure(text="プレビュー失敗")

    def _update_resource_usage(self):
        """Update CPU/GPU usage metrics periodically"""
        if not HAS_MONITOR: return
        
        try:
            # CPU Usage
            cpu_percent = psutil.cpu_percent()
            self.cpu_usage_label.configure(text=f"CPU: {cpu_percent:.1f}%")
            self.cpu_usage_bar.set(cpu_percent / 100.0)
            
            # GPU Usage (NVIDIA)
            gpus = GPUtil.getGPUs()
            if gpus:
                gpu = gpus[0]
                gpu_load = gpu.load * 100
                vram_util = gpu.memoryUtil * 100
                self.gpu_usage_label.configure(text=f"GPU: {gpu_load:.1f}%")
                self.gpu_usage_bar.set(gpu.load)
                self.vram_usage_label.configure(text=f"VRAM: {vram_util:.1f}%")
                self.vram_usage_bar.set(gpu.memoryUtil)
            else:
                self.gpu_usage_label.configure(text="GPU: N/A")
                self.gpu_usage_bar.set(0)
                self.vram_usage_label.configure(text="VRAM: N/A")
                self.vram_usage_bar.set(0)
                
        except Exception as e:
            print(f"Usage monitor error: {e}")
            
        # Schedule next update (2 seconds)
        self.root.after(2000, self._update_resource_usage)

    def _show_reference(self):
        ReferenceWindow(self.root)

    def _start_analysis(self):
        if self.is_running or not self.client: return
        items = self.tree.get_children()
        if not items:
            messagebox.showerror("エラー", "読み込まれた画像がありません。")
            return

        self.is_running = True
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self._update_status("ステータス: スキャン中...", "running")
        
        threading.Thread(target=self._worker, daemon=True).start()
        self.root.after(100, self._process_queue)

    def _stop_analysis(self):
        if not self.is_running: return
        self.is_running = False
        self._update_status("ステータス: 停止中...", "error")
        
        # Re-enable start button
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        
        # Clear the processing queue
        while not self.processing_queue.empty():
            try:
                self.processing_queue.get_nowait()
            except queue.Empty:
                break

    def _worker(self):
        items = self.tree.get_children()
        for item in items:
            if not self.is_running: break
            values = self.tree.item(item, 'values')
            path = Path(values[-1])
            try:
                detections = self.client.analyze_image(path)
                result = self.scorer.score(detections)
                self.processing_queue.put(('success', item, result, path))
            except Exception as e:
                self.processing_queue.put(('error', item, str(e), path))
        self.processing_queue.put(('done', None, None, None))

    def _restore_ui_state(self):
        """Restore UI state after processing"""
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")

    def _process_queue(self):
        try:
            while True:
                msg_type, item, data, path = self.processing_queue.get_nowait()
                if msg_type == 'done':
                    self.is_running = False
                    self._restore_ui_state()
                    self.status_label.configure(text="ステータス: 完了")
                    return

                total = len(self.tree.get_children())
                current = len(self.results) + 1
                self.progress_bar.set(current / total)
                
                if msg_type == 'success':
                    sr = data
                    c = sr.categories
                    
                    # Determine overall level for the row color
                    overall_lvl = self.determine_overall_level(sr.total_score, sr.primary_style, c)
                    tag = f"level_{overall_lvl}"
                    
                    status_str = f"{sr.verdict}({sr.total_score:.1f})"
                    
                    self.tree.item(item, values=(
                        path.name, status_str,
                        sr.primary_style,
                        f"{c['FEMALE_BREAST'].display_score:.1f}", 
                        f"{c['GENITALIA'].display_score:.1f}",
                        f"{c['ANUS'].display_score:.1f}", 
                        f"{c['BUTTOCKS'].display_score:.1f}", 
                        f"{c['OTHER_REGIONS'].display_score:.2f}", 
                        c['FACE'].label_info,
                        sr.labels_summary, str(path), sr.all_tags
                    ), tags=(tag,))
                    
                    self.results.append({'id': item, 'filename': path.name, 'score': sr.total_score, 'verdict': sr.verdict, 'data': sr, 'path': str(path)})
                else:
                    # Error case
                    self.tree.item(item, values=(path.name, "Error", "Error", "-", "-", "-", "-", "-", "-", str(data), str(path)), tags=('level_ERROR',))
                    self.results.append({'id': item, 'filename': path.name, 'score': 0, 'verdict': 'ERROR', 'path': str(path)})
        except queue.Empty: pass
        
        if self.is_running or not self.processing_queue.empty():
            self.root.after(100, self._process_queue)
        else:
            self.is_running = False
            self._restore_ui_state()
            self._update_status("ステータス: 完了", "done")

    def _export_results(self):
        if not self.results: return
        file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv"), ("JSON", "*.json")])
        if not file_path: return
        try:
            p = Path(file_path)
            if p.suffix == '.json':
                serializable_results = []
                for r in self.results:
                    if r['verdict'] == 'ERROR':
                        serializable_results.append(r)
                        continue
                    sr = r['data']
                    serializable_results.append({
                        'filename': r['filename'], 'score': r['score'], 'verdict': r['verdict'],
                        'categories': {k: v.display_score for k, v in sr.categories.items()},
                        'labels': sr.labels_summary, 'path': r['path']
                    })
                with open(p, 'w', encoding='utf-8') as f: json.dump(serializable_results, f, ensure_ascii=False, indent=2)
            else:
                with open(p, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.writer(f)
                    writer.writerow(["ファイル名", "総合スコア", "判定", "胸", "性器", "肛門", "お屁股", "腹部/足/脇", "スタイル", "詳細", "パス"])
                    for r in self.results:
                        if r['verdict'] == 'ERROR':
                            writer.writerow([r['filename'], 0, "ERROR", "", "", "", "", "", "", "", r['path']])
                            continue
                        sr = r['data']
                        c = sr.categories
                        writer.writerow([
                            r['filename'], r['score'], r['verdict'],
                            c['FEMALE_BREAST'].display_score, c['GENITALIA'].display_score, c['ANUS'].display_score, c['BUTTOCKS'].display_score,
                            c['OTHER_REGIONS'].display_score, sr.primary_style, sr.labels_summary, r['path']
                        ])
            messagebox.showinfo("成功", f"エクスポート完了: {p.name}")
        except Exception as e: messagebox.showerror("エラー", f"失敗: {e}")

def launch_gui():
    root = ctk.CTk()
    app = NudeNetGUI(root)
    root.mainloop()

if __name__ == "__main__":
    launch_gui()
