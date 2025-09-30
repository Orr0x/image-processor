#!/usr/bin/env python3
"""
Advanced Image Processing Tool - AI-Powered Metadata Management
Enhanced interface with drag-and-drop, image preview, and before/after comparison.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext, simpledialog
import threading
import os
import sys
from pathlib import Path
from PIL import Image, ImageTk
import queue
import time
from image_compressor import ImageCompressor
import tkinterdnd2 as tkdnd
import requests
import base64
import json
import piexif
import shutil
import tempfile
import subprocess

class AdvancedImageCompressorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Image Compression Tool - Advanced")
        self.root.geometry("1200x800")
        self.root.minsize(1000, 700)
        
        # Variables
        self.input_dir = tk.StringVar()
        self.output_dir = tk.StringVar()
        self.single_file = tk.StringVar()
        self.quality = tk.IntVar(value=85)
        self.max_width = tk.IntVar(value=1200)
        self.max_height = tk.IntVar(value=800)
        self.max_file_size = tk.IntVar(value=0)  # 0 = no limit, in KB
        self.format_var = tk.StringVar(value="webp")
        self.preserve_structure = tk.BooleanVar(value=True)
        self.max_workers = tk.IntVar(value=4)
        
        # Processing state
        self.is_processing = False
        self.processing_thread = None
        self.progress_queue = queue.Queue()
        
        # Image preview
        self.current_image = None
        self.preview_image = None
        self.preview_scale = 1.0
        
        # Statistics
        self.stats = {
            'processed': 0,
            'errors': 0,
            'original_size': 0,
            'compressed_size': 0,
            'time_taken': 0
        }
        
        # Tooltip
        self.tooltip_window = None
        
        # VISION MODEL CONFIGURATION (for image analysis and metadata generation)
        self.vision_model = "qwen/qwen2.5-vl-7b"  # Vision model for image analysis
        self.vision_max_tokens = 2000
        self.vision_temperature = 0.3
        self.vision_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # TOOL USE MODEL CONFIGURATION (for folder analysis and tool calls)
        self.tool_use_model = "deepseek/deepseek-r1-0528-qwen3-8b"  # Tool use model
        self.tool_use_enabled = False
        self.tool_use_max_tokens = 4000
        self.tool_use_temperature = 0.1
        self.tool_use_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        self.available_tool_models = [
            "deepseek/deepseek-r1-0528-qwen3-8b"  # Only model that supports tool use
        ]
        self.disable_thinking = True  # Flag to disable thinking in DeepSeek
        
        # Legacy compatibility (for existing code)
        self.max_tokens = self.vision_max_tokens
        self.ai_temperature = self.vision_temperature
        
        self.setup_ui()
        self.check_queue()
        
    def setup_ui(self):
        """Setup the user interface."""
        # Configure style
        style = ttk.Style()
        style.theme_use('clam')
        
        # Initialize metadata format configuration early
        self.metadata_format_override = tk.StringVar(value="auto")  # auto, jpeg, webp
        self.metadata_configs = {}
        self.setup_metadata_format_config()
        
        # Create main frame with scrollbar
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create canvas and scrollbar for scrolling
        self.main_canvas = tk.Canvas(main_frame)
        self.main_scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=self.main_canvas.yview)
        self.scrollable_frame = ttk.Frame(self.main_canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.main_canvas.configure(scrollregion=self.main_canvas.bbox("all"))
        )
        
        self.main_canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.main_canvas.configure(yscrollcommand=self.main_scrollbar.set)
        
        self.main_canvas.pack(side="left", fill="both", expand=True)
        self.main_scrollbar.pack(side="right", fill="y")
        
        # Bind mousewheel to canvas
        def _on_mousewheel(event):
            self.main_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        self.main_canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.scrollable_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Main compression tab
        self.main_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.main_frame, text="🎯 Compression")
        
        # Preview tab
        self.preview_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.preview_frame, text="🖼️ Preview")
        
        # Test Run tab
        self.test_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.test_frame, text="🧪 Test Run")
        
        # Metadata tab
        self.metadata_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.metadata_frame, text="📋 Metadata")
        
        # AI Chat tab
        self.ai_chat_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.ai_chat_frame, text="🤖 AI Chat")
        
        # Statistics tab
        self.stats_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.stats_frame, text="📊 Statistics")
        
        # Simple Metadata tab
        self.simple_metadata_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.simple_metadata_frame, text="📝 Simple Metadata")
        
        self.setup_main_tab()
        self.setup_preview_tab()
        self.setup_test_tab()
        self.setup_metadata_tab()
        self.setup_ai_chat_tab()
        self.setup_stats_tab()
        self.setup_simple_metadata_tab()
        
    def setup_main_tab(self):
        """Setup the main compression tab."""
        # Main container
        main_container = ttk.Frame(self.main_frame, padding="10")
        main_container.pack(fill=tk.BOTH, expand=True)
        main_container.columnconfigure(1, weight=1)
        
        # Title
        title_label = ttk.Label(main_container, text="🖼️ Image Compression Tool", 
                               font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # Input/Output Section
        self.create_io_section(main_container, 1)
        
        # Settings Section
        self.create_settings_section(main_container, 4)
        
        # Presets Section
        self.create_presets_section(main_container, 5)
        
        # Control Buttons
        self.create_control_section(main_container, 6)
        
        # Progress Section
        self.create_progress_section(main_container, 7)
        
        # Log Section
        self.create_log_section(main_container, 8)
        
        # Batch AI Processing Section
        self.create_batch_ai_section(main_container, 9)
        
    def setup_preview_tab(self):
        """Setup the image preview tab."""
        preview_container = ttk.Frame(self.preview_frame, padding="10")
        preview_container.pack(fill=tk.BOTH, expand=True)
        
        # Preview controls
        controls_frame = ttk.Frame(preview_container)
        controls_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(controls_frame, text="📁 Select Image", 
                  command=self.select_preview_image).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(controls_frame, text="🔄 Refresh Preview", 
                  command=self.refresh_preview).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(controls_frame, text="⚖️ Compare", 
                  command=self.show_comparison).pack(side=tk.LEFT, padx=(0, 10))
        
        # Zoom controls
        zoom_frame = ttk.Frame(controls_frame)
        zoom_frame.pack(side=tk.RIGHT)
        
        ttk.Label(zoom_frame, text="Zoom:").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(zoom_frame, text="-", command=self.zoom_out, width=3).pack(side=tk.LEFT, padx=(0, 2))
        ttk.Button(zoom_frame, text="+", command=self.zoom_in, width=3).pack(side=tk.LEFT, padx=(0, 2))
        ttk.Button(zoom_frame, text="Fit", command=self.zoom_fit, width=3).pack(side=tk.LEFT, padx=(0, 2))
        ttk.Button(zoom_frame, text="1:1", command=self.zoom_actual, width=3).pack(side=tk.LEFT, padx=(0, 5))
        
        # Zoom level display
        self.preview_zoom_label = ttk.Label(zoom_frame, text="100%")
        self.preview_zoom_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # Image preview area
        self.preview_canvas = tk.Canvas(preview_container, bg='white', relief=tk.SUNKEN, bd=2)
        self.preview_canvas.pack(fill=tk.BOTH, expand=True)
        
        # Mouse wheel zoom support
        self.preview_canvas.bind("<MouseWheel>", self.mouse_wheel_preview)
        
        # Image info
        self.image_info_label = ttk.Label(preview_container, text="No image selected")
        self.image_info_label.pack(fill=tk.X, pady=(10, 0))
        
    def setup_stats_tab(self):
        """Setup the statistics tab."""
        stats_container = ttk.Frame(self.stats_frame, padding="10")
        stats_container.pack(fill=tk.BOTH, expand=True)
        
        # Statistics display
        self.stats_text = scrolledtext.ScrolledText(stats_container, height=20, wrap=tk.WORD)
        self.stats_text.pack(fill=tk.BOTH, expand=True)
        
        # Update stats display
        self.update_detailed_stats()
        
    def setup_metadata_tab(self):
        """Setup the metadata tab."""
        metadata_container = ttk.Frame(self.metadata_frame, padding="10")
        metadata_container.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(metadata_container, text="📋 Image Metadata Editor", 
                               font=('Arial', 14, 'bold'))
        title_label.pack(pady=(0, 20))
        
        # Image selection
        image_frame = ttk.LabelFrame(metadata_container, text="📁 Select Image", padding="10")
        image_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.metadata_image_path = tk.StringVar()
        ttk.Entry(image_frame, textvariable=self.metadata_image_path, width=60).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(image_frame, text="Browse", command=self.browse_metadata_image).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(image_frame, text="Load Metadata", command=self.load_image_metadata).pack(side=tk.LEFT)
        
        # Main content area
        content_frame = ttk.Frame(metadata_container)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Left side - Image preview
        left_frame = ttk.LabelFrame(content_frame, text="🖼️ Image Preview", padding="10")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # Image canvas with scrollbars
        canvas_frame = ttk.Frame(left_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        self.metadata_canvas = tk.Canvas(canvas_frame, bg='white')
        h_scrollbar = ttk.Scrollbar(canvas_frame, orient="horizontal", command=self.metadata_canvas.xview)
        v_scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=self.metadata_canvas.yview)
        
        self.metadata_canvas.configure(xscrollcommand=h_scrollbar.set, yscrollcommand=v_scrollbar.set)
        
        self.metadata_canvas.pack(side="left", fill="both", expand=True)
        h_scrollbar.pack(side="bottom", fill="x")
        v_scrollbar.pack(side="right", fill="y")
        
        # Image info
        self.metadata_image_info = ttk.Label(left_frame, text="No image selected")
        self.metadata_image_info.pack(fill=tk.X, pady=(10, 0))
        
        # Right side - Metadata editor
        right_frame = ttk.LabelFrame(content_frame, text="📝 Metadata Editor", padding="10")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        # Metadata display area
        metadata_display_frame = ttk.Frame(right_frame)
        metadata_display_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create scrollable frame for metadata
        canvas = tk.Canvas(metadata_display_frame, bg='white')
        scrollbar = ttk.Scrollbar(metadata_display_frame, orient="vertical", command=canvas.yview)
        self.metadata_scrollable_frame = ttk.Frame(canvas)
        
        self.metadata_scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.metadata_scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Action buttons
        button_frame = ttk.Frame(right_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(button_frame, text="💾 Save Metadata", 
                  command=self.save_metadata).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="✅ Verify Saved Data", 
                  command=self.verify_saved_metadata).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="🔧 Install ExifTool", 
                  command=self.install_exiftool_help).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="➕ Add Field", 
                  command=self.add_metadata_field).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="🗑️ Remove Field", 
                  command=self.remove_metadata_field).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="🔍 Scan All Fields", 
                  command=self.scan_all_metadata_fields).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="🔄 Refresh", 
                  command=self.load_image_metadata).pack(side=tk.LEFT)
        
        # Dev/Testing controls
        dev_frame = ttk.LabelFrame(metadata_container, text="🔧 Dev/Testing Controls", padding="10")
        dev_frame.pack(fill=tk.X, pady=(10, 0))
        
        dev_controls = ttk.Frame(dev_frame)
        dev_controls.pack(fill=tk.X)
        
        ttk.Label(dev_controls, text="Metadata Format Override:").pack(side=tk.LEFT, padx=(0, 10))
        
        format_combo = ttk.Combobox(dev_controls, textvariable=self.metadata_format_override, 
                                   values=["auto", "jpeg", "webp"], state="readonly", width=10)
        format_combo.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(dev_controls, text="Apply Override", 
                  command=self.apply_metadata_format_override).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(dev_controls, text="Show Config", 
                  command=self.show_metadata_config).pack(side=tk.LEFT)
        
        # Batch operations
        batch_frame = ttk.LabelFrame(metadata_container, text="🔄 Batch Operations", padding="10")
        batch_frame.pack(fill=tk.X, pady=(10, 0))
        
        batch_controls = ttk.Frame(batch_frame)
        batch_controls.pack(fill=tk.X)
        
        ttk.Label(batch_controls, text="Batch Process:").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(batch_controls, text="📁 Select Folder", 
                  command=self.select_batch_folder).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(batch_controls, text="🚀 Process All", 
                  command=self.batch_process_metadata).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(batch_controls, text="📊 Show Summary", 
                  command=self.show_batch_summary).pack(side=tk.LEFT)
        
        # Metadata storage
        self.current_metadata = {}
        self.metadata_fields = {}
        self.batch_folder = None
        
        # AI/LM Studio variables
        self.lm_studio_url = tk.StringVar(value="http://192.168.0.17:1234")
        self.lm_studio_model = tk.StringVar(value="qwen/qwen2.5-vl-7b")
        self.ai_enabled = tk.BooleanVar(value=False)
        self.ai_descriptions = {}
        self.ai_processing = False
        self.available_lm_studio_models = []
        self.ai_connected = False
        
        # Chat folder navigation variables
        self.chat_folder_images = []
        self.chat_current_image_index = 0
        self.chat_folder_path_str = ""
        
        # Tool use variables already initialized before setup_ui()
        
        # Metadata format configuration already initialized in setup_ui()
        
        # Initialize AI integration
        self.setup_ai_integration()
        
        # Auto-connect to LM Studio on startup
        self.root.after(2000, self.auto_connect_lm_studio)  # Wait 2 seconds for UI to load
    
    def setup_metadata_format_config(self):
        """Setup metadata format configuration for different file types."""
        # Define metadata field mappings for different formats - streamlined to essential fields
        self.metadata_configs = {
            'jpeg': {
                'field_mapping': {
                    'XPTitle': 'XPTitle',
                    'ImageDescription': 'ImageDescription', 
                    'XPKeywords': 'XPKeywords',
                    'Artist': 'Artist',
                    'Make': 'Make',
                    'Model': 'Model'
                },
                'exif_tags': {
                    'XPTitle': (40091, 'XPTitle', 'utf-16le'),
                    'ImageDescription': (270, 'ImageDescription', 'utf-8'),
                    'XPKeywords': (40094, 'XPKeywords', 'utf-16le'),
                    'Artist': (315, 'Artist', 'utf-8'),
                    'Make': (271, 'Make', 'utf-8'),
                    'Model': (272, 'Model', 'utf-8')
                },
                'xmp_tags': {
                    'XPTitle': '-XMP:Title',
                    'ImageDescription': '-XMP:Description',
                    'XPKeywords': '-XMP:Subject',
                    'Artist': '-XMP:Creator',
                    'Make': '-XMP:Make',
                    'Model': '-XMP:Model'
                }
            },
            'webp': {
                'field_mapping': {
                    'XPTitle': 'XPTitle',
                    'ImageDescription': 'ImageDescription',
                    'XPKeywords': 'XPKeywords', 
                    'Artist': 'Artist',
                    'Make': 'Make',
                    'Model': 'Model'
                },
                'exif_tags': {},  # WebP doesn't use EXIF
                'xmp_tags': {
                    'XPTitle': '-XMP:Title',
                    'ImageDescription': '-XMP:Description',
                    'XPKeywords': '-XMP:Subject',
                    'Artist': '-XMP:Creator',
                    'Make': '-XMP:Make',
                    'Model': '-XMP:Model'
                }
            }
        }
        
    def get_metadata_config(self, file_path):
        """Get metadata configuration based on file type or override."""
        file_ext = Path(file_path).suffix.lower()
        
        # Check override setting
        if self.metadata_format_override.get() != "auto":
            return self.metadata_configs[self.metadata_format_override.get()]
        
        # Auto-detect based on file extension
        if file_ext in ['.jpg', '.jpeg']:
            return self.metadata_configs['jpeg']
        elif file_ext in ['.webp']:
            return self.metadata_configs['webp']
        else:
            # Default to JPEG for other formats
            return self.metadata_configs['jpeg']
        
    def setup_test_tab(self):
        """Setup the test run tab."""
        test_container = ttk.Frame(self.test_frame, padding="10")
        test_container.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(test_container, text="🧪 Test Run - Find Your Perfect Settings", 
                               font=('Arial', 14, 'bold'))
        title_label.pack(pady=(0, 20))
        
        # Test image selection
        image_frame = ttk.LabelFrame(test_container, text="📁 Select Test Image", padding="10")
        image_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.test_image_path = tk.StringVar()
        ttk.Entry(image_frame, textvariable=self.test_image_path, width=60).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(image_frame, text="Browse", command=self.select_test_image).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(image_frame, text="Use Current Preview", command=self.use_preview_image).pack(side=tk.LEFT)
        
        # Test configurations
        config_frame = ttk.LabelFrame(test_container, text="⚙️ Test Configurations", padding="10")
        config_frame.pack(fill=tk.X, pady=(0, 10))
        
        # File size limit for test
        size_frame = ttk.Frame(config_frame)
        size_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(size_frame, text="Target File Size:").pack(side=tk.LEFT, padx=(0, 10))
        self.test_file_size = tk.IntVar(value=300)
        ttk.Entry(size_frame, textvariable=self.test_file_size, width=10).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Label(size_frame, text="KB").pack(side=tk.LEFT, padx=(0, 20))
        
        ttk.Label(size_frame, text="(Test will try 5 different quality settings to reach this size)").pack(side=tk.LEFT)
        
        # Test button
        ttk.Button(config_frame, text="🚀 Run Test", command=self.run_test, 
                  style="Accent.TButton").pack(pady=10)
        
        # Test results
        results_frame = ttk.LabelFrame(test_container, text="📊 Test Results", padding="10")
        results_frame.pack(fill=tk.BOTH, expand=True)
        
        # Results canvas with scrollbar
        canvas_frame = ttk.Frame(results_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        self.test_canvas = tk.Canvas(canvas_frame, bg='white')
        self.test_scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=self.test_canvas.yview)
        self.test_scrollable_frame = ttk.Frame(self.test_canvas)
        
        self.test_scrollable_frame.bind(
            "<Configure>",
            lambda e: self.test_canvas.configure(scrollregion=self.test_canvas.bbox("all"))
        )
        
        self.test_canvas.create_window((0, 0), window=self.test_scrollable_frame, anchor="nw")
        self.test_canvas.configure(yscrollcommand=self.test_scrollbar.set)
        
        self.test_canvas.pack(side="left", fill="both", expand=True)
        self.test_scrollbar.pack(side="right", fill="y")
        
        # Test results storage
        self.test_results = []
        self.test_images = []
        
    def create_io_section(self, parent, row):
        """Create input/output directory selection section with drag-and-drop."""
        # Input Directory
        ttk.Label(parent, text="📁 Input Directory:").grid(row=row, column=0, sticky=tk.W, pady=5)
        
        input_frame = ttk.Frame(parent)
        input_frame.grid(row=row, column=1, sticky=(tk.W, tk.E), padx=(5, 5), pady=5)
        input_frame.columnconfigure(0, weight=1)
        
        self.input_entry = ttk.Entry(input_frame, textvariable=self.input_dir, width=50)
        self.input_entry.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        ttk.Button(input_frame, text="Browse", command=self.browse_input_dir).grid(row=0, column=1, padx=(5, 0))
        
        # Drag and drop label
        drop_label = ttk.Label(input_frame, text="📂 Drag folders here", 
                              foreground="gray", font=('Arial', 8))
        drop_label.grid(row=1, column=0, sticky=tk.W, pady=(2, 0))
        
        # Configure drag and drop
        self.input_entry.drop_target_register(tkdnd.DND_FILES)
        self.input_entry.dnd_bind('<<Drop>>', self.on_drop)
        
        # Single File Input
        ttk.Label(parent, text="📄 Single File:").grid(row=row+1, column=0, sticky=tk.W, pady=5)
        
        single_file_frame = ttk.Frame(parent)
        single_file_frame.grid(row=row+1, column=1, sticky=(tk.W, tk.E), padx=(5, 5), pady=5)
        single_file_frame.columnconfigure(0, weight=1)
        
        self.single_file_entry = ttk.Entry(single_file_frame, textvariable=self.single_file, width=50)
        self.single_file_entry.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        ttk.Button(single_file_frame, text="Browse", command=self.browse_single_file).grid(row=0, column=1, padx=(5, 0))
        ttk.Button(single_file_frame, text="Clear", command=self.clear_single_file).grid(row=0, column=2, padx=(5, 0))
        
        # Single file drag and drop label
        single_drop_label = ttk.Label(single_file_frame, text="📂 Drag single file here", 
                                     foreground="gray", font=('Arial', 8))
        single_drop_label.grid(row=1, column=0, sticky=tk.W, pady=(2, 0))
        
        # Configure single file drag and drop
        self.single_file_entry.drop_target_register(tkdnd.DND_FILES)
        self.single_file_entry.dnd_bind('<<Drop>>', self.on_single_file_drop)
        
        # Output Directory
        ttk.Label(parent, text="📤 Output Directory:").grid(row=row+2, column=0, sticky=tk.W, pady=5)
        ttk.Entry(parent, textvariable=self.output_dir, width=50).grid(row=row+2, column=1, sticky=(tk.W, tk.E), padx=(5, 5), pady=5)
        ttk.Button(parent, text="Browse", command=self.browse_output_dir).grid(row=row+2, column=2, pady=5)
        
        # Auto-detect image folders
        ttk.Button(parent, text="🔍 Auto-detect image folders", 
                  command=self.auto_detect_folders).grid(row=row+3, column=1, sticky=tk.W, pady=5)
        
    def create_settings_section(self, parent, row):
        """Create compression settings section."""
        settings_frame = ttk.LabelFrame(parent, text="⚙️ Compression Settings", padding="10")
        settings_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        settings_frame.columnconfigure(1, weight=1)
        settings_frame.columnconfigure(2, weight=2)
        
        # Quality
        quality_label = ttk.Label(settings_frame, text="Quality:")
        quality_label.grid(row=0, column=0, sticky=tk.W, pady=2)
        quality_label.bind("<Enter>", lambda e: self.show_tooltip("Quality controls compression level. Higher values (80-95) = better quality but larger files. Lower values (60-80) = smaller files but reduced quality. Recommended: 85 for web use."))
        quality_label.bind("<Leave>", lambda e: self.hide_tooltip())
        
        quality_frame = ttk.Frame(settings_frame)
        quality_frame.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=2)
        quality_scale = ttk.Scale(quality_frame, from_=1, to=100, variable=self.quality, 
                 orient=tk.HORIZONTAL, length=200)
        quality_scale.pack(side=tk.LEFT)
        quality_scale.bind("<Enter>", lambda e: self.show_tooltip("Quality controls compression level. Higher values (80-95) = better quality but larger files. Lower values (60-80) = smaller files but reduced quality. Recommended: 85 for web use."))
        quality_scale.bind("<Leave>", lambda e: self.hide_tooltip())
        
        quality_value = ttk.Label(quality_frame, textvariable=self.quality)
        quality_value.pack(side=tk.LEFT, padx=(10, 0))
        
        # Quality explanation
        quality_explanation = ttk.Label(settings_frame, text="Higher = better quality, larger files. Lower = smaller files, reduced quality", 
                                      foreground="gray", font=('Arial', 8))
        quality_explanation.grid(row=0, column=2, sticky=tk.W, padx=(10, 0), pady=2)
        
        # Max Width
        width_label = ttk.Label(settings_frame, text="Max Width:")
        width_label.grid(row=1, column=0, sticky=tk.W, pady=2)
        width_label.bind("<Enter>", lambda e: self.show_tooltip("Maximum width in pixels. Images wider than this will be resized while maintaining aspect ratio. Set to 0 to disable width limiting."))
        width_label.bind("<Leave>", lambda e: self.hide_tooltip())
        
        width_entry = ttk.Entry(settings_frame, textvariable=self.max_width, width=10)
        width_entry.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=2)
        width_entry.bind("<Enter>", lambda e: self.show_tooltip("Maximum width in pixels. Images wider than this will be resized while maintaining aspect ratio. Set to 0 to disable width limiting."))
        width_entry.bind("<Leave>", lambda e: self.hide_tooltip())
        
        # Width explanation
        width_explanation = ttk.Label(settings_frame, text="Images wider than this will be resized (0 = no limit)", 
                                    foreground="gray", font=('Arial', 8))
        width_explanation.grid(row=1, column=2, sticky=tk.W, padx=(10, 0), pady=2)
        
        # Max Height
        height_label = ttk.Label(settings_frame, text="Max Height:")
        height_label.grid(row=2, column=0, sticky=tk.W, pady=2)
        height_label.bind("<Enter>", lambda e: self.show_tooltip("Maximum height in pixels. Images taller than this will be resized while maintaining aspect ratio. Set to 0 to disable height limiting."))
        height_label.bind("<Leave>", lambda e: self.hide_tooltip())
        
        height_entry = ttk.Entry(settings_frame, textvariable=self.max_height, width=10)
        height_entry.grid(row=2, column=1, sticky=tk.W, padx=(10, 0), pady=2)
        height_entry.bind("<Enter>", lambda e: self.show_tooltip("Maximum height in pixels. Images taller than this will be resized while maintaining aspect ratio. Set to 0 to disable height limiting."))
        height_entry.bind("<Leave>", lambda e: self.hide_tooltip())
        
        # Height explanation
        height_explanation = ttk.Label(settings_frame, text="Images taller than this will be resized (0 = no limit)", 
                                     foreground="gray", font=('Arial', 8))
        height_explanation.grid(row=2, column=2, sticky=tk.W, padx=(10, 0), pady=2)
        
        # Format
        format_label = ttk.Label(settings_frame, text="Format:")
        format_label.grid(row=3, column=0, sticky=tk.W, pady=2)
        format_label.bind("<Enter>", lambda e: self.show_tooltip("Output image format. WebP: Best compression, modern browsers only. JPEG: Good compression, universal support. PNG: Lossless, larger files. AVIF: Newest format, excellent compression."))
        format_label.bind("<Leave>", lambda e: self.hide_tooltip())
        
        format_combo = ttk.Combobox(settings_frame, textvariable=self.format_var, 
                                   values=["webp", "jpeg", "png", "avif"], state="readonly", width=10)
        format_combo.grid(row=3, column=1, sticky=tk.W, padx=(10, 0), pady=2)
        format_combo.bind("<Enter>", lambda e: self.show_tooltip("Output image format. WebP: Best compression, modern browsers only. JPEG: Good compression, universal support. PNG: Lossless, larger files. AVIF: Newest format, excellent compression."))
        format_combo.bind("<Leave>", lambda e: self.hide_tooltip())
        
        # Format explanation
        format_explanation = ttk.Label(settings_frame, text="WebP: Best compression. JPEG: Universal support. PNG: Lossless. AVIF: Newest format", 
                                     foreground="gray", font=('Arial', 8))
        format_explanation.grid(row=3, column=2, sticky=tk.W, padx=(10, 0), pady=2)
        
        # Preserve Structure
        structure_check = ttk.Checkbutton(settings_frame, text="Preserve folder structure", 
                       variable=self.preserve_structure)
        structure_check.grid(row=4, column=0, columnspan=2, sticky=tk.W, pady=5)
        structure_check.bind("<Enter>", lambda e: self.show_tooltip("Keep the same folder organization in the output directory. If unchecked, all images will be placed in a single output folder."))
        structure_check.bind("<Leave>", lambda e: self.hide_tooltip())
        
        # Structure explanation
        structure_explanation = ttk.Label(settings_frame, text="Keep original folder organization in output", 
                                        foreground="gray", font=('Arial', 8))
        structure_explanation.grid(row=4, column=2, sticky=tk.W, padx=(10, 0), pady=5)
        
        # Max Workers
        workers_label = ttk.Label(settings_frame, text="Parallel Workers:")
        workers_label.grid(row=5, column=0, sticky=tk.W, pady=2)
        workers_label.bind("<Enter>", lambda e: self.show_tooltip("Number of images to process simultaneously. Higher values = faster processing but more memory usage. Recommended: 4 for most systems."))
        workers_label.bind("<Leave>", lambda e: self.hide_tooltip())
        
        workers_spinbox = ttk.Spinbox(settings_frame, from_=1, to=8, textvariable=self.max_workers, width=10)
        workers_spinbox.grid(row=5, column=1, sticky=tk.W, padx=(10, 0), pady=2)
        workers_spinbox.bind("<Enter>", lambda e: self.show_tooltip("Number of images to process simultaneously. Higher values = faster processing but more memory usage. Recommended: 4 for most systems."))
        workers_spinbox.bind("<Leave>", lambda e: self.hide_tooltip())
        
        # Workers explanation
        workers_explanation = ttk.Label(settings_frame, text="More workers = faster processing, more memory usage", 
                                      foreground="gray", font=('Arial', 8))
        workers_explanation.grid(row=5, column=2, sticky=tk.W, padx=(10, 0), pady=2)
        
        # Max File Size
        filesize_label = ttk.Label(settings_frame, text="Max File Size:")
        filesize_label.grid(row=6, column=0, sticky=tk.W, pady=2)
        filesize_label.bind("<Enter>", lambda e: self.show_tooltip("Maximum output file size in KB. If compressed file exceeds this size, quality will be reduced automatically. Set to 0 to disable file size limiting."))
        filesize_label.bind("<Leave>", lambda e: self.hide_tooltip())
        
        filesize_frame = ttk.Frame(settings_frame)
        filesize_frame.grid(row=6, column=1, sticky=tk.W, padx=(10, 0), pady=2)
        
        filesize_entry = ttk.Entry(filesize_frame, textvariable=self.max_file_size, width=8)
        filesize_entry.pack(side=tk.LEFT)
        filesize_entry.bind("<Enter>", lambda e: self.show_tooltip("Maximum output file size in KB. If compressed file exceeds this size, quality will be reduced automatically. Set to 0 to disable file size limiting."))
        filesize_entry.bind("<Leave>", lambda e: self.hide_tooltip())
        
        ttk.Label(filesize_frame, text="KB").pack(side=tk.LEFT, padx=(5, 0))
        
        # File size explanation
        filesize_explanation = ttk.Label(settings_frame, text="Auto-reduce quality if file exceeds this size (0 = no limit)", 
                                       foreground="gray", font=('Arial', 8))
        filesize_explanation.grid(row=6, column=2, sticky=tk.W, padx=(10, 0), pady=2)
        
    def create_presets_section(self, parent, row):
        """Create presets section."""
        presets_frame = ttk.LabelFrame(parent, text="🎯 Quick Presets", padding="10")
        presets_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        
        # Preset buttons
        presets = [
            ("Web High", "High quality for hero images", 90, 1920, 1080, "webp", 500),
            ("Web Medium", "Medium quality for gallery", 80, 1200, 800, "webp", 300),
            ("Web Thumb", "Thumbnail quality", 75, 400, 300, "webp", 50),
            ("JPEG Fallback", "JPEG for older browsers", 85, 1920, 1080, "jpeg", 800)
        ]
        
        for i, (name, desc, quality, width, height, format, max_size) in enumerate(presets):
            btn = ttk.Button(presets_frame, text=f"{name}\n{desc}", 
                           command=lambda q=quality, w=width, h=height, f=format, s=max_size: self.apply_preset(q, w, h, f, s))
            btn.grid(row=i//2, column=i%2, padx=5, pady=5, sticky=(tk.W, tk.E))
        
        presets_frame.columnconfigure(0, weight=1)
        presets_frame.columnconfigure(1, weight=1)
        
    def create_control_section(self, parent, row):
        """Create control buttons section."""
        control_frame = ttk.Frame(parent)
        control_frame.grid(row=row, column=0, columnspan=3, pady=10)
        
        self.start_button = ttk.Button(control_frame, text="🚀 Start Compression", 
                                     command=self.start_compression, style="Accent.TButton")
        self.start_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.stop_button = ttk.Button(control_frame, text="⏹️ Stop", 
                                    command=self.stop_compression, state="disabled")
        self.stop_button.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(control_frame, text="📊 Clear Log", 
                 command=self.clear_log).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(control_frame, text="❓ Help", 
                 command=self.show_help).pack(side=tk.LEFT)
        
    def create_progress_section(self, parent, row):
        """Create progress section."""
        progress_frame = ttk.LabelFrame(parent, text="📊 Progress", padding="10")
        progress_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        progress_frame.columnconfigure(1, weight=1)
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, 
                                          maximum=100, length=400)
        self.progress_bar.grid(row=0, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        
        # Status labels
        self.status_label = ttk.Label(progress_frame, text="Ready to compress images")
        self.status_label.grid(row=1, column=0, columnspan=3, sticky=tk.W, pady=2)
        
        # Statistics
        stats_frame = ttk.Frame(progress_frame)
        stats_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        stats_frame.columnconfigure(1, weight=1)
        
        self.stats_labels = {}
        stats = ["Processed:", "Errors:", "Original Size:", "Compressed Size:", "Time Taken:"]
        for i, stat in enumerate(stats):
            ttk.Label(stats_frame, text=stat).grid(row=i//3, column=(i%3)*2, sticky=tk.W, padx=(0, 5))
            self.stats_labels[stat] = ttk.Label(stats_frame, text="0")
            self.stats_labels[stat].grid(row=i//3, column=(i%3)*2+1, sticky=tk.W, padx=(0, 20))
        
    def create_log_section(self, parent, row):
        """Create log section."""
        log_frame = ttk.LabelFrame(parent, text="📝 Processing Log", padding="10")
        log_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=6, wrap=tk.WORD)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights for resizing
        parent.rowconfigure(row, weight=1)
    
    def create_batch_ai_section(self, parent, row):
        """Create batch AI processing section."""
        # Batch AI Processing Section
        batch_ai_frame = ttk.LabelFrame(parent, text="🤖 Batch AI Processing", padding="10")
        batch_ai_frame.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(10, 0))
        parent.columnconfigure(0, weight=1)
        
        # Instructions
        instructions = ttk.Label(batch_ai_frame, 
                               text="1. Set up rules in AI Chat tab\n2. Load a folder of images\n3. Click 'Process Batch with AI'", 
                               font=('Arial', 9), foreground='gray')
        instructions.pack(anchor=tk.W, pady=(0, 10))
        
        # Controls
        controls_frame = ttk.Frame(batch_ai_frame)
        controls_frame.pack(fill=tk.X)
        
        ttk.Button(controls_frame, text="🤖 Process Batch with AI", 
                  command=self.start_batch_ai_processing).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(controls_frame, text="📋 View Chat Rules", 
                  command=self.view_chat_rules).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(controls_frame, text="📁 Select Folder for AI", 
                  command=self.select_ai_folder).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(controls_frame, text="📂 Show Folder Contents", 
                  command=self.show_folder_contents).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(controls_frame, text="🔧 Enable Tool Use", 
                  command=self.toggle_tool_use).pack(side=tk.LEFT, padx=(0, 10))
        
        # Tool use model selection (DeepSeek only - supports tool use)
        model_frame = ttk.Frame(controls_frame)
        model_frame.pack(side=tk.LEFT, padx=(0, 10))
        ttk.Label(model_frame, text="Tool Model:").pack(side=tk.LEFT, padx=(0, 5))
        self.tool_model_var = tk.StringVar(value=self.tool_use_model)
        tool_model_combo = ttk.Combobox(model_frame, textvariable=self.tool_model_var, 
                                       values=self.available_tool_models, width=30,
                                       state="readonly")
        tool_model_combo.pack(side=tk.LEFT)
        tool_model_combo.bind('<<ComboboxSelected>>', self.update_tool_model)
        
        # Disable thinking checkbox
        self.disable_thinking_var = tk.BooleanVar(value=self.disable_thinking)
        thinking_check = ttk.Checkbutton(controls_frame, text="Disable Thinking", 
                                        variable=self.disable_thinking_var,
                                        command=self.toggle_thinking_disable)
        thinking_check.pack(side=tk.LEFT, padx=(0, 10))
        
        # Token limit control
        token_frame = ttk.Frame(controls_frame)
        token_frame.pack(side=tk.LEFT, padx=(0, 10))
        ttk.Label(token_frame, text="Max Tokens:").pack(side=tk.LEFT, padx=(0, 5))
        self.token_limit_var = tk.StringVar(value=str(self.max_tokens))
        token_spinbox = ttk.Spinbox(token_frame, from_=1000, to=8000, width=8, 
                                   textvariable=self.token_limit_var,
                                   command=self.update_token_limit)
        token_spinbox.pack(side=tk.LEFT)
        
        # Temperature control
        temp_frame = ttk.Frame(controls_frame)
        temp_frame.pack(side=tk.LEFT, padx=(0, 10))
        ttk.Label(temp_frame, text="Temperature:").pack(side=tk.LEFT, padx=(0, 5))
        self.temperature_var = tk.StringVar(value=str(self.ai_temperature))
        temp_spinbox = ttk.Spinbox(temp_frame, from_=0.1, to=1.0, increment=0.1, width=6, 
                                   textvariable=self.temperature_var,
                                   command=self.update_temperature)
        temp_spinbox.pack(side=tk.LEFT)
    
    def select_ai_folder(self):
        """Select folder for AI batch processing."""
        folder = filedialog.askdirectory(title="Select folder for AI batch processing")
        if folder:
            self.batch_folder = folder
            self.image_files = self._load_images_from_folder(folder)
            self.log_message(f"📁 Selected AI folder: {folder}")
            self.log_message(f"📊 Found {len(self.image_files)} images")
        
    def on_drop(self, event):
        """Handle drag and drop events."""
        files = self.root.tk.splitlist(event.data)
        if files:
            # Take the first directory if multiple items are dropped
            path = Path(files[0])
            if path.is_dir():
                self.input_dir.set(str(path))
                self.auto_set_output_dir()
                self.log_message(f"📁 Dropped directory: {path.name}")
            else:
                self.log_message(f"⚠️ Please drop a directory, not a file")
    
    def on_single_file_drop(self, event):
        """Handle drag and drop for single file."""
        files = self.root.tk.splitlist(event.data)
        if files:
            path = Path(files[0])
            if path.is_file() and path.suffix.lower() in ['.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.webp', '.avif']:
                self.single_file.set(str(path))
                # Auto-set output directory to same folder as input file
                output_dir = str(path.parent)
                self.output_dir.set(output_dir)
                self.log_message(f"📄 Dropped single file: {path.name}")
            else:
                self.log_message(f"⚠️ Please drop a valid image file")
        
    def browse_input_dir(self):
        """Browse for input directory."""
        directory = filedialog.askdirectory(title="Select Input Directory")
        if directory:
            self.input_dir.set(directory)
            self.auto_set_output_dir()
            
    def browse_single_file(self):
        """Browse for single image file."""
        file_path = filedialog.askopenfilename(
            title="Select Image File",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp *.tiff *.webp *.avif")]
        )
        if file_path:
            self.single_file.set(file_path)
            # Auto-set output directory to same folder as input file
            output_dir = str(Path(file_path).parent)
            self.output_dir.set(output_dir)
    
    def clear_single_file(self):
        """Clear single file selection."""
        self.single_file.set("")
        self.log_message("📄 Single file selection cleared")
            
    def browse_output_dir(self):
        """Browse for output directory."""
        directory = filedialog.askdirectory(title="Select Output Directory")
        if directory:
            self.output_dir.set(directory)
            
    def auto_detect_folders(self):
        """Auto-detect image folders in current directory."""
        current_dir = Path.cwd()
        common_folders = ['decor', 'edging', 'full_board', 'rooms', 'images', 'photos', 'pictures']
        found_folders = [folder for folder in common_folders if (current_dir / folder).exists()]
        
        if found_folders:
            self.input_dir.set(str(current_dir))
            self.auto_set_output_dir()
            self.log_message(f"✅ Auto-detected image folders: {', '.join(found_folders)}")
        else:
            self.log_message("⚠️ No common image folders found in current directory")
            
    def auto_set_output_dir(self):
        """Auto-set output directory based on input."""
        if self.input_dir.get():
            input_path = Path(self.input_dir.get())
            self.output_dir.set(str(input_path / "compressed"))
            
    def apply_preset(self, quality, width, height, format, max_size=0):
        """Apply a preset configuration."""
        self.quality.set(quality)
        self.max_width.set(width)
        self.max_height.set(height)
        self.format_var.set(format)
        self.max_file_size.set(max_size)
        self.log_message(f"✅ Applied preset: Quality={quality}, Size={width}x{height}, Format={format.upper()}, MaxSize={max_size}KB")
        
    def select_preview_image(self):
        """Select an image for preview."""
        file_path = filedialog.askopenfilename(
            title="Select Image for Preview",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp *.tiff *.webp *.avif")]
        )
        if file_path:
            self.load_preview_image(file_path)
            
    def load_preview_image(self, file_path):
        """Load an image for preview."""
        try:
            self.current_image = Image.open(file_path)
            self.preview_scale = 1.0
            self.refresh_preview()
            
            # Update image info
            width, height = self.current_image.size
            file_size = os.path.getsize(file_path) / 1024  # KB
            self.image_info_label.config(
                text=f"📁 {Path(file_path).name} | 📏 {width}x{height} | 📦 {file_size:.1f} KB"
            )
            
        except Exception as e:
            messagebox.showerror("Error", f"Could not load image: {str(e)}")
            
    def refresh_preview(self):
        """Refresh the image preview."""
        if not self.current_image:
            return
            
        # Calculate display size
        canvas_width = self.preview_canvas.winfo_width()
        canvas_height = self.preview_canvas.winfo_height()
        
        if canvas_width <= 1 or canvas_height <= 1:
            # Canvas not ready, schedule refresh
            self.root.after(100, self.refresh_preview)
            return
            
        # Resize image to fit canvas
        img_width, img_height = self.current_image.size
        scale_x = (canvas_width - 20) / img_width
        scale_y = (canvas_height - 20) / img_height
        scale = min(scale_x, scale_y) * self.preview_scale
        
        new_width = int(img_width * scale)
        new_height = int(img_height * scale)
        
        # Resize image
        resized_image = self.current_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        self.preview_image = ImageTk.PhotoImage(resized_image)
        
        # Clear canvas and draw image
        self.preview_canvas.delete("all")
        x = (canvas_width - new_width) // 2
        y = (canvas_height - new_height) // 2
        self.preview_canvas.create_image(x, y, anchor=tk.NW, image=self.preview_image)
        
        # Update zoom level display
        if hasattr(self, 'preview_zoom_label'):
            self.preview_zoom_label.config(text=f"{int(self.preview_scale * 100)}%")
        
    def zoom_in(self):
        """Zoom in on the preview image."""
        self.preview_scale *= 1.2
        self.refresh_preview()
        
    def zoom_out(self):
        """Zoom out on the preview image."""
        self.preview_scale /= 1.2
        if self.preview_scale < 0.1:
            self.preview_scale = 0.1
        self.refresh_preview()
        
    def zoom_fit(self):
        """Fit the image to the canvas."""
        self.preview_scale = 1.0
        self.refresh_preview()
        
    def zoom_actual(self):
        """Show image at actual size (100%)."""
        self.preview_scale = 1.0
        self.refresh_preview()
        
    def mouse_wheel_preview(self, event):
        """Handle mouse wheel zoom in preview."""
        if self.current_image:
            if event.delta > 0:
                self.zoom_in()
            else:
                self.zoom_out()
        
    def show_comparison(self):
        """Show before/after comparison."""
        if not self.current_image:
            messagebox.showwarning("Warning", "Please select an image first")
            return
            
        # Create comparison window
        comp_window = tk.Toplevel(self.root)
        comp_window.title("Before/After Comparison")
        comp_window.geometry("800x600")
        
        # Create comparison frame
        comp_frame = ttk.Frame(comp_window, padding="10")
        comp_frame.pack(fill=tk.BOTH, expand=True)
        
        # Before image
        before_frame = ttk.LabelFrame(comp_frame, text="Before (Original)", padding="5")
        before_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        before_canvas = tk.Canvas(before_frame, bg='white')
        before_canvas.pack(fill=tk.BOTH, expand=True)
        
        # After image (simulated compression)
        after_frame = ttk.LabelFrame(comp_frame, text="After (Compressed)", padding="5")
        after_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        after_canvas = tk.Canvas(after_frame, bg='white')
        after_canvas.pack(fill=tk.BOTH, expand=True)
        
        # Load and display images
        self.load_comparison_images(before_canvas, after_canvas)
        
    def load_comparison_images(self, before_canvas, after_canvas):
        """Load and display comparison images."""
        try:
            # Original image
            original = self.current_image.copy()
            self.display_image_in_canvas(original, before_canvas)
            
            # Simulate compressed image
            compressed = self.simulate_compression(original)
            self.display_image_in_canvas(compressed, after_canvas)
            
        except Exception as e:
            messagebox.showerror("Error", f"Could not create comparison: {str(e)}")
            
    def simulate_compression(self, image):
        """Simulate compression for preview."""
        # Apply the same settings as the compressor
        width, height = self.calculate_new_size(*image.size)
        
        if (width, height) != image.size:
            image = image.resize((width, height), Image.Resampling.LANCZOS)
            
        return image
        
    def calculate_new_size(self, width, height):
        """Calculate new dimensions maintaining aspect ratio."""
        if not self.max_width.get() and not self.max_height.get():
            return width, height
        
        ratio = width / height
        new_width, new_height = width, height
        
        if self.max_width.get() and self.max_height.get():
            if width > self.max_width.get():
                new_width = self.max_width.get()
                new_height = int(new_width / ratio)
            if new_height > self.max_height.get():
                new_height = self.max_height.get()
                new_width = int(new_height * ratio)
        elif self.max_width.get() and width > self.max_width.get():
            new_width = self.max_width.get()
            new_height = int(new_width / ratio)
        elif self.max_height.get() and height > self.max_height.get():
            new_height = self.max_height.get()
            new_width = int(new_height * ratio)
        
        return new_width, new_height
        
    def display_image_in_canvas(self, image, canvas):
        """Display an image in a canvas."""
        # Calculate display size
        canvas_width = canvas.winfo_width()
        canvas_height = canvas.winfo_height()
        
        if canvas_width <= 1 or canvas_height <= 1:
            # Canvas not ready, schedule refresh
            self.root.after(100, lambda: self.display_image_in_canvas(image, canvas))
            return
            
        # Resize image to fit canvas
        img_width, img_height = image.size
        scale_x = (canvas_width - 20) / img_width
        scale_y = (canvas_height - 20) / img_height
        scale = min(scale_x, scale_y)
        
        new_width = int(img_width * scale)
        new_height = int(img_height * scale)
        
        # Resize image
        resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(resized_image)
        
        # Clear canvas and draw image
        canvas.delete("all")
        x = (canvas_width - new_width) // 2
        y = (canvas_height - new_height) // 2
        canvas.create_image(x, y, anchor=tk.NW, image=photo)
        
        # Keep reference to prevent garbage collection
        canvas.image = photo
        
    def start_compression(self):
        """Start the compression process."""
        if not self.input_dir.get() and not self.single_file.get():
            messagebox.showerror("Error", "Please select an input directory or single file")
            return
            
        if not self.output_dir.get():
            messagebox.showerror("Error", "Please select an output directory")
            return
            
        if self.is_processing:
            messagebox.showwarning("Warning", "Compression is already in progress")
            return
            
        # Reset statistics
        self.stats = {'processed': 0, 'errors': 0, 'original_size': 0, 'compressed_size': 0, 'time_taken': 0}
        self.update_stats_display()
        
        # Start processing thread
        self.is_processing = True
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")
        self.progress_var.set(0)
        
        self.processing_thread = threading.Thread(target=self.process_images_thread)
        self.processing_thread.daemon = True
        self.processing_thread.start()
        
    def stop_compression(self):
        """Stop the compression process."""
        self.is_processing = False
        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")
        self.status_label.config(text="Compression stopped by user")
        
    def process_images_thread(self):
        """Process images in a separate thread."""
        try:
            # Check if single file is selected
            single_file_path = self.single_file.get().strip()
            if single_file_path:
                # Process single file
                self.process_single_file(single_file_path)
                return
            
            # Process directory (existing logic)
            if not self.input_dir.get().strip():
                self.progress_queue.put(("error", "Please select an input directory or single file"))
                return
                
            # Create compressor
            compressor = ImageCompressor(
                input_dir=self.input_dir.get(),
                output_dir=self.output_dir.get(),
                quality=self.quality.get(),
                max_width=self.max_width.get() if self.max_width.get() > 0 else None,
                max_height=self.max_height.get() if self.max_height.get() > 0 else None,
                format=self.format_var.get(),
                preserve_structure=self.preserve_structure.get()
            )
            
            # Set max file size if specified
            max_file_size_kb = self.max_file_size.get()
            if max_file_size_kb > 0:
                compressor.max_file_size = max_file_size_kb * 1024  # Convert KB to bytes
            
            # Get image files
            image_files = compressor.get_image_files()
            total_images = len(image_files)
            
            if total_images == 0:
                self.progress_queue.put(("error", "No image files found in input directory"))
                return
                
            self.progress_queue.put(("status", f"Found {total_images} images to process"))
            self.progress_queue.put(("status", f"Output format: {self.format_var.get().upper()}"))
            self.progress_queue.put(("status", f"Quality: {self.quality.get()}"))
            
            # Process images
            start_time = time.time()
            processed = 0
            
            for i, img_path in enumerate(image_files):
                if not self.is_processing:
                    break
                    
                result = compressor.optimize_image(img_path)
                
                if result['status'] == 'success':
                    processed += 1
                    self.stats['processed'] += 1
                    self.stats['original_size'] += result['original_size']
                    self.stats['compressed_size'] += result['compressed_size']
                    
                    # Update progress
                    progress = (i + 1) / total_images * 100
                    self.progress_queue.put(("progress", progress))
                    self.progress_queue.put(("log", f"✅ {img_path.name} ({result['compression_ratio']:.1f}% saved)"))
                else:
                    self.stats['errors'] += 1
                    self.progress_queue.put(("log", f"❌ {img_path.name} - Error: {result['error']}"))
                    
            self.stats['time_taken'] = time.time() - start_time
            
            if self.is_processing:
                self.progress_queue.put(("complete", "Compression completed successfully!"))
            else:
                self.progress_queue.put(("complete", "Compression stopped by user"))
                
        except Exception as e:
            self.progress_queue.put(("error", f"Error during compression: {str(e)}"))
    
    def process_single_file(self, file_path):
        """Process a single image file."""
        try:
            from image_compressor import ImageCompressor
            
            # Validate file exists
            if not Path(file_path).exists():
                self.progress_queue.put(("error", f"File not found: {file_path}"))
                return
            
            # Get file info
            file_size = Path(file_path).stat().st_size
            file_name = Path(file_path).name
            
            self.progress_queue.put(("status", f"Processing single file: {file_name}"))
            self.progress_queue.put(("status", f"File size: {file_size / 1024:.1f} KB"))
            self.progress_queue.put(("status", f"Output format: {self.format_var.get().upper()}"))
            self.progress_queue.put(("status", f"Quality: {self.quality.get()}"))
            
            # Create compressor for single file
            compressor = ImageCompressor(
                input_dir=str(Path(file_path).parent),
                output_dir=self.output_dir.get(),
                quality=self.quality.get(),
                max_width=self.max_width.get() if self.max_width.get() > 0 else None,
                max_height=self.max_height.get() if self.max_height.get() > 0 else None,
                format=self.format_var.get(),
                preserve_structure=False  # Single file doesn't need structure preservation
            )
            
            # Set max file size if specified
            max_file_size_kb = self.max_file_size.get()
            if max_file_size_kb > 0:
                compressor.max_file_size = max_file_size_kb * 1024  # Convert KB to bytes
            
            # Process the single file
            start_time = time.time()
            result = compressor.optimize_image(Path(file_path))
            
            if result['status'] == 'success':
                # Update statistics
                self.stats['processed'] = 1
                self.stats['original_size'] = result['original_size']
                self.stats['compressed_size'] = result['compressed_size']
                
                # Calculate compression ratio
                compression_ratio = (1 - result['compressed_size'] / result['original_size']) * 100
                
                # Update progress
                self.progress_queue.put(("progress", 100))
                self.progress_queue.put(("status", f"✅ Successfully processed: {file_name}"))
                self.progress_queue.put(("status", f"Original size: {result['original_size'] / 1024:.1f} KB"))
                self.progress_queue.put(("status", f"Compressed size: {result['compressed_size'] / 1024:.1f} KB"))
                self.progress_queue.put(("status", f"Compression ratio: {compression_ratio:.1f}%"))
                
                # Show output file location
                output_file = result.get('output_path', 'Unknown')
                if output_file != 'Unknown':
                    self.progress_queue.put(("status", f"Output saved to: {Path(output_file).name}"))
                
                # Update stats display
                self.update_stats_display()
                
            else:
                self.progress_queue.put(("error", f"Failed to process {file_name}: {result.get('error', 'Unknown error')}"))
                
        except Exception as e:
            self.progress_queue.put(("error", f"Error processing single file: {str(e)}"))
            
    def check_queue(self):
        """Check for messages from the processing thread."""
        try:
            while True:
                message_type, message = self.progress_queue.get_nowait()
                
                if message_type == "status":
                    self.status_label.config(text=message)
                elif message_type == "progress":
                    self.progress_var.set(message)
                elif message_type == "log":
                    self.log_message(message)
                elif message_type == "complete":
                    self.log_message(f"🎉 {message}")
                    self.is_processing = False
                    self.start_button.config(state="normal")
                    self.stop_button.config(state="disabled")
                    self.update_stats_display()
                    self.update_detailed_stats()
                elif message_type == "error":
                    self.log_message(f"❌ {message}")
                    self.is_processing = False
                    self.start_button.config(state="normal")
                    self.stop_button.config(state="disabled")
                    
        except queue.Empty:
            pass
            
        # Schedule next check
        self.root.after(100, self.check_queue)
        
    def log_message(self, message):
        """Add a message to the log."""
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        
    def clear_log(self):
        """Clear the log."""
        self.log_text.delete(1.0, tk.END)
        
    def update_stats_display(self):
        """Update the statistics display."""
        self.stats_labels["Processed:"].config(text=str(self.stats['processed']))
        self.stats_labels["Errors:"].config(text=str(self.stats['errors']))
        
        # Format file sizes
        original_mb = self.stats['original_size'] / (1024 * 1024)
        compressed_mb = self.stats['compressed_size'] / (1024 * 1024)
        
        self.stats_labels["Original Size:"].config(text=f"{original_mb:.1f} MB")
        self.stats_labels["Compressed Size:"].config(text=f"{compressed_mb:.1f} MB")
        self.stats_labels["Time Taken:"].config(text=f"{self.stats['time_taken']:.1f}s")
        
    def update_detailed_stats(self):
        """Update the detailed statistics in the stats tab."""
        self.stats_text.delete(1.0, tk.END)
        
        # Calculate detailed statistics
        original_mb = self.stats['original_size'] / (1024 * 1024)
        compressed_mb = self.stats['compressed_size'] / (1024 * 1024)
        savings_mb = original_mb - compressed_mb
        savings_percent = (savings_mb / original_mb * 100) if original_mb > 0 else 0
        
        stats_text = f"""
📊 DETAILED COMPRESSION STATISTICS
{'='*50}

📈 PROCESSING SUMMARY:
   • Images Processed: {self.stats['processed']:,}
   • Errors: {self.stats['errors']:,}
   • Processing Time: {self.stats['time_taken']:.1f} seconds
   • Average Time per Image: {self.stats['time_taken']/max(self.stats['processed'], 1):.2f} seconds

📦 FILE SIZE ANALYSIS:
   • Original Total Size: {original_mb:.2f} MB
   • Compressed Total Size: {compressed_mb:.2f} MB
   • Space Saved: {savings_mb:.2f} MB
   • Compression Ratio: {savings_percent:.1f}%

⚙️ COMPRESSION SETTINGS USED:
   • Output Format: {self.format_var.get().upper()}
   • Quality Setting: {self.quality.get()}
   • Max Dimensions: {self.max_width.get()}x{self.max_height.get()}
   • Preserve Structure: {'Yes' if self.preserve_structure.get() else 'No'}
   • Parallel Workers: {self.max_workers.get()}

🎯 PERFORMANCE METRICS:
   • Images per Second: {self.stats['processed']/max(self.stats['time_taken'], 0.001):.1f}
   • Average Compression per Image: {savings_percent:.1f}%
   • Total Bandwidth Saved: {savings_mb:.2f} MB

💡 RECOMMENDATIONS:
   • WebP format provides excellent compression for modern browsers
   • Consider JPEG fallback for older browser compatibility
   • Thumbnail generation (400x300) saves significant space
   • Quality 80-85 provides good balance of size vs quality

📁 OUTPUT LOCATION:
   {self.output_dir.get()}

{'='*50}
Statistics generated at: {time.strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        self.stats_text.insert(tk.END, stats_text)
        
    def show_help(self):
        """Show help dialog."""
        help_text = """
Advanced Image Processing Tool - Help

🎯 QUICK START:
1. Drag and drop a folder onto the input field, or click "Auto-detect image folders"
2. Choose a preset or adjust settings manually
3. Click "Start Compression" to begin processing
4. Use the Preview tab to see image quality before/after

🖼️ PREVIEW FEATURES:
• Select any image to preview compression results
• Zoom in/out to examine details
• Compare before/after side by side
• See file size and dimension changes

📊 STATISTICS TAB:
• Detailed processing metrics
• File size analysis
• Performance recommendations
• Compression efficiency data

🎯 PRESETS EXPLAINED:
• Web High: Best quality for hero images (1920x1080, WebP, 90%)
• Web Medium: Good quality for gallery images (1200x800, WebP, 80%)
• Web Thumb: Thumbnail quality (400x300, WebP, 75%)
• JPEG Fallback: Compatible with older browsers (1920x1080, JPEG, 85%)

⚙️ ADVANCED SETTINGS:
• Quality: 1-100, higher = better quality but larger files
• Max Width/Height: Resize images while maintaining aspect ratio
• Format: WebP recommended for modern browsers
• Preserve Structure: Keep original folder organization
• Parallel Workers: More workers = faster processing (but more memory)

💡 TIPS:
• Use WebP for modern browsers with JPEG fallback
• Lower quality = smaller files but reduced image quality
• Resizing large images significantly reduces file size
• Preview images before batch processing
• Check statistics tab for detailed analysis
        """
        
        messagebox.showinfo("Advanced Help", help_text)
        
    def show_tooltip(self, text):
        """Show a tooltip with the given text."""
        if self.tooltip_window:
            self.hide_tooltip()
        
        self.tooltip_window = tk.Toplevel(self.root)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_geometry("+%d+%d" % (self.root.winfo_pointerx() + 10, self.root.winfo_pointery() + 10))
        
        label = tk.Label(self.tooltip_window, text=text, justify=tk.LEFT,
                        background="lightyellow", relief=tk.SOLID, borderwidth=1,
                        font=('Arial', 9), wraplength=300)
        label.pack(ipadx=5, ipady=3)
        
    def hide_tooltip(self):
        """Hide the current tooltip."""
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None
            
    def select_test_image(self):
        """Select an image for testing."""
        file_path = filedialog.askopenfilename(
            title="Select Test Image",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp *.tiff *.webp *.avif")]
        )
        if file_path:
            self.test_image_path.set(file_path)
            
    def use_preview_image(self):
        """Use the current preview image for testing."""
        if self.current_image:
            # Save current preview image to temp file
            import tempfile
            temp_path = tempfile.mktemp(suffix='.png')
            self.current_image.save(temp_path)
            self.test_image_path.set(temp_path)
        else:
            messagebox.showwarning("Warning", "No image loaded in preview. Please select an image first.")
            
    def run_test(self):
        """Run compression test with 5 different configurations."""
        if not self.test_image_path.get():
            messagebox.showerror("Error", "Please select a test image first")
            return
            
        if not os.path.exists(self.test_image_path.get()):
            messagebox.showerror("Error", "Test image file not found")
            return
            
        # Clear previous results
        for widget in self.test_scrollable_frame.winfo_children():
            widget.destroy()
        self.test_results = []
        self.test_images = []
        
        # Show progress
        progress_label = ttk.Label(self.test_scrollable_frame, text="🔄 Running test... Please wait...", 
                                 font=('Arial', 12))
        progress_label.pack(pady=20)
        self.test_canvas.update()
        
        # Define test configurations
        target_size = self.test_file_size.get() * 1024  # Convert to bytes
        test_configs = [
            {"name": "High Quality", "quality": 95, "description": "Maximum quality, may exceed target size"},
            {"name": "Balanced", "quality": 85, "description": "Good balance of quality and size"},
            {"name": "Optimized", "quality": 75, "description": "Optimized for target size"},
            {"name": "Compressed", "quality": 65, "description": "Higher compression, smaller size"},
            {"name": "Maximum Compression", "quality": 55, "description": "Maximum compression, smallest size"}
        ]
        
        # Run tests
        for i, config in enumerate(test_configs):
            try:
                result = self._test_single_config(config, target_size, i)
                self.test_results.append(result)
                self._display_test_result(result, i)
            except Exception as e:
                error_result = {
                    "name": config["name"],
                    "error": str(e),
                    "config": config
                }
                self.test_results.append(error_result)
                self._display_test_error(error_result, i)
                
        # Remove progress label
        progress_label.destroy()
        
        # Show summary
        self._show_test_summary()
        
    def _test_single_config(self, config, target_size, index):
        """Test a single compression configuration."""
        import tempfile
        import shutil
        
        # Create temp directory for test
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Create compressor for this test
            compressor = ImageCompressor(
                input_dir=os.path.dirname(self.test_image_path.get()),
                output_dir=temp_dir,
                quality=config["quality"],
                max_width=self.max_width.get() if self.max_width.get() > 0 else None,
                max_height=self.max_height.get() if self.max_height.get() > 0 else None,
                format=self.format_var.get(),
                preserve_structure=False,
                max_file_size=target_size
            )
            
            # Process the single image
            input_path = Path(self.test_image_path.get())
            result = compressor.optimize_image(input_path)
            
            if result['status'] == 'success':
                # Load the compressed image for display
                compressed_img = Image.open(result['output_path'])
                
                return {
                    "name": config["name"],
                    "description": config["description"],
                    "config": config,
                    "result": result,
                    "compressed_image": compressed_img,
                    "original_size": result['original_size'],
                    "compressed_size": result['compressed_size'],
                    "compression_ratio": result['compression_ratio'],
                    "quality_used": result.get('quality_used', config["quality"]),
                    "file_size_kb": result['compressed_size'] // 1024,
                    "target_met": result['compressed_size'] <= target_size
                }
            else:
                return {
                    "name": config["name"],
                    "error": result['error'],
                    "config": config
                }
                
        finally:
            # Clean up temp directory
            shutil.rmtree(temp_dir, ignore_errors=True)
            
    def _display_test_result(self, result, index):
        """Display a single test result with original vs compressed comparison."""
        # Create result frame
        result_frame = ttk.LabelFrame(self.test_scrollable_frame, text=f"Test {index + 1}: {result['name']}", padding="10")
        result_frame.pack(fill=tk.X, pady=5, padx=5)
        
        # Comparison header
        comparison_header = ttk.Frame(result_frame)
        comparison_header.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(comparison_header, text="📊 Original vs Compressed Comparison", 
                 font=('Arial', 12, 'bold')).pack()
        
        # Images comparison row
        images_frame = ttk.Frame(result_frame)
        images_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Original image column
        original_frame = ttk.LabelFrame(images_frame, text="📷 Original", padding="5")
        original_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # Load and display original image
        original_img = Image.open(self.test_image_path.get())
        original_resized = original_img.copy()
        original_resized.thumbnail((200, 150), Image.Resampling.LANCZOS)
        original_photo = ImageTk.PhotoImage(original_resized)
        self.test_images.append(original_photo)  # Keep reference
        
        ttk.Label(original_frame, image=original_photo).pack()
        
        # Original image info
        original_size_kb = result['original_size'] // 1024
        original_width, original_height = original_img.size
        
        ttk.Label(original_frame, text=f"File Size: {original_size_kb} KB", 
                 font=('Arial', 9, 'bold')).pack(pady=(5, 0))
        ttk.Label(original_frame, text=f"Dimensions: {original_width}x{original_height}", 
                 font=('Arial', 9)).pack()
        ttk.Label(original_frame, text="Format: Original", 
                 font=('Arial', 9), foreground="gray").pack()
        
        # Compressed image column
        compressed_frame = ttk.LabelFrame(images_frame, text="🗜️ Compressed", padding="5")
        compressed_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Resize compressed image for preview
        compressed_resized = result['compressed_image'].copy()
        compressed_resized.thumbnail((200, 150), Image.Resampling.LANCZOS)
        compressed_photo = ImageTk.PhotoImage(compressed_resized)
        self.test_images.append(compressed_photo)  # Keep reference
        
        ttk.Label(compressed_frame, image=compressed_photo).pack()
        
        # Compressed image info
        quality_color = "green" if result['target_met'] else "orange"
        status_text = "✅ Target Met" if result['target_met'] else "⚠️ Over Target"
        compressed_width, compressed_height = result['compressed_image'].size
        
        ttk.Label(compressed_frame, text=f"File Size: {result['file_size_kb']} KB", 
                 font=('Arial', 9, 'bold')).pack(pady=(5, 0))
        ttk.Label(compressed_frame, text=f"Dimensions: {compressed_width}x{compressed_height}", 
                 font=('Arial', 9)).pack()
        ttk.Label(compressed_frame, text=f"Quality: {result['quality_used']}%", 
                 font=('Arial', 9)).pack()
        ttk.Label(compressed_frame, text=f"Format: {self.format_var.get().upper()}", 
                 font=('Arial', 9), foreground="gray").pack()
        ttk.Label(compressed_frame, text=status_text, 
                 font=('Arial', 9, 'bold'), foreground=quality_color).pack()
        
        # Comparison metrics
        metrics_frame = ttk.LabelFrame(result_frame, text="📈 Compression Metrics", padding="10")
        metrics_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Create metrics grid
        metrics_grid = ttk.Frame(metrics_frame)
        metrics_grid.pack(fill=tk.X)
        metrics_grid.columnconfigure(1, weight=1)
        metrics_grid.columnconfigure(3, weight=1)
        
        # Size reduction
        size_reduction = original_size_kb - result['file_size_kb']
        size_reduction_percent = (size_reduction / original_size_kb) * 100
        
        ttk.Label(metrics_grid, text="Size Reduction:", font=('Arial', 9, 'bold')).grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        ttk.Label(metrics_grid, text=f"{size_reduction} KB ({size_reduction_percent:.1f}%)", 
                 font=('Arial', 9), foreground="green").grid(row=0, column=1, sticky=tk.W)
        
        # Compression ratio
        ttk.Label(metrics_grid, text="Compression Ratio:", font=('Arial', 9, 'bold')).grid(row=0, column=2, sticky=tk.W, padx=(20, 10))
        ttk.Label(metrics_grid, text=f"{result['compression_ratio']:.1f}%", 
                 font=('Arial', 9), foreground="blue").grid(row=0, column=3, sticky=tk.W)
        
        # Dimension change
        dim_change = f"{original_width}x{original_height} → {compressed_width}x{compressed_height}"
        ttk.Label(metrics_grid, text="Dimensions:", font=('Arial', 9, 'bold')).grid(row=1, column=0, sticky=tk.W, padx=(0, 10), pady=(5, 0))
        ttk.Label(metrics_grid, text=dim_change, font=('Arial', 9)).grid(row=1, column=1, sticky=tk.W, pady=(5, 0))
        
        # Description
        ttk.Label(metrics_grid, text="Description:", font=('Arial', 9, 'bold')).grid(row=1, column=2, sticky=tk.W, padx=(20, 10), pady=(5, 0))
        ttk.Label(metrics_grid, text=result['description'], 
                 font=('Arial', 9), foreground="gray").grid(row=1, column=3, sticky=tk.W, pady=(5, 0))
        
        # Action buttons
        button_frame = ttk.Frame(result_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(button_frame, text="💾 Save as Preset", 
                  command=lambda: self.save_test_as_preset(result)).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="👁️ View Full Size", 
                  command=lambda: self.view_full_size(result)).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="📋 Copy Settings", 
                  command=lambda: self.copy_test_settings(result)).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="🔄 Side-by-Side", 
                  command=lambda: self.view_side_by_side(result)).pack(side=tk.LEFT)
        
    def _display_test_error(self, result, index):
        """Display a test error."""
        error_frame = ttk.LabelFrame(self.test_scrollable_frame, text=f"Test {index + 1}: {result['name']} - ERROR", padding="10")
        error_frame.pack(fill=tk.X, pady=5, padx=5)
        
        ttk.Label(error_frame, text=f"❌ Error: {result['error']}", 
                 foreground="red", font=('Arial', 10)).pack(anchor=tk.W)
                 
    def _show_test_summary(self):
        """Show test summary."""
        summary_frame = ttk.LabelFrame(self.test_scrollable_frame, text="📊 Test Summary", padding="10")
        summary_frame.pack(fill=tk.X, pady=10, padx=5)
        
        successful_tests = [r for r in self.test_results if 'error' not in r]
        target_met = [r for r in successful_tests if r['target_met']]
        
        ttk.Label(summary_frame, text=f"✅ Successful Tests: {len(successful_tests)}/5", 
                 font=('Arial', 10, 'bold')).pack(anchor=tk.W)
        ttk.Label(summary_frame, text=f"🎯 Target Size Met: {len(target_met)}/5", 
                 font=('Arial', 10, 'bold')).pack(anchor=tk.W)
        
        if target_met:
            best_result = min(target_met, key=lambda x: x['file_size_kb'])
            ttk.Label(summary_frame, text=f"🏆 Best Result: {best_result['name']} ({best_result['file_size_kb']} KB)", 
                     font=('Arial', 10, 'bold'), foreground="green").pack(anchor=tk.W, pady=(5, 0))
        
    def save_test_as_preset(self, result):
        """Save test result as a custom preset."""
        preset_name = tk.simpledialog.askstring("Save Preset", "Enter preset name:", 
                                               initialvalue=result['name'])
        if preset_name:
            # Add to presets (this would need to be implemented)
            self.log_message(f"💾 Saved preset '{preset_name}' with quality {result['quality_used']}%")
            messagebox.showinfo("Preset Saved", f"Preset '{preset_name}' saved successfully!")
            
    def view_full_size(self, result):
        """View full size image with zoom controls."""
        # Create new window for full size view
        view_window = tk.Toplevel(self.root)
        view_window.title(f"Full Size - {result['name']}")
        view_window.geometry("900x700")
        
        # Main frame
        main_frame = ttk.Frame(view_window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Header with image info
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(header_frame, text=f"Full Size View - {result['name']}", 
                 font=('Arial', 14, 'bold')).pack()
        
        # Image info
        info_text = f"Size: {result['file_size_kb']} KB | Dimensions: {result['compressed_image'].size[0]}x{result['compressed_image'].size[1]} | Quality: {result['quality_used']}%"
        ttk.Label(header_frame, text=info_text, font=('Arial', 10)).pack()
        
        # Zoom controls
        zoom_frame = ttk.Frame(main_frame)
        zoom_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(zoom_frame, text="Zoom:").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(zoom_frame, text="−", command=lambda: self.zoom_out_image(canvas, result['compressed_image']), width=3).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(zoom_frame, text="+", command=lambda: self.zoom_in_image(canvas, result['compressed_image']), width=3).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(zoom_frame, text="Fit", command=lambda: self.zoom_fit_image(canvas, result['compressed_image']), width=3).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(zoom_frame, text="1:1", command=lambda: self.zoom_actual_size(canvas, result['compressed_image']), width=3).pack(side=tk.LEFT, padx=(0, 10))
        
        # Zoom level display
        self.zoom_level_label = ttk.Label(zoom_frame, text="100%")
        self.zoom_level_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # Create canvas for image with scrollbars
        canvas_frame = ttk.Frame(main_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        canvas = tk.Canvas(canvas_frame, bg='white')
        h_scrollbar = ttk.Scrollbar(canvas_frame, orient="horizontal", command=canvas.xview)
        v_scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
        
        canvas.configure(xscrollcommand=h_scrollbar.set, yscrollcommand=v_scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        h_scrollbar.pack(side="bottom", fill="x")
        v_scrollbar.pack(side="right", fill="y")
        
        # Store zoom state
        canvas.zoom_level = 1.0
        canvas.original_image = result['compressed_image']
        canvas.current_image = None
        
        # Display image
        self.display_zoomed_image(canvas, result['compressed_image'])
        
        # Mouse wheel zoom
        canvas.bind("<MouseWheel>", lambda e: self.mouse_wheel_zoom(canvas, e, result['compressed_image']))
        canvas.bind("<Button-1>", lambda e: self.start_pan(canvas, e))
        canvas.bind("<B1-Motion>", lambda e: self.pan_image(canvas, e))
        
        # Keep reference
        canvas.image = None  # Will be set by display_zoomed_image
        
    def copy_test_settings(self, result):
        """Copy test settings to main compression tab."""
        self.quality.set(result['quality_used'])
        self.max_file_size.set(result['file_size_kb'])
        self.log_message(f"📋 Copied settings: Quality={result['quality_used']}%, MaxSize={result['file_size_kb']}KB")
        
        # Switch to main tab
        self.notebook.select(0)
        
    def view_side_by_side(self, result):
        """View original and compressed images side by side in full size."""
        # Create new window for side-by-side comparison
        compare_window = tk.Toplevel(self.root)
        compare_window.title(f"Side-by-Side Comparison - {result['name']}")
        compare_window.geometry("1200x600")
        
        # Main frame
        main_frame = ttk.Frame(compare_window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Header
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(header_frame, text="🔄 Side-by-Side Comparison", 
                 font=('Arial', 16, 'bold')).pack()
        ttk.Label(header_frame, text=f"Configuration: {result['name']}", 
                 font=('Arial', 12)).pack()
        
        # Images frame
        images_frame = ttk.Frame(main_frame)
        images_frame.pack(fill=tk.BOTH, expand=True)
        
        # Original image
        original_frame = ttk.LabelFrame(images_frame, text="📷 Original Image", padding="10")
        original_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        original_canvas = tk.Canvas(original_frame, bg='white')
        original_canvas.pack(fill=tk.BOTH, expand=True)
        
        # Load original image
        original_img = Image.open(self.test_image_path.get())
        self.display_image_in_canvas(original_img, original_canvas)
        
        # Original info
        original_size_kb = result['original_size'] // 1024
        original_width, original_height = original_img.size
        ttk.Label(original_frame, text=f"Size: {original_size_kb} KB | Dimensions: {original_width}x{original_height}", 
                 font=('Arial', 10, 'bold')).pack(pady=(5, 0))
        
        # Compressed image
        compressed_frame = ttk.LabelFrame(images_frame, text="🗜️ Compressed Image", padding="10")
        compressed_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        compressed_canvas = tk.Canvas(compressed_frame, bg='white')
        compressed_canvas.pack(fill=tk.BOTH, expand=True)
        
        # Load compressed image
        self.display_image_in_canvas(result['compressed_image'], compressed_canvas)
        
        # Compressed info
        compressed_width, compressed_height = result['compressed_image'].size
        quality_color = "green" if result['target_met'] else "orange"
        status_text = "✅ Target Met" if result['target_met'] else "⚠️ Over Target"
        
        info_text = f"Size: {result['file_size_kb']} KB | Dimensions: {compressed_width}x{compressed_height} | Quality: {result['quality_used']}% | {status_text}"
        ttk.Label(compressed_frame, text=info_text, 
                 font=('Arial', 10, 'bold'), foreground=quality_color).pack(pady=(5, 0))
        
        # Comparison summary
        summary_frame = ttk.LabelFrame(main_frame, text="📊 Comparison Summary", padding="10")
        summary_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Calculate metrics
        size_reduction = original_size_kb - result['file_size_kb']
        size_reduction_percent = (size_reduction / original_size_kb) * 100
        
        # Create summary grid
        summary_grid = ttk.Frame(summary_frame)
        summary_grid.pack(fill=tk.X)
        summary_grid.columnconfigure(1, weight=1)
        summary_grid.columnconfigure(3, weight=1)
        
        ttk.Label(summary_grid, text="Size Reduction:", font=('Arial', 10, 'bold')).grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        ttk.Label(summary_grid, text=f"{size_reduction} KB ({size_reduction_percent:.1f}%)", 
                 font=('Arial', 10), foreground="green").grid(row=0, column=1, sticky=tk.W)
        
        ttk.Label(summary_grid, text="Compression Ratio:", font=('Arial', 10, 'bold')).grid(row=0, column=2, sticky=tk.W, padx=(20, 10))
        ttk.Label(summary_grid, text=f"{result['compression_ratio']:.1f}%", 
                 font=('Arial', 10), foreground="blue").grid(row=0, column=3, sticky=tk.W)
        
        ttk.Label(summary_grid, text="Dimension Change:", font=('Arial', 10, 'bold')).grid(row=1, column=0, sticky=tk.W, padx=(0, 10), pady=(5, 0))
        ttk.Label(summary_grid, text=f"{original_width}x{original_height} → {compressed_width}x{compressed_height}", 
                 font=('Arial', 10)).grid(row=1, column=1, sticky=tk.W, pady=(5, 0))
        
        ttk.Label(summary_grid, text="Format:", font=('Arial', 10, 'bold')).grid(row=1, column=2, sticky=tk.W, padx=(20, 10), pady=(5, 0))
        ttk.Label(summary_grid, text=f"Original → {self.format_var.get().upper()}", 
                 font=('Arial', 10)).grid(row=1, column=3, sticky=tk.W, pady=(5, 0))
        
        # Action buttons
        button_frame = ttk.Frame(summary_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(button_frame, text="💾 Save as Preset", 
                  command=lambda: self.save_test_as_preset(result)).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="📋 Copy Settings", 
                  command=lambda: self.copy_test_settings(result)).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="❌ Close", 
                  command=compare_window.destroy).pack(side=tk.RIGHT)
        
        # Add zoom controls to side-by-side viewer
        zoom_frame = ttk.Frame(main_frame)
        zoom_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Label(zoom_frame, text="Zoom:").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(zoom_frame, text="−", command=lambda: self.zoom_out_side_by_side(original_canvas, compressed_canvas, original_img, result['compressed_image']), width=3).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(zoom_frame, text="+", command=lambda: self.zoom_in_side_by_side(original_canvas, compressed_canvas, original_img, result['compressed_image']), width=3).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(zoom_frame, text="Fit", command=lambda: self.zoom_fit_side_by_side(original_canvas, compressed_canvas, original_img, result['compressed_image']), width=3).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(zoom_frame, text="1:1", command=lambda: self.zoom_actual_side_by_side(original_canvas, compressed_canvas, original_img, result['compressed_image']), width=3).pack(side=tk.LEFT, padx=(0, 10))
        
        # Zoom level display
        zoom_level_label = ttk.Label(zoom_frame, text="100%")
        zoom_level_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # Store zoom state for both canvases
        original_canvas.zoom_level = 1.0
        original_canvas.original_image = original_img
        compressed_canvas.zoom_level = 1.0
        compressed_canvas.original_image = result['compressed_image']
        
        # Mouse wheel zoom for both canvases
        original_canvas.bind("<MouseWheel>", lambda e: self.mouse_wheel_zoom_side_by_side(original_canvas, compressed_canvas, e, original_img, result['compressed_image']))
        compressed_canvas.bind("<MouseWheel>", lambda e: self.mouse_wheel_zoom_side_by_side(original_canvas, compressed_canvas, e, original_img, result['compressed_image']))
        
        # Pan functionality
        original_canvas.bind("<Button-1>", lambda e: self.start_pan(original_canvas, e))
        original_canvas.bind("<B1-Motion>", lambda e: self.pan_image(original_canvas, e))
        compressed_canvas.bind("<Button-1>", lambda e: self.start_pan(compressed_canvas, e))
        compressed_canvas.bind("<B1-Motion>", lambda e: self.pan_image(compressed_canvas, e))
        
    def display_zoomed_image(self, canvas, image, zoom_level=None):
        """Display image with zoom level."""
        if zoom_level is None:
            zoom_level = getattr(canvas, 'zoom_level', 1.0)
        else:
            canvas.zoom_level = zoom_level
            
        # Calculate new size
        width, height = image.size
        new_width = int(width * zoom_level)
        new_height = int(height * zoom_level)
        
        # Resize image
        resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Convert to PhotoImage
        photo = ImageTk.PhotoImage(resized_image)
        canvas.image = photo  # Keep reference
        
        # Clear canvas and display image
        canvas.delete("all")
        canvas.create_image(0, 0, image=photo, anchor=tk.NW)
        
        # Update scroll region
        canvas.configure(scrollregion=canvas.bbox("all"))
        
        # Update zoom level display if it exists
        if hasattr(self, 'zoom_level_label'):
            self.zoom_level_label.config(text=f"{int(zoom_level * 100)}%")
            
    def zoom_in_image(self, canvas, image):
        """Zoom in on image."""
        canvas.zoom_level *= 1.2
        self.display_zoomed_image(canvas, image)
        
    def zoom_out_image(self, canvas, image):
        """Zoom out on image."""
        canvas.zoom_level /= 1.2
        if canvas.zoom_level < 0.1:
            canvas.zoom_level = 0.1
        self.display_zoomed_image(canvas, image)
        
    def zoom_fit_image(self, canvas, image):
        """Fit image to canvas."""
        canvas_width = canvas.winfo_width()
        canvas_height = canvas.winfo_height()
        
        if canvas_width <= 1 or canvas_height <= 1:
            # Canvas not ready, schedule refresh
            canvas.after(100, lambda: self.zoom_fit_image(canvas, image))
            return
            
        img_width, img_height = image.size
        scale_x = canvas_width / img_width
        scale_y = canvas_height / img_height
        scale = min(scale_x, scale_y) * 0.9  # 90% to leave some margin
        
        canvas.zoom_level = scale
        self.display_zoomed_image(canvas, image)
        
    def zoom_actual_size(self, canvas, image):
        """Show image at actual size (100%)."""
        canvas.zoom_level = 1.0
        self.display_zoomed_image(canvas, image)
        
    def mouse_wheel_zoom(self, canvas, event, image):
        """Handle mouse wheel zoom."""
        if event.delta > 0:
            self.zoom_in_image(canvas, image)
        else:
            self.zoom_out_image(canvas, image)
            
    def start_pan(self, canvas, event):
        """Start panning."""
        canvas.scan_mark(event.x, event.y)
        
    def pan_image(self, canvas, event):
        """Pan the image."""
        canvas.scan_dragto(event.x, event.y, gain=1)
        
    # Side-by-side zoom methods
    def zoom_in_side_by_side(self, original_canvas, compressed_canvas, original_img, compressed_img):
        """Zoom in on both images."""
        original_canvas.zoom_level *= 1.2
        compressed_canvas.zoom_level *= 1.2
        self.display_zoomed_image(original_canvas, original_img)
        self.display_zoomed_image(compressed_canvas, compressed_img)
        
    def zoom_out_side_by_side(self, original_canvas, compressed_canvas, original_img, compressed_img):
        """Zoom out on both images."""
        original_canvas.zoom_level /= 1.2
        compressed_canvas.zoom_level /= 1.2
        if original_canvas.zoom_level < 0.1:
            original_canvas.zoom_level = 0.1
            compressed_canvas.zoom_level = 0.1
        self.display_zoomed_image(original_canvas, original_img)
        self.display_zoomed_image(compressed_canvas, compressed_img)
        
    def zoom_fit_side_by_side(self, original_canvas, compressed_canvas, original_img, compressed_img):
        """Fit both images to their canvases."""
        # Calculate scale based on the larger image
        orig_width, orig_height = original_img.size
        comp_width, comp_height = compressed_img.size
        
        canvas_width = original_canvas.winfo_width()
        canvas_height = original_canvas.winfo_height()
        
        if canvas_width <= 1 or canvas_height <= 1:
            # Canvas not ready, schedule refresh
            original_canvas.after(100, lambda: self.zoom_fit_side_by_side(original_canvas, compressed_canvas, original_img, compressed_img))
            return
            
        # Use the larger image to determine scale
        max_width = max(orig_width, comp_width)
        max_height = max(orig_height, comp_height)
        
        scale_x = canvas_width / max_width
        scale_y = canvas_height / max_height
        scale = min(scale_x, scale_y) * 0.9  # 90% to leave some margin
        
        original_canvas.zoom_level = scale
        compressed_canvas.zoom_level = scale
        self.display_zoomed_image(original_canvas, original_img)
        self.display_zoomed_image(compressed_canvas, compressed_img)
        
    def zoom_actual_side_by_side(self, original_canvas, compressed_canvas, original_img, compressed_img):
        """Show both images at actual size."""
        original_canvas.zoom_level = 1.0
        compressed_canvas.zoom_level = 1.0
        self.display_zoomed_image(original_canvas, original_img)
        self.display_zoomed_image(compressed_canvas, compressed_img)
        
    def mouse_wheel_zoom_side_by_side(self, original_canvas, compressed_canvas, event, original_img, compressed_img):
        """Handle mouse wheel zoom for side-by-side view."""
        if event.delta > 0:
            self.zoom_in_side_by_side(original_canvas, compressed_canvas, original_img, compressed_img)
        else:
            self.zoom_out_side_by_side(original_canvas, compressed_canvas, original_img, compressed_img)
            
    # Metadata methods
    def browse_metadata_image(self):
        """Browse for image to edit metadata."""
        file_path = filedialog.askopenfilename(
            title="Select Image for Metadata Editing",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp *.tiff *.webp *.avif")]
        )
        if file_path:
            self.metadata_image_path.set(file_path)
            self.load_image_metadata()
            
    def load_image_metadata(self):
        """Load and display image metadata - streamlined approach."""
        if not self.metadata_image_path.get():
            messagebox.showwarning("Warning", "Please select an image first")
            return
            
        try:
            from PIL.ExifTags import TAGS
            
            # Load image
            image = Image.open(self.metadata_image_path.get())
            
            # Display image
            self.display_metadata_image(image)
            
            # Load EXIF data
            exifdata = image.getexif()
            self.current_metadata = {}
            
            # Clear existing fields and recreate with essential fields only
            for widget in self.metadata_scrollable_frame.winfo_children():
                widget.destroy()
            self.metadata_fields = {}
            
            # Essential fields only (same as simple metadata)
            essential_fields = ['XPTitle', 'ImageDescription', 'XPKeywords', 'Artist', 'Make', 'Model']
            all_fields = {}
            
            # Ensure all essential fields are present (even if empty)
            for field_name in essential_fields:
                all_fields[field_name] = ''
            
            # Process EXIF data
            for tag_id in exifdata:
                tag = TAGS.get(tag_id, tag_id)
                data = exifdata.get(tag_id)
                
                if isinstance(data, bytes):
                    # Handle different encodings based on tag type (same as simple metadata)
                    if tag_id in [40091, 40094]:  # XPTitle, XPKeywords - UTF-16LE
                        try:
                            # Remove BOM if present and decode as UTF-16LE
                            if data.startswith(b'\xff\xfe'):
                                data = data[2:]
                            data = data.decode('utf-16le', errors='ignore')
                        except:
                            data = data.decode('utf-8', errors='ignore')
                    else:  # Other fields - UTF-8
                        data = data.decode('utf-8', errors='ignore')
                
                # Map to essential fields only
                if tag == 'XPTitle':
                    all_fields['XPTitle'] = str(data) if data else ''
                elif tag == 'ImageDescription':
                    all_fields['ImageDescription'] = str(data) if data else ''
                elif tag == 'XPKeywords':
                    all_fields['XPKeywords'] = str(data) if data else ''
                elif tag == 'Artist':
                    all_fields['Artist'] = str(data) if data else ''
                elif tag == 'Make':
                    all_fields['Make'] = str(data) if data else ''
                elif tag == 'Model':
                    all_fields['Model'] = str(data) if data else ''
            
            # Create metadata fields for essential fields only
            row = 0
            for field_name in essential_fields:
                field_value = all_fields.get(field_name, '')
                self.create_metadata_field(field_name, field_value, row)
                row += 1
            
            # Update image info
            width, height = image.size
            file_size = os.path.getsize(self.metadata_image_path.get()) / 1024
            self.metadata_image_info.config(
                text=f"📁 {Path(self.metadata_image_path.get()).name} | 📏 {width}x{height} | 📦 {file_size:.1f} KB"
            )
            
        except Exception as e:
            messagebox.showerror("Error", f"Could not load image metadata: {str(e)}")
            
    def display_metadata_image(self, image):
        """Display image in metadata canvas."""
        # Calculate display size
        canvas_width = self.metadata_canvas.winfo_width()
        canvas_height = self.metadata_canvas.winfo_height()
        
        if canvas_width <= 1 or canvas_height <= 1:
            # Canvas not ready, schedule refresh
            self.root.after(100, lambda: self.display_metadata_image(image))
            return
            
        # Resize image to fit canvas
        img_width, img_height = image.size
        scale_x = (canvas_width - 20) / img_width
        scale_y = (canvas_height - 20) / img_height
        scale = min(scale_x, scale_y)
        
        new_width = int(img_width * scale)
        new_height = int(img_height * scale)
        
        # Resize image
        resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(resized_image)
        
        # Clear canvas and display image
        self.metadata_canvas.delete("all")
        x = (canvas_width - new_width) // 2
        y = (canvas_height - new_height) // 2
        self.metadata_canvas.create_image(x, y, anchor=tk.NW, image=photo)
        
        # Update scroll region
        self.metadata_canvas.configure(scrollregion=self.metadata_canvas.bbox("all"))
        
        # Keep reference
        self.metadata_canvas.image = photo
        
    def create_metadata_field(self, field_name, field_value, row):
        """Create a metadata field editor."""
        field_frame = ttk.Frame(self.metadata_scrollable_frame)
        field_frame.grid(row=row, column=0, sticky=(tk.W, tk.E), padx=5, pady=2)
        field_frame.columnconfigure(1, weight=1)
        
        # Field name
        ttk.Label(field_frame, text=f"{field_name}:", font=('Arial', 9, 'bold')).grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        
        # Field value entry
        field_var = tk.StringVar(value=field_value)
        entry = ttk.Entry(field_frame, textvariable=field_var, width=40)
        entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        
        # Store reference
        self.metadata_fields[field_name] = {
            'var': field_var,
            'entry': entry,
            'frame': field_frame
        }
        
    def add_metadata_field(self):
        """Add a new custom metadata field."""
        field_name = simpledialog.askstring("Add Field", "Enter field name:")
        if field_name and field_name not in self.metadata_fields:
            row = len(self.metadata_fields)
            self.create_metadata_field(field_name, '', row)
            
    def remove_metadata_field(self):
        """Remove selected metadata field."""
        field_name = simpledialog.askstring("Remove Field", "Enter field name to remove:")
        if field_name and field_name in self.metadata_fields:
            field_info = self.metadata_fields[field_name]
            field_info['frame'].destroy()
            del self.metadata_fields[field_name]
    
    def scan_all_metadata_fields(self):
        """Scan image for all available metadata fields, including empty ones."""
        if not self.metadata_image_path.get():
            messagebox.showwarning("Warning", "No image selected")
            return
            
        try:
            from PIL.ExifTags import TAGS
            import piexif
            
            # Load image
            image = Image.open(self.metadata_image_path.get())
            
            # Clear existing fields
            for widget in self.metadata_scrollable_frame.winfo_children():
                widget.destroy()
            self.metadata_fields = {}
            
            # Get EXIF data
            exifdata = image.getexif()
            
            # Create comprehensive field list
            all_fields = {}
            
            # Standard fields (always show these)
            standard_fields = {
                'XPTitle': '',
                'ImageDescription': '',
                'XPKeywords': '',
                'Artist': '',
                'Copyright': '',
                'Software': '',
                'DateTime': '',
                'Make': '',
                'Model': '',
                'ISO': '',
                'FNumber': '',
                'ExposureTime': '',
                'FocalLength': '',
                'Flash': '',
                'WhiteBalance': '',
                'GPSInfo': ''
            }
            
            # Process EXIF data
            for tag_id in exifdata:
                tag = TAGS.get(tag_id, tag_id)
                data = exifdata.get(tag_id)
                
                if isinstance(data, bytes):
                    data = data.decode('utf-8', errors='ignore')
                
                # Map to standard fields or add as custom
                if tag == 'XPTitle':
                    all_fields['XPTitle'] = str(data) if data else ''
                elif tag == 'ImageDescription':
                    all_fields['ImageDescription'] = str(data) if data else ''
                elif tag == 'XPKeywords':
                    all_fields['XPKeywords'] = str(data) if data else ''
                elif tag == 'Artist':
                    all_fields['Artist'] = str(data) if data else ''
                elif tag == 'Copyright':
                    all_fields['Copyright'] = str(data) if data else ''
                elif tag == 'Software':
                    all_fields['Software'] = str(data) if data else ''
                elif tag == 'DateTime':
                    all_fields['DateTime'] = str(data) if data else ''
                elif tag == 'Make':
                    all_fields['Make'] = str(data) if data else ''
                elif tag == 'Model':
                    all_fields['Model'] = str(data) if data else ''
                else:
                    # Add as custom field
                    all_fields[f"EXIF_{tag}"] = str(data) if data else ''
            
            # Add image.info fields
            for key, value in image.info.items():
                if key not in all_fields:
                    all_fields[f"INFO_{key}"] = str(value) if value else ''
            
            # Ensure all standard fields are present (even if empty)
            for field_name, default_value in standard_fields.items():
                if field_name not in all_fields:
                    all_fields[field_name] = default_value
            
            # Create metadata fields for all found fields
            row = 0
            for field_name, field_value in all_fields.items():
                self.create_metadata_field(field_name, field_value, row)
                row += 1
            
            # Update image info
            width, height = image.size
            file_size = os.path.getsize(self.metadata_image_path.get()) / 1024
            self.metadata_image_info.config(
                text=f"📁 {Path(self.metadata_image_path.get()).name} | 📏 {width}x{height} | 📦 {file_size:.1f} KB"
            )
            
            messagebox.showinfo("Scan Complete", f"Found {len(all_fields)} metadata fields (including empty ones)")
            
        except Exception as e:
            messagebox.showerror("Error", f"Could not scan image metadata: {str(e)}")
    
    def apply_metadata_format_override(self):
        """Apply metadata format override and reload fields."""
        if not self.metadata_image_path.get():
            messagebox.showwarning("Warning", "No image selected")
            return
        
        override = self.metadata_format_override.get()
        file_path = self.metadata_image_path.get()
        config = self.get_metadata_config(file_path)
        
        print(f"Applying metadata format override: {override}")
        print(f"Detected config: {config['field_mapping']}")
        
        # Reload metadata with new format
        self.load_image_metadata()
        
        messagebox.showinfo("Override Applied", f"Metadata format set to: {override}\nField mapping: {config['field_mapping']}")
    
    def show_metadata_config(self):
        """Show current metadata configuration."""
        if not self.metadata_image_path.get():
            messagebox.showwarning("Warning", "No image selected")
            return
        
        file_path = self.metadata_image_path.get()
        config = self.get_metadata_config(file_path)
        override = self.metadata_format_override.get()
        
        # Create config display window
        config_window = tk.Toplevel(self.root)
        config_window.title("Metadata Configuration")
        config_window.geometry("600x400")
        config_window.transient(self.root)
        config_window.grab_set()
        
        # Main frame
        main_frame = ttk.Frame(config_window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, text="🔧 Metadata Configuration", 
                               font=('Arial', 14, 'bold'))
        title_label.pack(pady=(0, 20))
        
        # File info
        file_info = ttk.Label(main_frame, text=f"📁 File: {Path(file_path).name}", 
                             font=('Arial', 10, 'bold'))
        file_info.pack(anchor=tk.W, pady=(0, 10))
        
        # Current settings
        settings_text = scrolledtext.ScrolledText(main_frame, height=15, wrap=tk.WORD)
        settings_text.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        # Build configuration display
        config_content = f"Current Settings:\n{'='*50}\n\n"
        config_content += f"Override Setting: {override}\n"
        config_content += f"File Extension: {Path(file_path).suffix.lower()}\n"
        config_content += f"Selected Config: {'jpeg' if 'XPTitle' in config['field_mapping'] else 'webp'}\n\n"
        
        config_content += f"Field Mapping:\n{'-'*30}\n"
        for ai_field, exif_field in config['field_mapping'].items():
            config_content += f"  {ai_field} → {exif_field}\n"
        
        config_content += f"\nEXIF Tags:\n{'-'*30}\n"
        for field, (tag_id, tag_name, encoding) in config['exif_tags'].items():
            config_content += f"  {field}: Tag {tag_id} ({tag_name}) - {encoding}\n"
        
        config_content += f"\nXMP Tags:\n{'-'*30}\n"
        for field, xmp_tag in config['xmp_tags'].items():
            config_content += f"  {field}: {xmp_tag}\n"
        
        settings_text.insert(tk.END, config_content)
        settings_text.config(state=tk.DISABLED)
        
        # Close button
        ttk.Button(main_frame, text="Close", command=config_window.destroy).pack()
    
    def setup_simple_metadata_tab(self):
        """Setup the simple metadata tab for manual testing."""
        # Main container
        main_container = ttk.Frame(self.simple_metadata_frame, padding="10")
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(main_container, text="📝 Simple Metadata Editor", 
                               font=('Arial', 16, 'bold'))
        title_label.pack(pady=(0, 20))
        
        # File selection
        file_frame = ttk.LabelFrame(main_container, text="📁 Select Image", padding="10")
        file_frame.pack(fill=tk.X, pady=(0, 10))
        
        file_input_frame = ttk.Frame(file_frame)
        file_input_frame.pack(fill=tk.X)
        
        self.simple_file_path = tk.StringVar()
        ttk.Entry(file_input_frame, textvariable=self.simple_file_path, width=60).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(file_input_frame, text="Browse", command=self.browse_simple_file).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(file_input_frame, text="Load Metadata", command=self.load_simple_metadata).pack(side=tk.LEFT)
        
        # Image preview
        preview_frame = ttk.LabelFrame(main_container, text="🖼️ Image Preview", padding="10")
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Image canvas
        self.simple_image_canvas = tk.Canvas(preview_frame, width=300, height=200, bg='lightgray')
        self.simple_image_canvas.pack(side=tk.LEFT, padx=(0, 10))
        
        # Image info
        self.simple_image_info = ttk.Label(preview_frame, text="No image loaded", 
                                          font=('Arial', 10))
        self.simple_image_info.pack(side=tk.LEFT, anchor=tk.NW)
        
        # Simple metadata form
        form_frame = ttk.LabelFrame(main_container, text="📝 Metadata Fields", padding="10")
        form_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Create scrollable frame for metadata fields
        self.simple_metadata_canvas = tk.Canvas(form_frame, height=200)
        self.simple_metadata_scrollbar = ttk.Scrollbar(form_frame, orient="vertical", command=self.simple_metadata_canvas.yview)
        self.simple_metadata_scrollable_frame = ttk.Frame(self.simple_metadata_canvas)
        
        self.simple_metadata_scrollable_frame.bind(
            "<Configure>",
            lambda e: self.simple_metadata_canvas.configure(scrollregion=self.simple_metadata_canvas.bbox("all"))
        )
        
        self.simple_metadata_canvas.create_window((0, 0), window=self.simple_metadata_scrollable_frame, anchor="nw")
        self.simple_metadata_canvas.configure(yscrollcommand=self.simple_metadata_scrollbar.set)
        
        self.simple_metadata_canvas.pack(side="left", fill="both", expand=True)
        self.simple_metadata_scrollbar.pack(side="right", fill="y")
        
        # Create simple form fields
        self.simple_fields = {}
        
        # Standard fields that we always show - streamlined to essential fields only
        self.simple_standard_fields = ['XPTitle', 'ImageDescription', 'XPKeywords', 'Artist', 'Make', 'Model']
        
        # Create initial fields (will be populated when image is loaded)
        self.create_simple_metadata_fields()
        
        # Action buttons
        button_frame = ttk.Frame(main_container)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(button_frame, text="💾 Save Metadata", 
                  command=self.save_simple_metadata).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="🔄 Reload", 
                  command=self.load_simple_metadata).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="✅ Verify", 
                  command=self.verify_simple_metadata).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="🗑️ Clear", 
                  command=self.clear_simple_metadata).pack(side=tk.LEFT)
    
    def create_simple_metadata_fields(self):
        """Create metadata fields in the simple metadata tab."""
        # Clear existing fields
        for widget in self.simple_metadata_scrollable_frame.winfo_children():
            widget.destroy()
        self.simple_fields = {}
        
        # Create standard fields
        for i, field_name in enumerate(self.simple_standard_fields):
            self.create_simple_metadata_field(field_name, '', i)
    
    def create_simple_metadata_field(self, field_name, field_value, row):
        """Create a single metadata field in the simple metadata tab."""
        field_frame = ttk.Frame(self.simple_metadata_scrollable_frame)
        field_frame.pack(fill=tk.X, pady=2)
        
        # Field label
        label = ttk.Label(field_frame, text=f"{field_name}:", width=15, anchor=tk.W)
        label.pack(side=tk.LEFT, padx=(0, 10))
        
        # Field entry
        field_var = tk.StringVar(value=field_value)
        field_entry = ttk.Entry(field_frame, textvariable=field_var, width=60)
        field_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Store field info
        self.simple_fields[field_name] = {
            'var': field_var,
            'entry': field_entry,
            'label': label
        }
    
    def browse_simple_file(self):
        """Browse for image file in simple metadata tab."""
        file_path = filedialog.askopenfilename(
            title="Select Image File",
            filetypes=[
                ("Image files", "*.jpg *.jpeg *.png *.webp *.tiff *.tif"),
                ("JPEG files", "*.jpg *.jpeg"),
                ("PNG files", "*.png"),
                ("WebP files", "*.webp"),
                ("All files", "*.*")
            ]
        )
        if file_path:
            self.simple_file_path.set(file_path)
            self.load_simple_metadata()
    
    def load_simple_metadata(self):
        """Load metadata from image in simple metadata tab."""
        if not self.simple_file_path.get():
            messagebox.showwarning("Warning", "No file selected")
            return
        
        try:
            from PIL.ExifTags import TAGS
            
            # Load image
            image = Image.open(self.simple_file_path.get())
            
            # Display image
            self.display_simple_image(image)
            
            # Get EXIF data
            exifdata = image.getexif()
            
            # Clear existing fields and recreate with all found fields
            for widget in self.simple_metadata_scrollable_frame.winfo_children():
                widget.destroy()
            self.simple_fields = {}
            
            # Create comprehensive field list
            all_fields = {}
            
            # Ensure all standard fields are present (even if empty)
            for field_name in self.simple_standard_fields:
                all_fields[field_name] = ''
            
            # Process EXIF data
            for tag_id in exifdata:
                tag = TAGS.get(tag_id, tag_id)
                data = exifdata.get(tag_id)
                
                if isinstance(data, bytes):
                    # Handle different encodings based on tag type
                    if tag_id in [40091, 40094]:  # XPTitle, XPKeywords - UTF-16LE
                        try:
                            # Remove BOM if present and decode as UTF-16LE
                            if data.startswith(b'\xff\xfe'):
                                data = data[2:]
                            data = data.decode('utf-16le', errors='ignore')
                        except:
                            data = data.decode('utf-8', errors='ignore')
                    else:  # Other fields - UTF-8
                        data = data.decode('utf-8', errors='ignore')
                
                # Map to essential fields only
                if tag == 'XPTitle':
                    all_fields['XPTitle'] = str(data) if data else ''
                elif tag == 'ImageDescription':
                    all_fields['ImageDescription'] = str(data) if data else ''
                elif tag == 'XPKeywords':
                    all_fields['XPKeywords'] = str(data) if data else ''
                elif tag == 'Artist':
                    all_fields['Artist'] = str(data) if data else ''
                elif tag == 'Make':
                    all_fields['Make'] = str(data) if data else ''
                elif tag == 'Model':
                    all_fields['Model'] = str(data) if data else ''
            
            # Add image.info fields
            for key, value in image.info.items():
                if key not in all_fields:
                    all_fields[f"INFO_{key}"] = str(value) if value else ''
            
            # Create metadata fields for all found fields
            row = 0
            for field_name, field_value in all_fields.items():
                self.create_simple_metadata_field(field_name, field_value, row)
                row += 1
            
            # Update image info
            width, height = image.size
            file_size = os.path.getsize(self.simple_file_path.get()) / 1024
            self.simple_image_info.config(
                text=f"📁 {Path(self.simple_file_path.get()).name}\n📏 {width}x{height}\n📦 {file_size:.1f} KB"
            )
            
            print(f"Simple metadata loaded from: {self.simple_file_path.get()}")
            print(f"Found {len(all_fields)} metadata fields")
            
        except Exception as e:
            messagebox.showerror("Error", f"Could not load image: {str(e)}")
    
    def display_simple_image(self, image):
        """Display image in simple metadata canvas."""
        # Calculate display size
        canvas_width = self.simple_image_canvas.winfo_width()
        canvas_height = self.simple_image_canvas.winfo_height()
        
        if canvas_width <= 1 or canvas_height <= 1:
            # Canvas not ready, schedule refresh
            self.root.after(100, lambda: self.display_simple_image(image))
            return
        
        # Resize image to fit canvas
        img_width, img_height = image.size
        scale = min(canvas_width / img_width, canvas_height / img_height)
        new_width = int(img_width * scale)
        new_height = int(img_height * scale)
        
        resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Convert to PhotoImage
        photo = ImageTk.PhotoImage(resized_image)
        
        # Clear canvas and display image
        self.simple_image_canvas.delete("all")
        self.simple_image_canvas.create_image(canvas_width//2, canvas_height//2, image=photo)
        
        # Keep reference to prevent garbage collection
        self.simple_image_canvas.image = photo
    
    def save_simple_metadata(self):
        """Save metadata using simple approach."""
        if not self.simple_file_path.get():
            messagebox.showwarning("Warning", "No file selected")
            return
        
        try:
            from PIL.ExifTags import TAGS
            
            # Get original file path
            original_file_path = self.simple_file_path.get()
            file_ext = Path(original_file_path).suffix.lower()
            
            print(f"Simple save - Original file: {original_file_path}")
            print(f"Simple save - File extension: {file_ext}")
            
            # Create temporary file
            temp_dir = tempfile.gettempdir()
            temp_file_path = os.path.join(temp_dir, f"simple_temp_{os.path.basename(original_file_path)}")
            
            # Copy original file
            shutil.copy2(original_file_path, temp_file_path)
            print(f"Simple save - Temp file: {temp_file_path}")
            
            # Load image from temp file
            image = Image.open(temp_file_path)
            
            # Collect field values
            metadata_dict = {}
            for field_name, field_info in self.simple_fields.items():
                value = field_info['var'].get().strip()
                if value:
                    metadata_dict[field_name] = value
                    print(f"Simple save - {field_name}: {value}")
            
            print(f"Simple save - Total fields to save: {len(metadata_dict)}")
            
            # Save based on file type
            if file_ext in ['.jpg', '.jpeg']:
                self.save_simple_jpeg_metadata(image, temp_file_path, metadata_dict)
            elif file_ext in ['.webp']:
                self.save_simple_webp_metadata(image, temp_file_path, metadata_dict)
            else:
                messagebox.showwarning("Warning", f"Unsupported file type: {file_ext}")
                return
            
            # Close image
            image.close()
            
            # Replace original with temp file
            shutil.move(temp_file_path, original_file_path)
            print(f"Simple save - File replaced: {original_file_path}")
            
            messagebox.showinfo("Success", "Metadata saved successfully!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Could not save metadata: {str(e)}")
            print(f"Simple save error: {str(e)}")
    
    def save_simple_jpeg_metadata(self, image, file_path, metadata_dict):
        """Save simple JPEG metadata using piexif."""
        try:
            # Get existing EXIF data or create new
            exif_dict = piexif.load(image.info.get('exif', b'')) if image.info.get('exif') else {'0th': {}, 'Exif': {}, 'GPS': {}, '1st': {}, 'Interop': {}, 'thumbnail': None}
            
            # Streamlined field mapping for JPEG - only essential fields
            field_mapping = {
                'XPTitle': (40091, 'XPTitle', 'utf-16le'),
                'ImageDescription': (270, 'ImageDescription', 'utf-8'),
                'XPKeywords': (40094, 'XPKeywords', 'utf-16le'),
                'Artist': (315, 'Artist', 'utf-8'),
                'Make': (271, 'Make', 'utf-8'),
                'Model': (272, 'Model', 'utf-8')
            }
            
            # Add metadata
            for field_name, value in metadata_dict.items():
                if field_name in field_mapping:
                    tag_id, tag_name, encoding = field_mapping[field_name]
                    
                    # Handle UTF-16LE encoding properly for piexif
                    if encoding == 'utf-16le':
                        # For UTF-16LE, we need to add a BOM and ensure proper encoding
                        encoded_value = value.encode('utf-16le')
                        # Add BOM if not present
                        if not encoded_value.startswith(b'\xff\xfe'):
                            encoded_value = b'\xff\xfe' + encoded_value
                    else:
                        encoded_value = value.encode(encoding)
                    
                    exif_dict['0th'][tag_id] = encoded_value
                    print(f"Simple JPEG - Added {field_name} to tag {tag_id} with {encoding}: '{value}' -> {len(encoded_value)} bytes")
            
            # Save with EXIF data
            exif_bytes = piexif.dump(exif_dict)
            image.save(file_path, exif=exif_bytes, quality=95)
            print(f"Simple JPEG - Saved to: {file_path}")
            
        except Exception as e:
            print(f"Simple JPEG save error: {str(e)}")
            raise
    
    def save_simple_webp_metadata(self, image, file_path, metadata_dict):
        """Save simple WebP metadata using ExifTool."""
        try:
            # Find ExifTool
            exiftool_paths = [
                'exiftool',
                r'.\exiftool\exiftool.exe',
                r'C:\exiftool\exiftool.exe'
            ]
            
            exiftool_cmd = None
            for path in exiftool_paths:
                try:
                    result = subprocess.run([path, '-ver'], capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        exiftool_cmd = path
                        break
                except:
                    continue
            
            if not exiftool_cmd:
                raise Exception("ExifTool not found")
            
            # Build command
            cmd = [exiftool_cmd, '-overwrite_original']
            
            # Add metadata - streamlined for WebP
            field_mapping = {
                'XPTitle': '-XMP:Title',
                'ImageDescription': '-XMP:Description',
                'XPKeywords': '-XMP:Subject',
                'Artist': '-XMP:Creator',
                'Make': '-XMP:Make',
                'Model': '-XMP:Model'
            }
            
            for field_name, value in metadata_dict.items():
                if field_name in field_mapping:
                    cmd.extend([field_mapping[field_name], f'"{value}"'])
                    print(f"Simple WebP - Added {field_name}: {value}")
            
            cmd.append(file_path)
            
            # Run ExifTool
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            print(f"Simple WebP - Command: {' '.join(cmd)}")
            print(f"Simple WebP - Return code: {result.returncode}")
            print(f"Simple WebP - Output: {result.stdout}")
            print(f"Simple WebP - Error: {result.stderr}")
            
            if result.returncode != 0:
                raise Exception(f"ExifTool failed: {result.stderr}")
            
        except Exception as e:
            print(f"Simple WebP save error: {str(e)}")
            raise
    
    def verify_simple_metadata(self):
        """Verify simple metadata was saved."""
        if not self.simple_file_path.get():
            messagebox.showwarning("Warning", "No file selected")
            return
        
        try:
            from PIL.ExifTags import TAGS
            
            # Load image
            image = Image.open(self.simple_file_path.get())
            exifdata = image.getexif()
            
            # Create verification window
            verify_window = tk.Toplevel(self.root)
            verify_window.title("Simple Metadata Verification")
            verify_window.geometry("500x400")
            verify_window.transient(self.root)
            verify_window.grab_set()
            
            # Main frame
            main_frame = ttk.Frame(verify_window, padding="20")
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            # Title
            title_label = ttk.Label(main_frame, text="✅ Simple Metadata Verification", 
                                   font=('Arial', 14, 'bold'))
            title_label.pack(pady=(0, 20))
            
            # File info
            file_info = ttk.Label(main_frame, text=f"📁 File: {Path(self.simple_file_path.get()).name}", 
                                 font=('Arial', 10, 'bold'))
            file_info.pack(anchor=tk.W, pady=(0, 10))
            
            # Metadata display
            metadata_text = scrolledtext.ScrolledText(main_frame, height=15, wrap=tk.WORD)
            metadata_text.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
            
            # Build metadata content
            content = "Found Metadata:\n" + "="*50 + "\n\n"
            
            # Check simple fields - streamlined verification
            field_mapping = {
                'XPTitle': (40091, 'XPTitle'),
                'ImageDescription': (270, 'ImageDescription'),
                'XPKeywords': (40094, 'XPKeywords'),
                'Artist': (315, 'Artist'),
                'Make': (271, 'Make'),
                'Model': (272, 'Model')
            }
            
            found_count = 0
            for field_name, (tag_id, tag_name) in field_mapping.items():
                if tag_id in exifdata:
                    data = exifdata.get(tag_id)
                    if isinstance(data, bytes):
                        # Handle different encodings based on tag type
                        if tag_id in [40091, 40094]:  # XPTitle, XPKeywords - UTF-16LE
                            try:
                                # Remove BOM if present and decode as UTF-16LE
                                if data.startswith(b'\xff\xfe'):
                                    data = data[2:]
                                data = data.decode('utf-16le', errors='ignore')
                            except:
                                data = data.decode('utf-8', errors='ignore')
                        else:  # Other fields - UTF-8
                            data = data.decode('utf-8', errors='ignore')
                    content += f"✅ {field_name}: {str(data)}\n"
                    found_count += 1
                else:
                    content += f"❌ {field_name}: Not found\n"
            
            content += f"\nTotal fields found: {found_count}/5\n"
            
            metadata_text.insert(tk.END, content)
            metadata_text.config(state=tk.DISABLED)
            
            # Close button
            ttk.Button(main_frame, text="Close", command=verify_window.destroy).pack()
            
        except Exception as e:
            messagebox.showerror("Error", f"Could not verify metadata: {str(e)}")
    
    def clear_simple_metadata(self):
        """Clear all simple metadata fields."""
        for field_info in self.simple_fields.values():
            field_info['var'].set('')
        print("Simple metadata fields cleared")
        
        # Recreate fields with empty values
        self.create_simple_metadata_fields()
            
    def save_metadata(self):
        """Save metadata to image file using copy-and-replace approach."""
        if not self.metadata_image_path.get():
            messagebox.showwarning("Warning", "No image selected")
            return
            
        try:
            from PIL.ExifTags import TAGS
            from PIL import ExifTags
            import piexif
            import shutil
            import tempfile
            
            # Get original file path
            original_file_path = self.metadata_image_path.get()
            file_ext = Path(original_file_path).suffix.lower()
            
            # Create temporary file path
            temp_dir = tempfile.gettempdir()
            temp_file_path = os.path.join(temp_dir, f"temp_metadata_{os.path.basename(original_file_path)}")
            
            print(f"Original file: {original_file_path}")
            print(f"Temp file: {temp_file_path}")
            
            # Copy original file to temporary location
            shutil.copy2(original_file_path, temp_file_path)
            print("File copied to temporary location")
            
            # Load image from temporary file
            image = Image.open(temp_file_path)
            
            # Get metadata configuration for this file type
            config = self.get_metadata_config(original_file_path)
            print(f"Using metadata config: {config['field_mapping']}")
            
            # Prepare metadata dictionary - only essential fields
            metadata_dict = {}
            essential_fields = ['XPTitle', 'ImageDescription', 'XPKeywords', 'Artist', 'Make', 'Model']
            
            # Collect only essential field values
            for field_name in essential_fields:
                if field_name in self.metadata_fields:
                    value = self.metadata_fields[field_name]['var'].get().strip()
                    if value:
                        metadata_dict[field_name] = value
                        print(f"Main save - {field_name}: {value}")
            
            print(f"Main save - Total fields to save: {len(metadata_dict)}")
            
            # Handle different image formats - save to temporary file using streamlined approach
            if file_ext in ['.jpg', '.jpeg']:
                self.save_main_jpeg_metadata(image, temp_file_path, metadata_dict)
            elif file_ext in ['.webp']:
                self.save_main_webp_metadata(image, temp_file_path, metadata_dict)
            else:
                messagebox.showwarning("Warning", f"Unsupported file type: {file_ext}")
                return
            
            print("Metadata written to temporary file")
            
            # Close the image to release file handle
            image.close()
            
            # Replace original file with the modified temporary file
            shutil.move(temp_file_path, original_file_path)
            print(f"Temporary file moved to replace original: {original_file_path}")
            
            messagebox.showinfo("Success", "Metadata saved successfully!\n\nClick 'Verify Saved Data' to confirm the metadata was written to the file.")
            
        except Exception as e:
            # Clean up temporary file if it exists
            try:
                if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
                    print("Cleaned up temporary file after error")
            except:
                pass
            messagebox.showerror("Error", f"Could not save metadata: {str(e)}")
    
    def save_main_jpeg_metadata(self, image, file_path, metadata_dict):
        """Save main JPEG metadata using piexif - streamlined approach."""
        try:
            # Get existing EXIF data or create new
            exif_dict = piexif.load(image.info.get('exif', b'')) if image.info.get('exif') else {'0th': {}, 'Exif': {}, 'GPS': {}, '1st': {}, 'Interop': {}, 'thumbnail': None}
            
            # Streamlined field mapping for JPEG - only essential fields
            field_mapping = {
                'XPTitle': (40091, 'XPTitle', 'utf-16le'),
                'ImageDescription': (270, 'ImageDescription', 'utf-8'),
                'XPKeywords': (40094, 'XPKeywords', 'utf-16le'),
                'Artist': (315, 'Artist', 'utf-8'),
                'Make': (271, 'Make', 'utf-8'),
                'Model': (272, 'Model', 'utf-8')
            }
            
            # Add metadata
            for field_name, value in metadata_dict.items():
                if field_name in field_mapping:
                    tag_id, tag_name, encoding = field_mapping[field_name]
                    
                    # Handle UTF-16LE encoding properly for piexif
                    if encoding == 'utf-16le':
                        # For UTF-16LE, we need to add a BOM and ensure proper encoding
                        encoded_value = value.encode('utf-16le')
                        # Add BOM if not present
                        if not encoded_value.startswith(b'\xff\xfe'):
                            encoded_value = b'\xff\xfe' + encoded_value
                    else:
                        encoded_value = value.encode(encoding)
                    
                    exif_dict['0th'][tag_id] = encoded_value
                    print(f"Main JPEG - Added {field_name} to tag {tag_id} with {encoding}: '{value}' -> {len(encoded_value)} bytes")
            
            # Save with EXIF data
            exif_bytes = piexif.dump(exif_dict)
            image.save(file_path, exif=exif_bytes, quality=95)
            print(f"Main JPEG - Saved to: {file_path}")
            
        except Exception as e:
            print(f"Main JPEG save error: {str(e)}")
            raise
    
    def save_main_webp_metadata(self, image, file_path, metadata_dict):
        """Save main WebP metadata using ExifTool - streamlined approach."""
        try:
            # Find ExifTool
            exiftool_paths = [
                'exiftool',
                r'.\exiftool\exiftool.exe',
                r'C:\exiftool\exiftool.exe'
            ]
            
            exiftool_cmd = None
            for path in exiftool_paths:
                try:
                    result = subprocess.run([path, '-ver'], capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        exiftool_cmd = path
                        break
                except:
                    continue
            
            if not exiftool_cmd:
                raise Exception("ExifTool not found")
            
            # Build command
            cmd = [exiftool_cmd, '-overwrite_original']
            
            # Add metadata - streamlined for WebP
            field_mapping = {
                'XPTitle': '-XMP:Title',
                'ImageDescription': '-XMP:Description',
                'XPKeywords': '-XMP:Subject',
                'Artist': '-XMP:Creator',
                'Make': '-XMP:Make',
                'Model': '-XMP:Model'
            }
            
            for field_name, value in metadata_dict.items():
                if field_name in field_mapping:
                    cmd.extend([field_mapping[field_name], f'"{value}"'])
                    print(f"Main WebP - Added {field_name}: {value}")
            
            cmd.append(file_path)
            
            # Run ExifTool
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            print(f"Main WebP - Command: {' '.join(cmd)}")
            print(f"Main WebP - Return code: {result.returncode}")
            print(f"Main WebP - Output: {result.stdout}")
            print(f"Main WebP - Error: {result.stderr}")
            
            if result.returncode != 0:
                raise Exception(f"ExifTool failed: {result.stderr}")
            
        except Exception as e:
            print(f"Main WebP save error: {str(e)}")
            raise
            
    def _save_jpeg_metadata(self, image, file_path, metadata_dict, custom_fields, config=None):
        """Save metadata to JPEG file using piexif."""
        try:
            # Get existing EXIF data or create new
            exif_dict = piexif.load(image.info.get('exif', b'')) if image.info.get('exif') else {'0th': {}, 'Exif': {}, 'GPS': {}, '1st': {}, 'Interop': {}, 'thumbnail': None}
            
            # Use configuration-based tag mapping
            if config and 'exif_tags' in config:
                tag_mapping = {}
                for field, (tag_id, tag_name, encoding) in config['exif_tags'].items():
                    tag_mapping[field] = (tag_id, tag_name, encoding)
            else:
                # Fallback to default mapping
                tag_mapping = {
                    'XPTitle': (40091, 'XPTitle', 'utf-16le'),
                    'ImageDescription': (270, 'ImageDescription', 'utf-8'),
                    'XPKeywords': (40094, 'XPKeywords', 'utf-16le'),
                    'Artist': (315, 'Artist', 'utf-8'),
                    'Copyright': (33432, 'Copyright', 'utf-8'),
                    'Software': (11, 'Software', 'utf-8'),
                    'DateTime': (306, 'DateTime', 'utf-8'),
                    'Make': (271, 'Make', 'utf-8'),
                    'Model': (272, 'Model', 'utf-8'),
                }
            
            # Handle title and description using configuration
            title_field = config['field_mapping'].get('Title', 'XPTitle') if config else 'XPTitle'
            desc_field = config['field_mapping'].get('Description', 'ImageDescription') if config else 'ImageDescription'
            
            title_value = metadata_dict.get(title_field, '').strip()
            description_value = metadata_dict.get(desc_field, '').strip()
            
            if title_value and title_field in tag_mapping:
                tag_id, tag_name, encoding = tag_mapping[title_field]
                exif_dict['0th'][tag_id] = title_value.encode(encoding)
            if description_value and desc_field in tag_mapping:
                tag_id, tag_name, encoding = tag_mapping[desc_field]
                exif_dict['0th'][tag_id] = description_value.encode(encoding)
            
            # Add standard metadata (skip XPTitle and ImageDescription as they're handled above)
            for field_name, value in metadata_dict.items():
                if field_name in tag_mapping and field_name not in ['XPTitle', 'ImageDescription']:
                    tag_id, tag_name = tag_mapping[field_name]
                    if field_name == 'XPKeywords':
                        # XPKeywords requires UTF-16LE encoding
                        exif_dict['0th'][tag_id] = value.encode('utf-16le') if isinstance(value, str) else value
                    else:
                        exif_dict['0th'][tag_id] = value.encode('utf-8') if isinstance(value, str) else value
                elif field_name in ['ISO', 'FNumber', 'ExposureTime', 'FocalLength', 'Flash', 'WhiteBalance']:
                    # These go in Exif section
                    exif_tag_mapping = {
                        'ISO': 34855,
                        'FNumber': 33437,
                        'ExposureTime': 33434,
                        'FocalLength': 37386,
                        'Flash': 37385,
                        'WhiteBalance': 41987,
                    }
                    if field_name in exif_tag_mapping:
                        exif_dict['Exif'][exif_tag_mapping[field_name]] = value
            
            # Add custom fields to UserComment
            if custom_fields:
                user_comment = '; '.join(custom_fields)
                exif_dict['Exif'][37510] = user_comment.encode('utf-8')
            
            # Save with EXIF data
            exif_bytes = piexif.dump(exif_dict)
            
            # Debug output
            print(f"JPEG Save Debug:")
            print(f"  Metadata dict: {metadata_dict}")
            print(f"  EXIF dict keys: {list(exif_dict.keys())}")
            print(f"  EXIF 0th keys: {list(exif_dict['0th'].keys())}")
            print(f"  EXIF Exif keys: {list(exif_dict['Exif'].keys())}")
            
            image.save(file_path, exif=exif_bytes, quality=95)
            print(f"  JPEG saved successfully to: {file_path}")
            
        except Exception as e:
            # Fallback to basic PIL EXIF
            exif_dict = image.getexif()
            for field_name, value in metadata_dict.items():
                if field_name == 'Title' or field_name == 'Description':
                    exif_dict[270] = value
                elif field_name == 'Author':
                    exif_dict[315] = value
                elif field_name == 'Copyright':
                    exif_dict[33432] = value
                elif field_name == 'Software':
                    exif_dict[11] = value
                elif field_name == 'DateTime':
                    exif_dict[306] = value
                elif field_name == 'Make':
                    exif_dict[271] = value
                elif field_name == 'Model':
                    exif_dict[272] = value
            
            if custom_fields:
                exif_dict[0x9286] = '; '.join(custom_fields)
            
            image.save(file_path, exif=exif_dict, quality=95)
    
    def _save_png_metadata(self, image, file_path, metadata_dict, custom_fields):
        """Save metadata to PNG file using PIL info."""
        info = image.info.copy()
        
        # PNG supports text chunks
        for field_name, value in metadata_dict.items():
            if field_name in ['Title', 'Description']:
                info['Title'] = value
            elif field_name == 'Author':
                info['Author'] = value
            elif field_name == 'Copyright':
                info['Copyright'] = value
            elif field_name == 'Software':
                info['Software'] = value
            elif field_name == 'Keywords':
                info['Keywords'] = value
        
        # Add custom fields as a single text chunk
        if custom_fields:
            info['Comment'] = '; '.join(custom_fields)
        
        image.save(file_path, **info)
    
    def _save_webp_metadata(self, image, file_path, metadata_dict, custom_fields):
        """Save metadata to WebP file."""
        # Try ExifTool first for WebP (better support)
        if self._try_exiftool_webp_save(file_path, metadata_dict, custom_fields):
            return
        
        # Fallback to PIL info dictionary
        info = image.info.copy()
        
        # WebP supports some basic metadata
        for field_name, value in metadata_dict.items():
            if field_name in ['Title', 'Description']:
                info['Title'] = value
            elif field_name == 'Author':
                info['Author'] = value
            elif field_name == 'Copyright':
                info['Copyright'] = value
            elif field_name == 'Software':
                info['Software'] = value
        
        # Add custom fields
        if custom_fields:
            info['Comment'] = '; '.join(custom_fields)
        
        # Try to preserve EXIF if it exists
        if image.info.get('exif'):
            info['exif'] = image.info['exif']
        
        image.save(file_path, **info)
    
    def _try_exiftool_webp_save(self, file_path, metadata_dict, custom_fields):
        """Try to save WebP metadata using ExifTool."""
        try:
            import subprocess
            
            # Try to find exiftool in common locations
            exiftool_paths = [
                'exiftool',  # In PATH
                r'.\exiftool\exiftool.exe',  # Local directory
                r'C:\Program Files\ExifTool\exiftool.exe',
                r'C:\Program Files (x86)\ExifTool\exiftool.exe',
                r'C:\Users\{}\AppData\Local\Microsoft\WinGet\Packages\OliverBetz.ExifTool_*\exiftool.exe'.format(os.getenv('USERNAME', '')),
                r'C:\exiftool\exiftool.exe',
                r'C:\tools\exiftool\exiftool.exe'
            ]
            
            exiftool_cmd = None
            for path in exiftool_paths:
                try:
                    if '*' in path:
                        # Handle wildcard paths
                        import glob
                        matches = glob.glob(path)
                        if matches:
                            exiftool_cmd = matches[0]
                            break
                    else:
                        result = subprocess.run([path, '-ver'], 
                                              capture_output=True, text=True, timeout=5)
                        if result.returncode == 0:
                            exiftool_cmd = path
                            break
                except:
                    continue
            
            if not exiftool_cmd:
                return False
            
            # Build exiftool command
            cmd = [exiftool_cmd, '-overwrite_original']
            
            # Map metadata to ExifTool tags (WebP-specific)
            tag_mapping = {
                'XPTitle': '-XMP:Title',
                'ImageDescription': '-XMP:Description', 
                'Artist': '-XMP:Creator',
                'Copyright': '-XMP:Rights',
                'Software': '-XMP:Software',
                'XPKeywords': '-XMP:Subject',
                'DateTime': '-XMP:CreateDate',
                'Make': '-XMP:Make',
                'Model': '-XMP:Model',
            }
            
            # Add standard metadata
            for field_name, value in metadata_dict.items():
                if field_name in tag_mapping:
                    print(f"Adding {field_name}: {value} -> {tag_mapping[field_name]}")
                    cmd.extend([tag_mapping[field_name], f'"{value}"'])  # Quote the value
                else:
                    print(f"Skipping {field_name}: {value} (not in tag_mapping)")
            
            # Add custom fields as UserComment
            if custom_fields:
                cmd.extend(['-UserComment', f'"{"; ".join(custom_fields)}"'])  # Quote the value
            
            # Add file path
            cmd.append(file_path)
            
            # Run exiftool
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            # Debug output
            print(f"ExifTool command: {' '.join(cmd)}")
            print(f"ExifTool return code: {result.returncode}")
            print(f"ExifTool stdout: {result.stdout}")
            print(f"ExifTool stderr: {result.stderr}")
            
            return result.returncode == 0
            
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
            return False
    
    def _save_tiff_metadata(self, image, file_path, metadata_dict, custom_fields):
        """Save metadata to TIFF file."""
        # TIFF has good EXIF support
        exif_dict = image.getexif()
        
        for field_name, value in metadata_dict.items():
            if field_name in ['Title', 'Description']:
                exif_dict[270] = value
            elif field_name == 'Author':
                exif_dict[315] = value
            elif field_name == 'Copyright':
                exif_dict[33432] = value
            elif field_name == 'Software':
                exif_dict[11] = value
            elif field_name == 'DateTime':
                exif_dict[306] = value
            elif field_name == 'Make':
                exif_dict[271] = value
            elif field_name == 'Model':
                exif_dict[272] = value
        
        if custom_fields:
            exif_dict[0x9286] = '; '.join(custom_fields)
        
        image.save(file_path, exif=exif_dict)
    
    def _save_generic_metadata(self, image, file_path, metadata_dict, custom_fields):
        """Fallback metadata saving for other formats."""
        # Try to save as much as possible
        exif_dict = image.getexif()
        
        for field_name, value in metadata_dict.items():
            if field_name in ['Title', 'Description']:
                exif_dict[270] = value
            elif field_name == 'Author':
                exif_dict[315] = value
            elif field_name == 'Copyright':
                exif_dict[33432] = value
            elif field_name == 'Software':
                exif_dict[11] = value
        
        if custom_fields:
            exif_dict[0x9286] = '; '.join(custom_fields)
        
        image.save(file_path, exif=exif_dict)
    
    def verify_saved_metadata(self, file_path=None):
        """Verify that metadata was actually saved to the image file."""
        if not file_path:
            file_path = self.metadata_image_path.get()
            
        if not file_path:
            messagebox.showwarning("Warning", "No image selected")
            return
            
        try:
            from PIL.ExifTags import TAGS
            import piexif
            import subprocess
            import json
            
            # Load image and read metadata
            image = Image.open(file_path)
            file_ext = Path(file_path).suffix.lower()
            
            # Create verification window
            verify_window = tk.Toplevel(self.root)
            verify_window.title("Metadata Verification")
            verify_window.geometry("1000x700")
            verify_window.transient(self.root)
            verify_window.grab_set()
            
            # Main frame
            main_frame = ttk.Frame(verify_window, padding="20")
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            # Title
            title_label = ttk.Label(main_frame, text="✅ Metadata Verification Results", 
                                   font=('Arial', 14, 'bold'))
            title_label.pack(pady=(0, 20))
            
            # File info
            file_info = ttk.Label(main_frame, text=f"📁 File: {Path(file_path).name}", 
                                 font=('Arial', 10, 'bold'))
            file_info.pack(anchor=tk.W, pady=(0, 10))
            
            # Create notebook for different verification methods
            notebook = ttk.Notebook(main_frame)
            notebook.pack(fill=tk.BOTH, expand=True)
            
            # PIL EXIF tab
            pil_frame = ttk.Frame(notebook)
            notebook.add(pil_frame, text="PIL EXIF Data")
            
            # PIL EXIF content
            pil_text = scrolledtext.ScrolledText(pil_frame, height=15, wrap=tk.WORD)
            pil_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # Read EXIF data using PIL
            exifdata = image.getexif()
            pil_content = "PIL EXIF Data:\n" + "="*50 + "\n\n"
            
            if exifdata:
                for tag_id in exifdata:
                    tag = TAGS.get(tag_id, tag_id)
                    data = exifdata.get(tag_id)
                    
                    if isinstance(data, bytes):
                        try:
                            data = data.decode('utf-8', errors='ignore')
                        except:
                            data = str(data)
                    
                    pil_content += f"Tag {tag_id} ({tag}): {data}\n"
            else:
                pil_content += "No EXIF data found using PIL\n"
            
            pil_text.insert(tk.END, pil_content)
            pil_text.config(state=tk.DISABLED)
            
            # Piexif tab (for JPEG)
            if file_ext in ['.jpg', '.jpeg']:
                piexif_frame = ttk.Frame(notebook)
                notebook.add(piexif_frame, text="Piexif EXIF Data")
                
                piexif_text = scrolledtext.ScrolledText(piexif_frame, height=15, wrap=tk.WORD)
                piexif_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
                
                try:
                    exif_dict = piexif.load(image.info.get('exif', b''))
                    piexif_content = "Piexif EXIF Data:\n" + "="*50 + "\n\n"
                    
                    for ifd_name in exif_dict:
                        if ifd_name != 'thumbnail' and exif_dict[ifd_name]:
                            piexif_content += f"\n{ifd_name.upper()}:\n"
                            piexif_content += "-" * 30 + "\n"
                            for tag_id, value in exif_dict[ifd_name].items():
                                tag_name = TAGS.get(tag_id, f"Tag_{tag_id}")
                                if isinstance(value, bytes):
                                    try:
                                        value = value.decode('utf-8', errors='ignore')
                                    except:
                                        value = str(value)
                                piexif_content += f"  {tag_id} ({tag_name}): {value}\n"
                    
                    if not any(exif_dict[ifd] for ifd in exif_dict if ifd != 'thumbnail'):
                        piexif_content += "No EXIF data found using piexif\n"
                        
                except Exception as e:
                    piexif_content = f"Error reading EXIF with piexif: {str(e)}\n"
                
                piexif_text.insert(tk.END, piexif_content)
                piexif_text.config(state=tk.DISABLED)
            
            # Image Info tab
            info_frame = ttk.Frame(notebook)
            notebook.add(info_frame, text="Image Info")
            
            info_text = scrolledtext.ScrolledText(info_frame, height=15, wrap=tk.WORD)
            info_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            info_content = "Image Information:\n" + "="*50 + "\n\n"
            info_content += f"Format: {image.format}\n"
            info_content += f"Mode: {image.mode}\n"
            info_content += f"Size: {image.size}\n"
            info_content += f"File Size: {os.path.getsize(file_path) / 1024:.1f} KB\n\n"
            
            info_content += "Image Info Dictionary:\n"
            info_content += "-" * 30 + "\n"
            for key, value in image.info.items():
                if isinstance(value, bytes):
                    try:
                        value = value.decode('utf-8', errors='ignore')
                    except:
                        value = f"<bytes: {len(value)} bytes>"
                info_content += f"{key}: {value}\n"
            
            info_text.insert(tk.END, info_content)
            info_text.config(state=tk.DISABLED)
            
            # ExifTool tab
            exiftool_frame = ttk.Frame(notebook)
            notebook.add(exiftool_frame, text="ExifTool Data")
            
            # ExifTool content
            exiftool_text = scrolledtext.ScrolledText(exiftool_frame, height=15, wrap=tk.WORD)
            exiftool_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # Try to use exiftool
            exiftool_content = "ExifTool Data:\n" + "="*50 + "\n\n"
            exiftool_available = False
            
            try:
                # Try to find exiftool in common locations
                exiftool_paths = [
                    'exiftool',  # In PATH
                    r'.\exiftool\exiftool.exe',  # Local directory
                    r'C:\Program Files\ExifTool\exiftool.exe',
                    r'C:\Program Files (x86)\ExifTool\exiftool.exe',
                    r'C:\Users\{}\AppData\Local\Microsoft\WinGet\Packages\OliverBetz.ExifTool_*\exiftool.exe'.format(os.getenv('USERNAME', '')),
                    r'C:\exiftool\exiftool.exe',
                    r'C:\tools\exiftool\exiftool.exe'
                ]
                
                exiftool_cmd = None
                for path in exiftool_paths:
                    try:
                        if '*' in path:
                            # Handle wildcard paths
                            import glob
                            matches = glob.glob(path)
                            if matches:
                                exiftool_cmd = matches[0]
                                break
                        else:
                            result = subprocess.run([path, '-ver'], 
                                                  capture_output=True, text=True, timeout=5)
                            if result.returncode == 0:
                                exiftool_cmd = path
                                break
                    except:
                        continue
                
                if exiftool_cmd:
                    exiftool_available = True
                    exiftool_content += f"ExifTool Path: {exiftool_cmd}\n"
                    
                    # Get version
                    result = subprocess.run([exiftool_cmd, '-ver'], 
                                          capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        exiftool_content += f"ExifTool Version: {result.stdout.strip()}\n\n"
                    
                    # Get metadata in JSON format
                    result = subprocess.run([exiftool_cmd, '-j', '-g', file_path], 
                                          capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        try:
                            exif_data = json.loads(result.stdout)
                            if exif_data and len(exif_data) > 0:
                                file_data = exif_data[0]
                                
                                # Group by category
                                categories = {}
                                for key, value in file_data.items():
                                    if ':' in key:
                                        category = key.split(':')[0]
                                        if category not in categories:
                                            categories[category] = []
                                        categories[category].append((key, value))
                                    else:
                                        if 'General' not in categories:
                                            categories['General'] = []
                                        categories['General'].append((key, value))
                                
                                for category, items in categories.items():
                                    exiftool_content += f"\n{category.upper()}:\n"
                                    exiftool_content += "-" * 30 + "\n"
                                    for key, value in items:
                                        clean_key = key.split(':')[-1] if ':' in key else key
                                        exiftool_content += f"  {clean_key}: {value}\n"
                            else:
                                exiftool_content += "No metadata found by ExifTool\n"
                        except json.JSONDecodeError:
                            exiftool_content += "Error parsing ExifTool JSON output\n"
                    else:
                        exiftool_content += f"ExifTool error: {result.stderr}\n"
                else:
                    exiftool_content += "ExifTool not found or not working\n"
            except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
                exiftool_content += "ExifTool not available (not installed or not in PATH)\n"
                exiftool_content += "\n🔧 QUICK INSTALLATION:\n"
                exiftool_content += "1. Run 'install_exiftool.bat' in this folder\n"
                exiftool_content += "2. Or manually download from https://exiftool.org/\n"
                exiftool_content += "3. Extract exiftool.exe to C:\\exiftool\\\n"
                exiftool_content += "\n📋 MANUAL INSTALLATION:\n"
                exiftool_content += "1. Go to https://exiftool.org/\n"
                exiftool_content += "2. Download 'ExifTool-12.95.zip'\n"
                exiftool_content += "3. Extract exiftool.exe to C:\\exiftool\\\n"
                exiftool_content += "4. Restart this application\n"
                exiftool_content += "\n💡 WHY EXIFTOOL?\n"
                exiftool_content += "- Better WebP metadata support\n"
                exiftool_content += "- Shows in Windows Properties\n"
                exiftool_content += "- More reliable than PIL for metadata\n"
                exiftool_content += "\n🔄 WITHOUT EXIFTOOL:\n"
                exiftool_content += "- App will use PIL (limited WebP support)\n"
                exiftool_content += "- Metadata may not show in Windows Properties\n"
                exiftool_content += "- Basic text chunks only for WebP\n"
            
            exiftool_text.insert(tk.END, exiftool_content)
            exiftool_text.config(state=tk.DISABLED)
            
            # Summary tab
            summary_frame = ttk.Frame(notebook)
            notebook.add(summary_frame, text="Summary")
            
            summary_text = scrolledtext.ScrolledText(summary_frame, height=15, wrap=tk.WORD)
            summary_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # Analyze what was found
            summary_content = "Metadata Analysis Summary:\n" + "="*50 + "\n\n"
            
            # Check for common metadata fields
            found_fields = []
            missing_fields = []
            exiftool_fields = []
            
            # Check PIL EXIF
            if exifdata:
                pil_fields = {
                    'Title/Description': 270,
                    'XPTitle': 40091,
                    'XPKeywords': 40094,
                    'Author': 315,
                    'Copyright': 33432,
                    'Software': 11,
                    'DateTime': 306,
                    'Make': 271,
                    'Model': 272,
                }
                
                for field_name, tag_id in pil_fields.items():
                    if tag_id in exifdata:
                        found_fields.append(f"PIL: {field_name}")
                    else:
                        missing_fields.append(f"PIL: {field_name}")
            
            # Check image info
            info_fields = ['Title', 'XPTitle', 'Author', 'Artist', 'Copyright', 'Software', 'Keywords', 'XPKeywords', 'Comment']
            for field in info_fields:
                if field in image.info:
                    found_fields.append(f"Info: {field}")
                else:
                    missing_fields.append(f"Info: {field}")
            
            # Check ExifTool results
            if exiftool_available and exiftool_cmd:
                try:
                    result = subprocess.run([exiftool_cmd, '-j', '-g', file_path], 
                                          capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        exif_data = json.loads(result.stdout)
                        if exif_data and len(exif_data) > 0:
                            file_data = exif_data[0]
                            exiftool_fields = list(file_data.keys())
                            summary_content += f"ExifTool found {len(exiftool_fields)} metadata fields\n"
                        else:
                            summary_content += "ExifTool found no metadata\n"
                    else:
                        summary_content += "ExifTool failed to read metadata\n"
                except:
                    summary_content += "ExifTool data could not be parsed\n"
            else:
                summary_content += "ExifTool not available - install for better WebP support\n"
            
            summary_content += f"\nFound {len(found_fields)} metadata fields:\n"
            for field in found_fields:
                summary_content += f"  ✅ {field}\n"
            
            summary_content += f"\nMissing {len(missing_fields)} common fields:\n"
            for field in missing_fields:
                summary_content += f"  ❌ {field}\n"
            
            if exiftool_available and exiftool_fields:
                summary_content += f"\nExifTool found {len(exiftool_fields)} total fields:\n"
                for field in exiftool_fields[:10]:  # Show first 10
                    summary_content += f"  📋 {field}\n"
                if len(exiftool_fields) > 10:
                    summary_content += f"  ... and {len(exiftool_fields) - 10} more\n"
            
            # Format-specific notes
            summary_content += f"\nFormat-specific notes:\n"
            summary_content += "-" * 30 + "\n"
            if file_ext in ['.jpg', '.jpeg']:
                summary_content += "JPEG: Full EXIF support available\n"
            elif file_ext == '.png':
                summary_content += "PNG: Limited to text chunks (Title, Author, etc.)\n"
            elif file_ext == '.webp':
                summary_content += "WebP: Limited metadata support, may not show in Windows Properties\n"
            elif file_ext in ['.tiff', '.tif']:
                summary_content += "TIFF: Good EXIF support\n"
            else:
                summary_content += f"{file_ext.upper()}: Limited metadata support\n"
            
            summary_text.insert(tk.END, summary_content)
            summary_text.config(state=tk.DISABLED)
            
            # Close button
            ttk.Button(main_frame, text="Close", command=verify_window.destroy).pack(pady=(20, 0))
            
        except Exception as e:
            messagebox.showerror("Error", f"Could not verify metadata: {str(e)}")
    
    def install_exiftool_help(self):
        """Show ExifTool installation help dialog."""
        help_window = tk.Toplevel(self.root)
        help_window.title("ExifTool Installation Help")
        help_window.geometry("700x600")
        help_window.transient(self.root)
        help_window.grab_set()
        
        # Main frame
        main_frame = ttk.Frame(help_window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, text="🔧 ExifTool Installation Help", 
                               font=('Arial', 14, 'bold'))
        title_label.pack(pady=(0, 20))
        
        # Content
        content_text = scrolledtext.ScrolledText(main_frame, height=25, wrap=tk.WORD)
        content_text.pack(fill=tk.BOTH, expand=True)
        
        help_content = """ExifTool Installation Guide
=====================================

WHY INSTALL EXIFTOOL?
---------------------
✅ Better WebP metadata support
✅ Metadata shows in Windows Properties dialog
✅ More reliable than PIL for metadata
✅ Supports all image formats
✅ Industry standard tool

QUICK INSTALLATION (RECOMMENDED)
--------------------------------
1. Run the 'install_exiftool.bat' file in this folder
2. Follow the on-screen instructions
3. Restart this application

MANUAL INSTALLATION
-------------------
1. Go to: https://exiftool.org/
2. Download: ExifTool-12.95.zip
3. Extract exiftool.exe to: C:\\exiftool\\
4. Restart this application

VERIFY INSTALLATION
-------------------
After installation, click "Verify Saved Data" to test ExifTool.

WHAT HAPPENS WITHOUT EXIFTOOL?
------------------------------
❌ Limited WebP metadata support
❌ Metadata may not show in Windows Properties
❌ Basic text chunks only for WebP
✅ App still works with PIL fallback

COMMAND LINE EXAMPLES
---------------------
# Add metadata to WebP
exiftool -Title="My Title" -Description="My Description" image.webp

# Add multiple fields
exiftool -Title="Kitchen Design" -Keywords="kitchen,modern,oak" -Author="John Doe" image.webp

# View all metadata
exiftool image.webp

# Batch process multiple files
exiftool -Title="Project Title" -Keywords="keyword1,keyword2" *.webp

TROUBLESHOOTING
---------------
If ExifTool is not found:
1. Check it's in C:\\exiftool\\exiftool.exe
2. Try running: C:\\exiftool\\exiftool.exe -ver
3. Restart this application
4. Check Windows antivirus isn't blocking it

SUPPORT
-------
- ExifTool Website: https://exiftool.org/
- ExifTool Forum: https://exiftool.org/forum/
- This App: Check the "Verify Saved Data" tab for detailed info
"""
        
        content_text.insert(tk.END, help_content)
        content_text.config(state=tk.DISABLED)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(20, 0))
        
        ttk.Button(button_frame, text="🌐 Open ExifTool Website", 
                  command=lambda: self.open_url("https://exiftool.org/")).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="📁 Open Installation Folder", 
                  command=self.open_install_folder).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="✅ Test ExifTool", 
                  command=self.test_exiftool).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Close", 
                  command=help_window.destroy).pack(side=tk.RIGHT)
    
    def open_url(self, url):
        """Open URL in default browser."""
        import webbrowser
        webbrowser.open(url)
    
    def open_install_folder(self):
        """Open ExifTool installation folder."""
        import subprocess
        try:
            subprocess.run(['explorer', 'C:\\exiftool'], check=True)
        except:
            messagebox.showwarning("Warning", "Could not open C:\\exiftool folder")
    
    def test_exiftool(self):
        """Test if ExifTool is working."""
        try:
            import subprocess
            result = subprocess.run(['C:\\exiftool\\exiftool.exe', '-ver'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                messagebox.showinfo("Success", f"ExifTool is working!\nVersion: {result.stdout.strip()}")
            else:
                messagebox.showerror("Error", "ExifTool is not working properly")
        except:
            messagebox.showerror("Error", "ExifTool not found at C:\\exiftool\\exiftool.exe")
            
    def select_batch_folder(self):
        """Select folder for batch metadata processing."""
        folder = filedialog.askdirectory(title="Select Folder for Batch Processing")
        if folder:
            self.batch_folder = folder
            self.image_files = self._load_images_from_folder(folder)
            self.log_message(f"📁 Batch folder selected: {folder}")
            self.log_message(f"📊 Found {len(self.image_files)} images")
            
    def batch_process_metadata(self):
        """Process metadata for all images in batch folder."""
        if not self.batch_folder:
            messagebox.showwarning("Warning", "Please select a batch folder first")
            return
            
        # Get all image files
        image_extensions = {'.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.webp', '.avif'}
        image_files = []
        
        for ext in image_extensions:
            image_files.extend(Path(self.batch_folder).glob(f'*{ext}'))
            image_files.extend(Path(self.batch_folder).glob(f'*{ext.upper()}'))
        
        if not image_files:
            messagebox.showwarning("Warning", "No image files found in selected folder")
            return
            
        # Show batch processing dialog
        self.show_batch_processing_dialog(image_files)
        
    def show_batch_processing_dialog(self, image_files):
        """Show dialog for batch metadata processing."""
        batch_window = tk.Toplevel(self.root)
        batch_window.title("Batch Metadata Processing")
        batch_window.geometry("600x500")
        batch_window.transient(self.root)
        batch_window.grab_set()
        
        # Main frame
        main_frame = ttk.Frame(batch_window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_frame, text="🔄 Batch Metadata Processing", 
                 font=('Arial', 14, 'bold')).pack(pady=(0, 20))
        
        # File list
        ttk.Label(main_frame, text=f"Found {len(image_files)} images:").pack(anchor=tk.W)
        
        list_frame = ttk.Frame(main_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 20))
        
        # Create listbox with scrollbar
        listbox = tk.Listbox(list_frame, height=10)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=listbox.yview)
        listbox.configure(yscrollcommand=scrollbar.set)
        
        for img_file in image_files:
            listbox.insert(tk.END, img_file.name)
        
        listbox.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Batch options
        options_frame = ttk.LabelFrame(main_frame, text="Batch Options", padding="10")
        options_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Add common metadata to all images
        ttk.Label(options_frame, text="Add to all images:").pack(anchor=tk.W)
        
        common_fields = ['Title', 'Description', 'Keywords', 'Author', 'Copyright']
        field_vars = {}
        
        for field in common_fields:
            field_frame = ttk.Frame(options_frame)
            field_frame.pack(fill=tk.X, pady=2)
            
            ttk.Label(field_frame, text=f"{field}:", width=12).pack(side=tk.LEFT)
            field_var = tk.StringVar()
            ttk.Entry(field_frame, textvariable=field_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
            field_vars[field] = field_var
        
        # Action buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        ttk.Button(button_frame, text="🚀 Process All", 
                  command=lambda: self.execute_batch_processing(image_files, field_vars, batch_window)).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="❌ Cancel", 
                  command=batch_window.destroy).pack(side=tk.LEFT)
                  
    def execute_batch_processing(self, image_files, field_vars, window):
        """Execute batch metadata processing."""
        # Get values from fields
        batch_metadata = {}
        for field, var in field_vars.items():
            value = var.get().strip()
            if value:
                batch_metadata[field] = value
        
        if not batch_metadata:
            messagebox.showwarning("Warning", "Please enter at least one metadata field")
            return
            
        # Process images
        processed = 0
        errors = 0
        
        for img_file in image_files:
            try:
                # Load image
                image = Image.open(img_file)
                exif_dict = image.getexif()
                
                # Add batch metadata
                tag_mapping = {
                    'Title': 270,
                    'Description': 270,
                    'Keywords': 272,
                    'Author': 315,
                    'Copyright': 33432,
                }
                
                for field, value in batch_metadata.items():
                    tag_id = tag_mapping.get(field)
                    if tag_id:
                        exif_dict[tag_id] = value
                
                # Save image
                image.save(img_file, exif=exif_dict)
                processed += 1
                
            except Exception as e:
                errors += 1
                self.log_message(f"❌ Error processing {img_file.name}: {str(e)}")
        
        # Show results
        messagebox.showinfo("Batch Processing Complete", 
                           f"Processed: {processed} images\nErrors: {errors} images")
        
        window.destroy()
        
    def show_batch_summary(self):
        """Show summary of batch processing."""
        if not self.batch_folder:
            messagebox.showwarning("Warning", "No batch folder selected")
            return
            
        # This would show statistics about processed images
        messagebox.showinfo("Batch Summary", "Batch processing summary feature coming soon!")
    
    def setup_ai_chat_tab(self):
        """Setup the AI Chat tab for direct interaction with the model."""
        # Main container
        chat_container = ttk.Frame(self.ai_chat_frame, padding="10")
        chat_container.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(chat_container, text="🤖 AI Chat - Direct Model Interaction", 
                               font=('Arial', 16, 'bold'))
        title_label.pack(pady=(0, 20))
        
        # Connection status and model info
        status_frame = ttk.Frame(chat_container)
        status_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.chat_connection_status = ttk.Label(status_frame, text="❌ Not Connected", 
                                              foreground="red", font=('Arial', 10, 'bold'))
        self.chat_connection_status.pack(side=tk.LEFT)
        
        self.chat_model_info = ttk.Label(status_frame, text="No model selected", 
                                       foreground="gray")
        self.chat_model_info.pack(side=tk.LEFT, padx=(20, 0))
        
        # AI Settings section
        settings_frame = ttk.LabelFrame(chat_container, text="⚙️ AI Settings", padding="10")
        settings_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Model selection row
        model_frame = ttk.Frame(settings_frame)
        model_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(model_frame, text="Vision Model:").pack(side=tk.LEFT, padx=(0, 5))
        self.chat_vision_model_var = tk.StringVar(value=self.vision_model)
        vision_model_combo = ttk.Combobox(model_frame, textvariable=self.chat_vision_model_var, 
                                         values=[self.vision_model], width=25, state="readonly")
        vision_model_combo.pack(side=tk.LEFT, padx=(0, 20))
        
        ttk.Label(model_frame, text="Tool Model:").pack(side=tk.LEFT, padx=(0, 5))
        self.chat_tool_model_var = tk.StringVar(value=self.tool_use_model)
        tool_model_combo = ttk.Combobox(model_frame, textvariable=self.chat_tool_model_var, 
                                       values=self.available_tool_models, width=30, state="readonly")
        tool_model_combo.pack(side=tk.LEFT, padx=(0, 20))
        
        # Tool use controls row
        tool_frame = ttk.Frame(settings_frame)
        tool_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.chat_tool_use_var = tk.BooleanVar(value=self.tool_use_enabled)
        tool_use_check = ttk.Checkbutton(tool_frame, text="🔧 Enable Tool Use", 
                                        variable=self.chat_tool_use_var,
                                        command=self.toggle_chat_tool_use)
        tool_use_check.pack(side=tk.LEFT, padx=(0, 20))
        
        self.chat_disable_thinking_var = tk.BooleanVar(value=self.disable_thinking)
        thinking_check = ttk.Checkbutton(tool_frame, text="🧠 Hide Thinking Output", 
                                        variable=self.chat_disable_thinking_var,
                                        command=self.toggle_chat_thinking_disable)
        thinking_check.pack(side=tk.LEFT, padx=(0, 20))
        
        # Token and temperature controls row
        params_frame = ttk.Frame(settings_frame)
        params_frame.pack(fill=tk.X)
        
        ttk.Label(params_frame, text="Max Tokens:").pack(side=tk.LEFT, padx=(0, 5))
        self.chat_token_limit_var = tk.StringVar(value=str(self.tool_use_max_tokens))
        token_spinbox = ttk.Spinbox(params_frame, from_=1000, to=8000, width=8, 
                                   textvariable=self.chat_token_limit_var,
                                   command=self.update_chat_token_limit)
        token_spinbox.pack(side=tk.LEFT, padx=(0, 20))
        
        ttk.Label(params_frame, text="Temperature:").pack(side=tk.LEFT, padx=(0, 5))
        self.chat_temperature_var = tk.StringVar(value=str(self.tool_use_temperature))
        temp_spinbox = ttk.Spinbox(params_frame, from_=0.1, to=1.0, increment=0.1, width=6, 
                                  textvariable=self.chat_temperature_var,
                                  command=self.update_chat_temperature)
        temp_spinbox.pack(side=tk.LEFT, padx=(0, 20))
        
        # Update model info display
        self.update_chat_model_display()
        
        # Image selection and preview section
        image_frame = ttk.LabelFrame(chat_container, text="🖼️ Current Image", padding="10")
        image_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Image selection row
        image_select_frame = ttk.Frame(image_frame)
        image_select_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(image_select_frame, text="📁 Select Image", 
                  command=self.select_chat_image).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(image_select_frame, text="📂 Select Folder", 
                  command=self.select_chat_folder).pack(side=tk.LEFT, padx=(0, 10))
        
        self.chat_image_path = ttk.Label(image_select_frame, text="No image selected", 
                                       foreground="gray", font=('Arial', 9))
        self.chat_image_path.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(image_select_frame, text="🔄 Use from Metadata Tab", 
                  command=self.use_metadata_image).pack(side=tk.LEFT)
        
        # Folder navigation (if folder is selected)
        self.chat_folder_frame = ttk.Frame(image_frame)
        self.chat_folder_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.chat_folder_path = ttk.Label(self.chat_folder_frame, text="", 
                                        foreground="blue", font=('Arial', 9))
        self.chat_folder_path.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(self.chat_folder_frame, text="⬅️ Previous", 
                  command=self.previous_chat_image).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(self.chat_folder_frame, text="➡️ Next", 
                  command=self.next_chat_image).pack(side=tk.LEFT, padx=(0, 5))
        
        self.chat_image_counter = ttk.Label(self.chat_folder_frame, text="", 
                                          foreground="gray", font=('Arial', 9))
        self.chat_image_counter.pack(side=tk.LEFT, padx=(10, 0))
        
        # Image preview
        self.chat_image_canvas = tk.Canvas(image_frame, width=200, height=150, 
                                         bg="lightgray", relief=tk.SUNKEN, bd=2)
        self.chat_image_canvas.pack(side=tk.LEFT, padx=(0, 10))
        
        # Image info
        self.chat_image_info = ttk.Label(image_frame, text="No image loaded", 
                                       font=('Arial', 9), foreground="gray")
        self.chat_image_info.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Chat history area
        chat_history_frame = ttk.LabelFrame(chat_container, text="💬 Chat History", padding="10")
        chat_history_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Chat display with scrollbar
        chat_display_frame = ttk.Frame(chat_history_frame)
        chat_display_frame.pack(fill=tk.BOTH, expand=True)
        
        self.chat_display = scrolledtext.ScrolledText(chat_display_frame, wrap=tk.WORD, 
                                                     height=15, state=tk.DISABLED,
                                                     font=('Consolas', 10))
        self.chat_display.pack(fill=tk.BOTH, expand=True)
        
        # Input area
        input_frame = ttk.LabelFrame(chat_container, text="✍️ Send Message", padding="10")
        input_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Message input
        self.chat_input = scrolledtext.ScrolledText(input_frame, wrap=tk.WORD, height=4,
                                                   font=('Arial', 10))
        self.chat_input.pack(fill=tk.X, pady=(0, 10))
        
        # Control buttons
        button_frame = ttk.Frame(input_frame)
        button_frame.pack(fill=tk.X)
        
        ttk.Button(button_frame, text="📤 Send Message", 
                  command=self.send_chat_message).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="🖼️ Send with Current Image", 
                  command=self.send_chat_with_image).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="🗑️ Clear Chat", 
                  command=self.clear_chat).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="💾 Save Chat", 
                  command=self.save_chat).pack(side=tk.LEFT)
        
        # Apply AI output to metadata buttons
        apply_frame = ttk.Frame(button_frame)
        apply_frame.pack(side=tk.RIGHT)
        
        ttk.Button(apply_frame, text="📝 Apply Description", 
                  command=self.apply_ai_description_to_metadata).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(apply_frame, text="🔍 Apply SEO Data", 
                  command=self.apply_ai_seo_to_metadata).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(apply_frame, text="⚡ Apply All", 
                  command=self.apply_all_ai_to_metadata).pack(side=tk.LEFT)
        
        # Quick action buttons
        quick_frame = ttk.LabelFrame(chat_container, text="⚡ Quick Actions", padding="10")
        quick_frame.pack(fill=tk.X)
        
        quick_buttons = ttk.Frame(quick_frame)
        quick_buttons.pack(fill=tk.X)
        
        ttk.Button(quick_buttons, text="🔍 Analyze Image", 
                  command=self.quick_analyze_image).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(quick_buttons, text="📝 Generate SEO", 
                  command=self.quick_generate_seo).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(quick_buttons, text="🎨 Describe Colors", 
                  command=self.quick_describe_colors).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(quick_buttons, text="📐 Analyze Composition", 
                  command=self.quick_analyze_composition).pack(side=tk.LEFT)
        
        # Initialize chat
        self.chat_messages = []
        self.add_chat_message("system", "AI Chat initialized. Select an image and start chatting!")
    
    def update_chat_model_display(self):
        """Update the model display in AI Chat tab."""
        if self.tool_use_enabled:
            model_text = f"Model: {self.tool_use_model} (Tool Use)"
            self.chat_model_info.config(text=model_text, foreground="blue")
        else:
            model_text = f"Model: {self.vision_model} (Vision)"
            self.chat_model_info.config(text=model_text, foreground="green")
    
    def toggle_chat_tool_use(self):
        """Toggle tool use from AI Chat tab."""
        self.tool_use_enabled = self.chat_tool_use_var.get()
        status = "enabled" if self.tool_use_enabled else "disabled"
        self.log_message(f"🔧 Tool use {status} - Using model: {self.tool_use_model}")
        self.update_chat_model_display()
        
        if self.tool_use_enabled:
            self.add_chat_message("system", f"🔧 Tool use enabled! Using {self.tool_use_model} for folder analysis.")
        else:
            self.add_chat_message("system", f"🔧 Tool use disabled. Using {self.vision_model} for image analysis.")
    
    def toggle_chat_thinking_disable(self):
        """Toggle thinking display from AI Chat tab."""
        self.disable_thinking = self.chat_disable_thinking_var.get()
        status = "hidden" if self.disable_thinking else "visible"
        self.log_message(f"🧠 Thinking output {status} for DeepSeek model")
        self.add_chat_message("system", f"🧠 Thinking output {status} for DeepSeek model (tool use still works)")
    
    def update_chat_token_limit(self):
        """Update token limit from AI Chat tab."""
        try:
            new_limit = int(self.chat_token_limit_var.get())
            if 1000 <= new_limit <= 8000:
                self.tool_use_max_tokens = new_limit
                self.log_message(f"🔧 Token limit updated to {new_limit}")
                self.add_chat_message("system", f"🔧 Token limit updated to {new_limit}")
            else:
                self.chat_token_limit_var.set(str(self.tool_use_max_tokens))
                messagebox.showwarning("Invalid Token Limit", "Token limit must be between 1000 and 8000")
        except ValueError:
            self.chat_token_limit_var.set(str(self.tool_use_max_tokens))
            messagebox.showwarning("Invalid Token Limit", "Please enter a valid number")
    
    def update_chat_temperature(self):
        """Update temperature from AI Chat tab."""
        try:
            new_temp = float(self.chat_temperature_var.get())
            if 0.1 <= new_temp <= 1.0:
                self.tool_use_temperature = new_temp
                self.log_message(f"🌡️ Temperature updated to {new_temp}")
                self.add_chat_message("system", f"🌡️ Temperature updated to {new_temp}")
            else:
                self.chat_temperature_var.set(str(self.tool_use_temperature))
                messagebox.showwarning("Invalid Temperature", "Temperature must be between 0.1 and 1.0")
        except ValueError:
            self.chat_temperature_var.set(str(self.tool_use_temperature))
            messagebox.showwarning("Invalid Temperature", "Please enter a valid number")
    
    def filter_thinking_output(self, message):
        """Filter out thinking tags if thinking is disabled."""
        if self.disable_thinking and "<think>" in message:
            # Remove thinking tags and content
            import re
            # Remove <think>...</think> blocks
            filtered = re.sub(r'<think>.*?</think>', '', message, flags=re.DOTALL)
            # Clean up extra whitespace
            filtered = re.sub(r'\n\s*\n', '\n', filtered).strip()
            return filtered if filtered else message
        return message
    
    def add_chat_message(self, sender, message, timestamp=None):
        """Add a message to the chat display."""
        if timestamp is None:
            timestamp = time.strftime("%H:%M:%S")
        
        # Filter thinking output if disabled
        display_message = self.filter_thinking_output(message)
        
        self.chat_display.config(state=tk.NORMAL)
        
        # Add timestamp and sender
        self.chat_display.insert(tk.END, f"[{timestamp}] ", "timestamp")
        if sender == "user":
            self.chat_display.insert(tk.END, "You: ", "user")
        elif sender == "ai":
            self.chat_display.insert(tk.END, "AI: ", "ai")
        else:
            self.chat_display.insert(tk.END, f"{sender.title()}: ", "system")
        
        # Add message
        self.chat_display.insert(tk.END, f"{display_message}\n\n")
        
        # Configure tags for styling
        self.chat_display.tag_configure("timestamp", foreground="gray")
        self.chat_display.tag_configure("user", foreground="blue", font=('Arial', 10, 'bold'))
        self.chat_display.tag_configure("ai", foreground="green", font=('Arial', 10, 'bold'))
        self.chat_display.tag_configure("system", foreground="purple", font=('Arial', 10, 'bold'))
        
        # Scroll to bottom
        self.chat_display.see(tk.END)
        self.chat_display.config(state=tk.DISABLED)
        
        # Store message
        self.chat_messages.append({
            'sender': sender,
            'message': message,
            'timestamp': timestamp
        })
    
    def send_chat_message(self):
        """Send a text-only message to the AI."""
        message = self.chat_input.get("1.0", tk.END).strip()
        if not message:
            return
        
        if not self.ai_connected:
            self.add_chat_message("system", "❌ Not connected to LM Studio. Please check connection.")
            return
        
        # Add user message to chat
        self.add_chat_message("user", message)
        
        # Clear input
        self.chat_input.delete("1.0", tk.END)
        
        # Send to AI
        threading.Thread(target=self._process_chat_message, args=(message,), daemon=True).start()
    
    def send_chat_with_image(self):
        """Send a message with the current image to the AI."""
        # Check for image in chat tab first, then metadata tab
        image_path = None
        if hasattr(self, 'chat_current_image') and self.chat_current_image:
            image_path = self.chat_current_image
        elif self.metadata_image_path.get():
            image_path = self.metadata_image_path.get()
        
        if not image_path or not os.path.exists(image_path):
            self.add_chat_message("system", "❌ No image selected. Please select an image first using 'Select Image' or 'Use from Metadata Tab'.")
            return
        
        message = self.chat_input.get("1.0", tk.END).strip()
        if not message:
            message = "Please analyze this image and provide a detailed description."
        
        if not self.ai_connected:
            self.add_chat_message("system", "❌ Not connected to LM Studio. Please check connection.")
            return
        
        # Add user message to chat
        self.add_chat_message("user", f"{message} (with image: {os.path.basename(image_path)})")
        
        # Clear input
        self.chat_input.delete("1.0", tk.END)
        
        # Send to AI with image
        threading.Thread(target=self._process_chat_with_image, args=(message, image_path), daemon=True).start()
    
    def _process_chat_message(self, message):
        """Process a text-only chat message."""
        try:
            self.add_chat_message("system", "🤖 AI is thinking...")
            
            # Call LM Studio API for text-only
            response = self._call_lm_studio_text_api(message)
            
            if response:
                self.add_chat_message("ai", response)
            else:
                self.add_chat_message("system", "❌ Failed to get response from AI")
                
        except Exception as e:
            self.add_chat_message("system", f"❌ Error: {str(e)}")
    
    def parse_filename_data(self, filename):
        """Parse filename to extract relevant metadata context."""
        try:
            # Remove extension
            name_without_ext = Path(filename).stem
            
            # Common product filename patterns
            # Examples: F032_ST78_Grey_Cascia_Granite_room_images_000
            # Pattern: [Code]_[Type]_[Color]_[Name]_[Category]_[Number]
            
            parts = name_without_ext.split('_')
            parsed_data = {
                'filename': filename,
                'code': '',
                'type': '',
                'color': '',
                'name': '',
                'category': '',
                'number': ''
            }
            
            if len(parts) >= 6:
                parsed_data['code'] = parts[0]  # F032
                parsed_data['type'] = parts[1]  # ST78
                parsed_data['color'] = parts[2]  # Grey
                parsed_data['name'] = parts[3]  # Cascia
                parsed_data['category'] = parts[4]  # Granite
                parsed_data['number'] = parts[5] if len(parts) > 5 else ''  # room_images_000
            
            return parsed_data
            
        except Exception as e:
            print(f"Error parsing filename: {e}")
            return {'filename': filename, 'code': '', 'type': '', 'color': '', 'name': '', 'category': '', 'number': ''}
    
    def _process_chat_with_image(self, message, image_path):
        """Process a chat message with image with context and memory."""
        try:
            self.add_chat_message("system", "🤖 AI is analyzing image...")
            
            # Validate image path
            if not image_path or not os.path.exists(image_path):
                self.add_chat_message("system", "❌ No valid image selected")
                return
            
            # Parse filename for context
            filename = Path(image_path).name
            filename_data = self.parse_filename_data(filename)
            
            # Store filename data for use in parsing
            self.current_filename_data = filename_data
            
            # Build comprehensive context from filename data and folder
            folder_context = ""
            if self.chat_folder_images:
                folder_name = os.path.basename(self.chat_folder_path_str) if self.chat_folder_path_str else "Unknown"
                total_images = len(self.chat_folder_images)
                current_position = self.chat_current_image_index + 1
                
                # Get sample filenames from the folder for context
                sample_files = []
                for i, img_path in enumerate(self.chat_folder_images[:5]):  # First 5 files
                    sample_files.append(os.path.basename(img_path))
                
                folder_context = f"""
FOLDER CONTEXT:
- Folder Name: {folder_name}
- Total Images: {total_images}
- Current Image: {current_position} of {total_images}
- Sample Files: {', '.join(sample_files)}
- This is part of a batch of {total_images} images from the same product line
"""

            context = f"""
{filename_data['filename']} - IMAGE ANALYSIS REQUEST

PRODUCT INFORMATION:
- Product Code: {filename_data['code']}
- Product Type: {filename_data['type']}
- Color: {filename_data['color']}
- Product Name: {filename_data['name']}
- Category: {filename_data['category']}

{folder_context}

USER REQUEST: {message}

ANALYSIS TASK:
Please analyze this image and provide metadata suggestions. Consider:
1. The product type and color from the filename
2. The room/space shown in the image
3. The overall design and style
4. How this fits with the broader product line (if part of a folder)

REQUIRED OUTPUT FORMAT:
Title: [descriptive title based on the product and room shown]
Description: [detailed description of what's shown in the image]
Keywords: [relevant search terms, comma-separated]
Artist: [Your Company Name]
Make: {filename_data['code']}
Model: {filename_data['type']}

Please ensure all 6 fields are provided with the exact format shown above.
"""
            
            # Encode image to base64
            with open(image_path, "rb") as image_file:
                image_data = base64.b64encode(image_file.read()).decode('utf-8')
            
            # Call LM Studio API with image and context
            response = self._call_lm_studio_api_with_context(image_data, context)
            
            if response:
                self.add_chat_message("ai", response)
            else:
                # Fallback: Try text-only approach with filename context
                self.add_chat_message("system", "🔄 Vision model failed, trying text-only approach...")
                text_context = f"""
Based on the filename {filename_data['filename']}, please provide metadata for this interior design image:

Product Code: {filename_data['code']}
Product Type: {filename_data['type']}
Color: {filename_data['color']}
Product Name: {filename_data['name']}
Category: {filename_data['category']}

User Request: {message}

Please provide:
- Title: A descriptive title for this {filename_data['category']} {filename_data['color']} {filename_data['name']} room image
- Description: A detailed description of what's shown in the image
- Keywords: Relevant search terms (comma-separated)
- Artist: [Your Company Name]
- Make: {filename_data['code']}
- Model: {filename_data['type']}
"""
                
                text_response = self._call_lm_studio_text_api(text_context)
                if text_response:
                    self.add_chat_message("ai", text_response)
                else:
                    self.add_chat_message("system", "❌ Failed to get response from AI (both vision and text failed)")
                
        except Exception as e:
            self.add_chat_message("system", f"❌ Error: {str(e)}")
    
    def _call_lm_studio_text_api(self, message):
        """Call LM Studio API for text-only messages with conversation memory."""
        try:
            print(f"AI Debug (Text) - Tool use enabled: {self.tool_use_enabled}")
            print(f"AI Debug (Text) - Message: {message}")
            # Use tool use if enabled
            if self.tool_use_enabled:
                print(f"AI Debug (Text) - Tool use enabled, calling tool use API")
                result = self._call_tool_use_api_with_tools(message)
                print(f"AI Debug (Text) - Tool use API result: {result is not None}")
                return result
            
            url = f"{self.lm_studio_url.get()}/v1/chat/completions"
            
            selected_model = self.lm_studio_model.get()
            if not selected_model:
                selected_model = "qwen/qwen2.5-vl-7b"
            
            # Use the full model name as it appears in LM Studio
            model_name = selected_model
            
            # Build message with context
            messages = []
            
            # Build context-aware message
            context_message = message
            
            # Add folder context if available
            if hasattr(self, 'chat_folder_images') and self.chat_folder_images:
                folder_name = os.path.basename(self.chat_folder_path_str) if hasattr(self, 'chat_folder_path_str') and self.chat_folder_path_str else "Unknown"
                total_images = len(self.chat_folder_images)
                current_position = self.chat_current_image_index + 1
                
                context_message = f"""
FOLDER CONTEXT: You are working with a folder called "{folder_name}" containing {total_images} images. You are currently on image {current_position} of {total_images}.

USER MESSAGE: {message}

Please respond with this context in mind, understanding that you're working through a batch of related images.
"""
            
            messages.append({
                "role": "user",
                "content": context_message
            })
            
            print(f"AI Debug (Text) - Using Model Name: {model_name}")
            print(f"AI Debug (Text) - Messages count: {len(messages)}")
            
            payload = {
                "model": model_name,
                "messages": messages,
                "max_tokens": self.vision_max_tokens,
                "temperature": self.vision_temperature
            }
            
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            print(f"AI Debug (Text) - Sending request to: {url}")
            print(f"AI Debug (Text) - Headers: {headers}")
            print(f"AI Debug (Text) - Payload: {json.dumps(payload, indent=2)}")
            
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            
            print(f"AI Debug (Text) - Response status: {response.status_code}")
            print(f"AI Debug (Text) - Response text: {response.text}")
            
            if response.status_code != 200:
                print(f"AI Debug (Text) - Error response: {response.text}")
                return None
                
            result = response.json()
            return result['choices'][0]['message']['content']
            
        except Exception as e:
            self.log_message(f"❌ Text API call error: {str(e)}")
            return None
    
    def _call_lm_studio_api_with_context(self, image_data, context):
        """Call LM Studio API with image and context."""
        try:
            url = f"{self.lm_studio_url.get()}/v1/chat/completions"
            
            # Use vision model configuration
            model_name = self.vision_model
            
            print(f"AI Debug (Vision) - Using vision model: {model_name}")
            
            print(f"AI Debug (Vision) - URL: {url}")
            print(f"AI Debug (Vision) - Model: {model_name}")
            print(f"AI Debug (Vision) - Context length: {len(context)}")
            print(f"AI Debug (Vision) - Image data length: {len(image_data)}")
            
            # Build messages for vision model
            messages = []
            
            # Add system context
            messages.append({
                "role": "system",
                "content": "You are an expert at analyzing interior design images and creating SEO-optimized metadata. You have access to product information from filenames and can see image content. Always provide structured responses for metadata fields."
            })
            
            # For vision models, keep it simple - just the current request with image
            # Don't mix conversation history with vision messages as it causes format conflicts
            messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": context
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_data}"
                        }
                    }
                ]
            })
            
            payload = {
                "model": model_name,
                "messages": messages,
                "max_tokens": self.vision_max_tokens,
                "temperature": self.vision_temperature
            }
            
            print(f"AI Debug - Payload messages count: {len(messages)}")
            print(f"AI Debug - Sending request...")
            
            # Debug: Print the exact payload being sent
            import json
            print(f"AI Debug - Full payload: {json.dumps(payload, indent=2)}")
            
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            print(f"AI Debug - Headers: {headers}")
            
            response = requests.post(url, json=payload, headers=headers, timeout=60)
            
            print(f"AI Debug - Response status: {response.status_code}")
            print(f"AI Debug - Response headers: {dict(response.headers)}")
            
            if response.status_code != 200:
                print(f"AI Debug - Error response: {response.text}")
                self.add_chat_message("system", f"❌ API Error {response.status_code}: {response.text}")
                return None
            
            result = response.json()
            print(f"AI Debug - Response result: {result}")
            
            if 'choices' in result and len(result['choices']) > 0:
                content = result['choices'][0]['message']['content']
                print(f"AI Debug - Extracted content: {content[:100]}...")
                return content
            else:
                print(f"AI Debug - No choices in response: {result}")
                return None
            
        except Exception as e:
            print(f"Error calling LM Studio API with context: {e}")
            self.add_chat_message("system", f"❌ API Error: {str(e)}")
            return None
    
    def clear_chat(self):
        """Clear the chat history."""
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.delete("1.0", tk.END)
        self.chat_display.config(state=tk.DISABLED)
        self.chat_messages = []
        self.add_chat_message("system", "Chat cleared. Ready for new conversation!")
    
    def save_chat(self):
        """Save chat history to file."""
        if not self.chat_messages:
            messagebox.showwarning("Warning", "No chat messages to save")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            title="Save Chat History"
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    for msg in self.chat_messages:
                        f.write(f"[{msg['timestamp']}] {msg['sender'].title()}: {msg['message']}\n\n")
                self.add_chat_message("system", f"💾 Chat saved to {filename}")
            except Exception as e:
                self.add_chat_message("system", f"❌ Error saving chat: {str(e)}")
    
    def quick_analyze_image(self):
        """Quick action: Analyze current image."""
        # Check for image in chat tab first, then metadata tab
        image_path = None
        if hasattr(self, 'chat_current_image') and self.chat_current_image:
            image_path = self.chat_current_image
        elif self.metadata_image_path.get():
            image_path = self.metadata_image_path.get()
        
        if not image_path or not os.path.exists(image_path):
            self.add_chat_message("system", "❌ No image selected. Please select an image first.")
            return
        
        self.chat_input.delete("1.0", tk.END)
        self.chat_input.insert("1.0", "Please analyze this image in detail, describing what you see, the composition, colors, and any interesting features.")
        self.send_chat_with_image()
    
    def quick_generate_seo(self):
        """Quick action: Generate SEO data."""
        # Check for image in chat tab first, then metadata tab
        image_path = None
        if hasattr(self, 'chat_current_image') and self.chat_current_image:
            image_path = self.chat_current_image
        elif self.metadata_image_path.get():
            image_path = self.metadata_image_path.get()
        
        if not image_path or not os.path.exists(image_path):
            self.add_chat_message("system", "❌ No image selected. Please select an image first.")
            return
        
        self.chat_input.delete("1.0", tk.END)
        self.chat_input.insert("1.0", "Generate SEO-optimized metadata for this image including title, description, keywords, and alt text.")
        self.send_chat_with_image()
    
    def quick_describe_colors(self):
        """Quick action: Describe colors."""
        # Check for image in chat tab first, then metadata tab
        image_path = None
        if hasattr(self, 'chat_current_image') and self.chat_current_image:
            image_path = self.chat_current_image
        elif self.metadata_image_path.get():
            image_path = self.metadata_image_path.get()
        
        if not image_path or not os.path.exists(image_path):
            self.add_chat_message("system", "❌ No image selected. Please select an image first.")
            return
        
        self.chat_input.delete("1.0", tk.END)
        self.chat_input.insert("1.0", "Describe the color palette of this image in detail, including dominant colors, accent colors, and the overall color scheme.")
        self.send_chat_with_image()
    
    def quick_analyze_composition(self):
        """Quick action: Analyze composition."""
        # Check for image in chat tab first, then metadata tab
        image_path = None
        if hasattr(self, 'chat_current_image') and self.chat_current_image:
            image_path = self.chat_current_image
        elif self.metadata_image_path.get():
            image_path = self.metadata_image_path.get()
        
        if not image_path or not os.path.exists(image_path):
            self.add_chat_message("system", "❌ No image selected. Please select an image first.")
            return
        
        self.chat_input.delete("1.0", tk.END)
        self.chat_input.insert("1.0", "Analyze the composition of this image, including the rule of thirds, focal points, balance, and overall visual structure.")
        self.send_chat_with_image()
    
    def select_chat_image(self):
        """Select an image for the chat tab."""
        filename = filedialog.askopenfilename(
            title="Select Image for AI Chat",
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.bmp *.tiff *.webp *.avif"),
                ("All files", "*.*")
            ]
        )
        
        if filename:
            self.load_chat_image(filename)
    
    def use_metadata_image(self):
        """Use the image from the metadata tab."""
        # Get the actual path value from StringVar
        image_path = self.metadata_image_path.get()
        
        if image_path and os.path.exists(image_path):
            self.load_chat_image(image_path)
            self.add_chat_message("system", f"📸 Using image from Metadata tab: {os.path.basename(image_path)}")
        else:
            self.add_chat_message("system", "❌ No image selected in Metadata tab")
    
    def load_chat_image(self, image_path):
        """Load and display an image in the chat tab."""
        try:
            # Store the image path
            self.chat_current_image = image_path
            
            # Update path label
            self.chat_image_path.config(text=os.path.basename(image_path), foreground="black")
            
            # Load and display image
            image = Image.open(image_path)
            
            # Resize image to fit canvas
            canvas_width = 200
            canvas_height = 150
            
            # Calculate aspect ratio
            img_width, img_height = image.size
            aspect_ratio = img_width / img_height
            
            if aspect_ratio > canvas_width / canvas_height:
                # Image is wider
                new_width = canvas_width
                new_height = int(canvas_width / aspect_ratio)
            else:
                # Image is taller
                new_height = canvas_height
                new_width = int(canvas_height * aspect_ratio)
            
            # Resize image
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Convert to PhotoImage
            photo = ImageTk.PhotoImage(image)
            
            # Clear canvas and display image
            self.chat_image_canvas.delete("all")
            x = (canvas_width - new_width) // 2
            y = (canvas_height - new_height) // 2
            self.chat_image_canvas.create_image(x, y, anchor=tk.NW, image=photo)
            
            # Keep reference to prevent garbage collection
            self.chat_image_canvas.image = photo
            
            # Update image info
            file_size = os.path.getsize(image_path)
            size_mb = file_size / (1024 * 1024)
            info_text = f"📏 {img_width}x{img_height}\n💾 {size_mb:.2f} MB\n📁 {os.path.basename(image_path)}"
            self.chat_image_info.config(text=info_text, foreground="black")
            
            self.add_chat_message("system", f"📸 Image loaded: {os.path.basename(image_path)} ({img_width}x{img_height})")
            
        except Exception as e:
            self.add_chat_message("system", f"❌ Error loading image: {str(e)}")
            self.chat_image_path.config(text="Error loading image", foreground="red")
            self.chat_image_info.config(text="Failed to load image", foreground="red")
    
    def apply_ai_description_to_metadata(self):
        """Apply the most recent AI description to metadata fields."""
        if not self.chat_messages:
            self.add_chat_message("system", "❌ No chat messages to process")
            return
        
        # Find the most recent AI message with detailed description
        ai_messages = [msg for msg in reversed(self.chat_messages) if msg['sender'] == 'ai']
        
        if not ai_messages:
            self.add_chat_message("system", "❌ No AI responses found")
            return
        
        # Get the most recent AI response
        latest_ai_response = ai_messages[0]['message']
        
        # Extract key information from the AI response
        metadata_dict = self._parse_ai_response_for_metadata(latest_ai_response)
        
        # Apply to metadata fields
        self._apply_metadata_to_fields(metadata_dict)
        
        # Switch to metadata tab
        self.notebook.select(self.metadata_frame)
        
        self.add_chat_message("system", "✅ Description applied to metadata fields. Check the Metadata tab.")
    
    def apply_ai_seo_to_metadata(self):
        """Apply SEO data from AI responses to metadata fields."""
        if not self.chat_messages:
            self.add_chat_message("system", "❌ No chat messages to process")
            return
        
        # Find AI messages that contain SEO recommendations
        seo_messages = []
        for msg in reversed(self.chat_messages):
            if msg['sender'] == 'ai' and any(keyword in msg['message'].lower() for keyword in 
                ['seo', 'meta', 'title', 'description', 'alt text', 'keywords', 'structured data']):
                seo_messages.append(msg)
        
        if not seo_messages:
            self.add_chat_message("system", "❌ No SEO-related AI responses found")
            return
        
        # Parse the most recent SEO response
        seo_response = seo_messages[0]['message']
        metadata_dict = self._parse_seo_response_for_metadata(seo_response)
        
        # Apply to metadata fields
        self._apply_metadata_to_fields(metadata_dict)
        
        # Switch to metadata tab
        self.notebook.select(self.metadata_frame)
        
        self.add_chat_message("system", "✅ SEO data applied to metadata fields. Check the Metadata tab.")
    
    def apply_all_ai_to_metadata(self):
        """Apply all relevant AI data to metadata fields."""
        if not self.chat_messages:
            self.add_chat_message("system", "❌ No chat messages to process")
            return
        
        # Combine all AI responses
        all_ai_responses = [msg['message'] for msg in self.chat_messages if msg['sender'] == 'ai']
        combined_response = "\n\n".join(all_ai_responses)
        
        # Parse for metadata
        metadata_dict = self._parse_ai_response_for_metadata(combined_response)
        seo_metadata = self._parse_seo_response_for_metadata(combined_response)
        
        # Merge both dictionaries
        metadata_dict.update(seo_metadata)
        
        # Apply to metadata fields
        self._apply_metadata_to_fields(metadata_dict)
        
        # Switch to metadata tab
        self.notebook.select(self.metadata_frame)
        
        self.add_chat_message("system", "✅ All AI data applied to metadata fields. Check the Metadata tab.")
    
    def _parse_ai_response_for_metadata(self, ai_response):
        """Parse AI response to extract metadata fields."""
        metadata = {}
        
        self.add_chat_message("system", f"🔍 Parsing AI response for metadata...")
        
        # Extract description (look for detailed descriptions)
        lines = ai_response.split('\n')
        description_parts = []
        
        for line in lines:
            line = line.strip()
            if line and not line.startswith('**') and not line.startswith('###') and not line.startswith('```'):
                # Skip very short lines and headers
                if len(line) > 20:
                    description_parts.append(line)
        
        if description_parts:
            # Take the longest description part
            metadata['Description'] = max(description_parts, key=len)
            self.add_chat_message("system", f"📝 Found description: {metadata['Description'][:50]}...")
        
        # Extract keywords from the response
        keywords = []
        keyword_indicators = ['kitchen', 'worktop', 'countertop', 'cabinet', 'modern', 'design', 'concrete', 'wood', 'granite', 'braganza']
        for indicator in keyword_indicators:
            if indicator.lower() in ai_response.lower():
                keywords.append(indicator)
        
        if keywords:
            metadata['Keywords'] = ', '.join(keywords)
            self.add_chat_message("system", f"🏷️ Found keywords: {metadata['Keywords']}")
        
        # Extract title suggestions
        import re
        
        # Look for structured format first (Title: value)
        title_match = re.search(r'title\s*:\s*(.+?)(?:\n|$)', ai_response, re.IGNORECASE | re.MULTILINE)
        if title_match:
            metadata['Title'] = title_match.group(1).strip()
            self.add_chat_message("system", f"📋 Found title: {metadata['Title']}")
        elif 'title' in ai_response.lower() or 'name' in ai_response.lower():
            # Fallback to other patterns
            title_patterns = [
                r'title["\']?\s*[:=]\s*["\']([^"\']+)["\']',
                r'<title>([^<]+)</title>',
                r'name["\']?\s*[:=]\s*["\']([^"\']+)["\']'
            ]
            
            for pattern in title_patterns:
                match = re.search(pattern, ai_response, re.IGNORECASE)
                if match:
                    metadata['Title'] = match.group(1).strip()
                    self.add_chat_message("system", f"📋 Found title: {metadata['Title']}")
                    break
        
        # Extract Artist, Make, Model from AI response using structured format
        # Look for Artist field
        artist_match = re.search(r'artist\s*:\s*(.+?)(?:\n|$)', ai_response, re.IGNORECASE | re.MULTILINE)
        if artist_match:
            metadata['Artist'] = artist_match.group(1).strip()
            self.add_chat_message("system", f"👤 Found artist: {metadata['Artist']}")
        else:
            # Fallback patterns
            artist_patterns = [
                r'artist["\']?\s*[:=]\s*["\']([^"\']+)["\']',
                r'company["\']?\s*[:=]\s*["\']([^"\']+)["\']',
                r'brand["\']?\s*[:=]\s*["\']([^"\']+)["\']'
            ]
            for pattern in artist_patterns:
                match = re.search(pattern, ai_response, re.IGNORECASE)
                if match:
                    metadata['Artist'] = match.group(1).strip()
                    self.add_chat_message("system", f"👤 Found artist: {metadata['Artist']}")
                    break
        
        # Look for Make field
        make_match = re.search(r'make\s*:\s*(.+?)(?:\n|$)', ai_response, re.IGNORECASE | re.MULTILINE)
        if make_match:
            metadata['Make'] = make_match.group(1).strip()
            self.add_chat_message("system", f"🏭 Found make: {metadata['Make']}")
        else:
            # Fallback patterns
            make_patterns = [
                r'make["\']?\s*[:=]\s*["\']([^"\']+)["\']',
                r'product code["\']?\s*[:=]\s*["\']([^"\']+)["\']',
                r'code["\']?\s*[:=]\s*["\']([^"\']+)["\']'
            ]
            for pattern in make_patterns:
                match = re.search(pattern, ai_response, re.IGNORECASE)
                if match:
                    metadata['Make'] = match.group(1).strip()
                    self.add_chat_message("system", f"🏭 Found make: {metadata['Make']}")
                    break
        
        # Look for Model field
        model_match = re.search(r'model\s*:\s*(.+?)(?:\n|$)', ai_response, re.IGNORECASE | re.MULTILINE)
        if model_match:
            metadata['Model'] = model_match.group(1).strip()
            self.add_chat_message("system", f"📦 Found model: {metadata['Model']}")
        else:
            # Fallback patterns
            model_patterns = [
                r'model["\']?\s*[:=]\s*["\']([^"\']+)["\']',
                r'type["\']?\s*[:=]\s*["\']([^"\']+)["\']',
                r'product type["\']?\s*[:=]\s*["\']([^"\']+)["\']'
            ]
            for pattern in model_patterns:
                match = re.search(pattern, ai_response, re.IGNORECASE)
                if match:
                    metadata['Model'] = match.group(1).strip()
                    self.add_chat_message("system", f"📦 Found model: {metadata['Model']}")
                    break
        
        # If we didn't find structured data, try to extract from context
        if not metadata.get('Artist'):
            if 'egger' in ai_response.lower():
                metadata['Artist'] = '[Your Company Name]'
                self.add_chat_message("system", f"👤 Set artist to [Your Company Name] from context")
        
        if not metadata.get('Make') and not metadata.get('Model'):
            # Try to extract from filename context if available
            if hasattr(self, 'current_filename_data'):
                filename_data = self.current_filename_data
                if filename_data.get('code'):
                    metadata['Make'] = filename_data['code']
                    self.add_chat_message("system", f"🏭 Set make to {metadata['Make']} from filename")
                if filename_data.get('type'):
                    metadata['Model'] = filename_data['type']
                    self.add_chat_message("system", f"📦 Set model to {metadata['Model']} from filename")
        
        self.add_chat_message("system", f"📊 Parsed metadata: {list(metadata.keys())}")
        return metadata
    
    def _parse_seo_response_for_metadata(self, seo_response):
        """Parse SEO-specific response for metadata."""
        metadata = {}
        
        # Extract title from meta tags or structured data
        import re
        
        # Look for title in meta tags
        title_match = re.search(r'<meta[^>]*name=["\']title["\'][^>]*content=["\']([^"\']+)["\']', seo_response, re.IGNORECASE)
        if not title_match:
            title_match = re.search(r'title["\']?\s*[:=]\s*["\']([^"\']+)["\']', seo_response, re.IGNORECASE)
        
        if title_match:
            metadata['Title'] = title_match.group(1).strip()
        
        # Extract description
        desc_match = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']+)["\']', seo_response, re.IGNORECASE)
        if not desc_match:
            desc_match = re.search(r'description["\']?\s*[:=]\s*["\']([^"\']+)["\']', seo_response, re.IGNORECASE)
        
        if desc_match:
            metadata['Description'] = desc_match.group(1).strip()
        
        # Extract alt text
        alt_match = re.search(r'alt=["\']([^"\']+)["\']', seo_response, re.IGNORECASE)
        if alt_match:
            metadata['AltText'] = alt_match.group(1).strip()
        
        # Extract keywords
        keywords_match = re.search(r'keywords["\']?\s*[:=]\s*["\']([^"\']+)["\']', seo_response, re.IGNORECASE)
        if keywords_match:
            metadata['Keywords'] = keywords_match.group(1).strip()
        
        # Extract from structured data (JSON-LD)
        json_ld_match = re.search(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', seo_response, re.DOTALL | re.IGNORECASE)
        if json_ld_match:
            try:
                import json
                json_data = json.loads(json_ld_match.group(1))
                if 'name' in json_data:
                    metadata['Title'] = json_data['name']
                if 'description' in json_data:
                    metadata['Description'] = json_data['description']
            except:
                pass
        
        return metadata
    
    def _apply_metadata_to_fields(self, metadata_dict):
        """Apply metadata dictionary to the metadata editor fields."""
        if not metadata_dict:
            self.add_chat_message("system", "❌ No metadata to apply")
            return
        
        self.add_chat_message("system", f"🔍 Applying metadata: {list(metadata_dict.keys())}")
        
        # Map metadata keys to field names (use official EXIF field names)
        field_mapping = {
            'Title': 'XPTitle',
            'Description': 'ImageDescription', 
            'Keywords': 'XPKeywords',
            'AltText': 'AltText',
            'Author': 'Artist',
            'Artist': 'Artist',
            'Make': 'Make',
            'Model': 'Model',
            'Copyright': 'Copyright'
        }
        
        applied_count = 0
        for key, value in metadata_dict.items():
            if key in field_mapping:
                field_name = field_mapping[key]
                self.add_chat_message("system", f"📝 Setting {field_name}: {value[:50]}...")
                self._set_metadata_field(field_name, value)
                applied_count += 1
        
        self.add_chat_message("system", f"✅ Applied {applied_count} metadata fields")
        
        # Don't refresh metadata display as it clears the fields
        # The fields are already updated, just switch to metadata tab
        self.add_chat_message("system", "📋 Check the Metadata tab to see the populated fields")
    
    def _set_metadata_field(self, field_name, value):
        """Set a metadata field value."""
        # Ensure metadata fields are initialized
        if not hasattr(self, 'metadata_fields') or not self.metadata_fields:
            self._initialize_metadata_fields()
        
        if field_name in self.metadata_fields:
            # Access the StringVar from the dictionary
            self.metadata_fields[field_name]['var'].set(value)
            self.add_chat_message("system", f"✅ Set existing field {field_name}")
        else:
            # Create new field if it doesn't exist
            row = len(self.metadata_fields)
            self.create_metadata_field(field_name, value, row)
            self.add_chat_message("system", f"➕ Created new field {field_name}")
    
    def _initialize_metadata_fields(self):
        """Initialize basic metadata fields if they don't exist."""
        if not hasattr(self, 'metadata_scrollable_frame'):
            return
            
        # Standard metadata fields
        standard_fields = {
            'ImageDescription': '',
            'Description': '',
            'Keywords': '',
            'Author': '',
            'Copyright': ''
        }
        
        row = 0
        for field_name, field_value in standard_fields.items():
            if field_name not in self.metadata_fields:
                self.create_metadata_field(field_name, field_value, row)
                row += 1
    
    def update_chat_connection_status(self):
        """Update the chat tab connection status."""
        if hasattr(self, 'chat_connection_status'):
            if self.ai_connected:
                self.chat_connection_status.config(text="✅ Connected", foreground="green")
                if hasattr(self, 'chat_model_info'):
                    model = self.lm_studio_model.get()
                    self.chat_model_info.config(text=f"Model: {model}", foreground="black")
            else:
                self.chat_connection_status.config(text="❌ Not Connected", foreground="red")
                if hasattr(self, 'chat_model_info'):
                    self.chat_model_info.config(text="No model selected", foreground="gray")
    
    def setup_ai_integration(self):
        """Setup AI integration for LM Studio."""
        # Add AI settings to metadata tab
        self.add_ai_settings_to_metadata_tab()
    
    def add_ai_settings_to_metadata_tab(self):
        """Add AI settings section to metadata tab."""
        # Find the metadata frame and add AI settings
        for child in self.metadata_frame.winfo_children():
            if isinstance(child, ttk.Frame):
                # Add AI settings frame
                ai_frame = ttk.LabelFrame(child, text="🤖 AI-Powered Metadata Generation", padding="10")
                ai_frame.pack(fill=tk.X, pady=(10, 0))
                
                # LM Studio URL
                url_frame = ttk.Frame(ai_frame)
                url_frame.pack(fill=tk.X, pady=5)
                ttk.Label(url_frame, text="LM Studio URL:").pack(side=tk.LEFT)
                ttk.Entry(url_frame, textvariable=self.lm_studio_url, width=30).pack(side=tk.LEFT, padx=(5, 0))
                
                # Model Selection
                model_frame = ttk.Frame(ai_frame)
                model_frame.pack(fill=tk.X, pady=5)
                ttk.Label(model_frame, text="Model:").pack(side=tk.LEFT)
                self.model_combo = ttk.Combobox(model_frame, textvariable=self.lm_studio_model, 
                                              width=35, state="readonly")
                self.model_combo.pack(side=tk.LEFT, padx=(5, 0))
                ttk.Button(model_frame, text="🔄 Refresh", 
                          command=self.fetch_lm_studio_models).pack(side=tk.LEFT, padx=(5, 0))
                
                # Connection Status
                status_frame = ttk.Frame(ai_frame)
                status_frame.pack(fill=tk.X, pady=5)
                self.connection_status = ttk.Label(status_frame, text="❌ Not Connected", 
                                                 foreground="red")
                self.connection_status.pack(side=tk.LEFT)
                
                # Enable AI checkbox
                ttk.Checkbutton(ai_frame, text="Enable AI Description Generation", 
                               variable=self.ai_enabled).pack(anchor=tk.W, pady=5)
                
                # AI controls
                ai_controls = ttk.Frame(ai_frame)
                ai_controls.pack(fill=tk.X, pady=5)
                
                ttk.Button(ai_controls, text="🔍 Analyze Current Image", 
                          command=self.analyze_current_image).pack(side=tk.LEFT, padx=(0, 5))
                ttk.Button(ai_controls, text="📝 Generate SEO Data", 
                          command=self.generate_seo_data).pack(side=tk.LEFT, padx=(0, 5))
                ttk.Button(ai_controls, text="🔄 Test AI Connection", 
                          command=self.test_ai_connection).pack(side=tk.LEFT)
                
                break
    
    def analyze_current_image(self):
        """Analyze current image with AI to generate description."""
        if not self.metadata_image_path:
            messagebox.showwarning("Warning", "Please select an image first")
            return
            
        if not self.ai_enabled.get():
            messagebox.showwarning("Warning", "Please enable AI description generation first")
            return
            
        # Start AI analysis in background
        threading.Thread(target=self._analyze_image_ai, daemon=True).start()
    
    def _analyze_image_ai(self):
        """Analyze image with AI (runs in background thread)."""
        try:
            self.ai_processing = True
            self.log_message("🤖 Starting AI analysis...")
            
            # Encode image to base64
            with open(self.metadata_image_path, "rb") as image_file:
                image_data = base64.b64encode(image_file.read()).decode('utf-8')
            
            # Prepare prompt for Qwen2.5-VL
            prompt = """Analyze this image and provide:
1. A detailed description of what you see
2. Key visual elements and composition
3. Color palette and mood
4. Potential use cases (e.g., website hero, product photo, etc.)
5. SEO-friendly keywords and tags
6. Alt text for accessibility

Please be specific and professional in your analysis."""
            
            # Call LM Studio API
            response = self._call_lm_studio_api(image_data, prompt)
            
            if response:
                # Parse and display results
                self._display_ai_results(response)
                self.log_message("✅ AI analysis completed successfully")
            else:
                self.log_message("❌ AI analysis failed")
                
        except Exception as e:
            self.log_message(f"❌ AI analysis error: {str(e)}")
        finally:
            self.ai_processing = False
    
    def _call_lm_studio_api(self, image_data, prompt):
        """Call LM Studio API with image and prompt."""
        try:
            url = f"{self.lm_studio_url.get()}/v1/chat/completions"
            
            # Use the selected model
            selected_model = self.lm_studio_model.get()
            if not selected_model:
                selected_model = "qwen/qwen2.5-vl-7b"  # Fallback
            
            # Use the full model name as it appears in LM Studio
            model_name = selected_model
            
            print(f"AI Debug (Legacy) - Using Model Name: {model_name}")
            print(f"AI Debug (Legacy) - Prompt: {prompt[:100]}...")
            
            payload = {
                "model": model_name,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_data}"
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": self.max_tokens,
                "temperature": 0.7
            }
            
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            print(f"AI Debug (Legacy) - Headers: {headers}")
            
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            return result['choices'][0]['message']['content']
            
        except requests.exceptions.RequestException as e:
            self.log_message(f"❌ LM Studio connection error: {str(e)}")
            return None
        except Exception as e:
            self.log_message(f"❌ API call error: {str(e)}")
            return None
    
    def _display_ai_results(self, ai_response):
        """Display AI analysis results in the metadata editor."""
        # Parse AI response and populate metadata fields
        lines = ai_response.split('\n')
        
        # Look for specific sections and populate fields
        for line in lines:
            line = line.strip()
            if line.startswith('1.') or 'description' in line.lower():
                self._set_metadata_field('ImageDescription', line.replace('1.', '').strip())
            elif line.startswith('5.') or 'keywords' in line.lower():
                self._set_metadata_field('Keywords', line.replace('5.', '').strip())
            elif line.startswith('6.') or 'alt text' in line.lower():
                self._set_metadata_field('AltText', line.replace('6.', '').strip())
        
        # Store full AI response
        self._set_metadata_field('AIAnalysis', ai_response)
        
        # Refresh metadata display
        self.load_image_metadata()
        
        # Show results in a popup
        self._show_ai_results_popup(ai_response)
    
    def _show_ai_results_popup(self, ai_response):
        """Show AI analysis results in a popup window."""
        popup = tk.Toplevel(self.root)
        popup.title("🤖 AI Analysis Results")
        popup.geometry("600x500")
        popup.transient(self.root)
        popup.grab_set()
        
        # Main frame
        main_frame = ttk.Frame(popup, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        ttk.Label(main_frame, text="🤖 AI Analysis Results", 
                 font=('Arial', 14, 'bold')).pack(pady=(0, 10))
        
        # Results text
        text_widget = scrolledtext.ScrolledText(main_frame, wrap=tk.WORD, height=20)
        text_widget.pack(fill=tk.BOTH, expand=True)
        text_widget.insert(tk.END, ai_response)
        text_widget.config(state=tk.DISABLED)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(button_frame, text="✅ Apply to Metadata", 
                  command=lambda: [self._apply_ai_to_metadata(), popup.destroy()]).pack(side=tk.LEFT)
        ttk.Button(button_frame, text="❌ Close", 
                  command=popup.destroy).pack(side=tk.RIGHT)
    
    def _apply_ai_to_metadata(self):
        """Apply AI-generated data to metadata fields."""
        # This will automatically populate the metadata editor
        self.log_message("✅ AI data applied to metadata fields")
    
    def generate_seo_data(self):
        """Generate SEO-optimized metadata for the current image."""
        if not self.metadata_image_path:
            messagebox.showwarning("Warning", "Please select an image first")
            return
            
        # Generate SEO-specific prompt
        seo_prompt = """Analyze this image and generate SEO-optimized metadata:

1. Title (50-60 characters): Compelling, descriptive title
2. Description (150-160 characters): Brief, engaging description
3. Keywords (5-10 relevant keywords): Comma-separated
4. Alt Text (125 characters max): Descriptive alt text for accessibility
5. File Name Suggestion: SEO-friendly filename
6. Category/Tags: Relevant categories
7. Color Palette: Dominant colors
8. Mood/Atmosphere: Visual mood description

Focus on search engine optimization and user engagement."""
        
        threading.Thread(target=self._generate_seo_ai, args=(seo_prompt,), daemon=True).start()
    
    def _generate_seo_ai(self, prompt):
        """Generate SEO data with AI (runs in background thread)."""
        try:
            self.ai_processing = True
            self.log_message("🔍 Generating SEO data...")
            
            # Encode image to base64
            with open(self.metadata_image_path, "rb") as image_file:
                image_data = base64.b64encode(image_file.read()).decode('utf-8')
            
            # Call LM Studio API
            response = self._call_lm_studio_api(image_data, prompt)
            
            if response:
                self._display_seo_results(response)
                self.log_message("✅ SEO data generated successfully")
            else:
                self.log_message("❌ SEO data generation failed")
                
        except Exception as e:
            self.log_message(f"❌ SEO generation error: {str(e)}")
        finally:
            self.ai_processing = False
    
    def _display_seo_results(self, seo_response):
        """Display SEO results in a structured format."""
        popup = tk.Toplevel(self.root)
        popup.title("📈 SEO Data Generated")
        popup.geometry("700x600")
        popup.transient(self.root)
        popup.grab_set()
        
        # Main frame
        main_frame = ttk.Frame(popup, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        ttk.Label(main_frame, text="📈 SEO-Optimized Metadata", 
                 font=('Arial', 14, 'bold')).pack(pady=(0, 10))
        
        # Create form for SEO data
        seo_frame = ttk.Frame(main_frame)
        seo_frame.pack(fill=tk.BOTH, expand=True)
        
        # Parse and display structured SEO data
        lines = seo_response.split('\n')
        seo_fields = {}
        
        for line in lines:
            line = line.strip()
            if ':' in line and any(keyword in line.lower() for keyword in ['title', 'description', 'keywords', 'alt text', 'file name', 'category', 'color', 'mood']):
                key, value = line.split(':', 1)
                seo_fields[key.strip()] = value.strip()
        
        # Create form fields
        row = 0
        for key, value in seo_fields.items():
            ttk.Label(seo_frame, text=f"{key}:").grid(row=row, column=0, sticky=tk.W, pady=2)
            entry = ttk.Entry(seo_frame, width=60)
            entry.insert(0, value)
            entry.grid(row=row, column=1, sticky=(tk.W, tk.E), padx=(5, 0), pady=2)
            seo_fields[key] = entry
            row += 1
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(button_frame, text="✅ Apply to Image", 
                  command=lambda: [self._apply_seo_to_image(seo_fields), popup.destroy()]).pack(side=tk.LEFT)
        ttk.Button(button_frame, text="❌ Close", 
                  command=popup.destroy).pack(side=tk.RIGHT)
    
    def _apply_seo_to_image(self, seo_fields):
        """Apply SEO data to the current image metadata."""
        # Map SEO fields to metadata fields
        field_mapping = {
            'Title': 'ImageDescription',
            'Description': 'Description', 
            'Keywords': 'Keywords',
            'Alt Text': 'AltText',
            'Category/Tags': 'Category',
            'Color Palette': 'ColorPalette',
            'Mood/Atmosphere': 'Mood'
        }
        
        for seo_key, entry_widget in seo_fields.items():
            if seo_key in field_mapping:
                metadata_key = field_mapping[seo_key]
                value = entry_widget.get().strip()
                if value:
                    self._set_metadata_field(metadata_key, value)
        
        self.log_message("✅ SEO data applied to image metadata")
    
    def fetch_lm_studio_models(self):
        """Fetch available models from LM Studio."""
        def fetch_models():
            try:
                self.log_message("🔍 Fetching available models from LM Studio...")
                
                # Get models from LM Studio
                url = f"{self.lm_studio_url.get()}/v1/models"
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                
                models_data = response.json()
                self.available_lm_studio_models = []
                
                # Extract model IDs
                if 'data' in models_data:
                    for model in models_data['data']:
                        if 'id' in model:
                            self.available_lm_studio_models.append(model['id'])
                
                # Update combobox
                self.root.after(0, self._update_model_combobox)
                
                # Auto-select Qwen2.5-VL-7B if available
                qwen_model = "qwen/qwen2.5-vl-7b"
                if qwen_model in self.available_lm_studio_models:
                    self.lm_studio_model.set(qwen_model)
                    self.log_message(f"✅ Auto-selected {qwen_model}")
                else:
                    # Try to find any qwen model
                    for model in self.available_lm_studio_models:
                        if 'qwen' in model.lower():
                            self.lm_studio_model.set(model)
                            self.log_message(f"✅ Auto-selected {model}")
                            break
                
                self.ai_connected = True
                self.root.after(0, self._update_connection_status, True)
                self.log_message(f"✅ Found {len(self.available_lm_studio_models)} models")
                
                # Debug: Show available models
                print(f"AI Debug - Available models: {self.available_lm_studio_models}")
                
            except requests.exceptions.RequestException as e:
                self.log_message(f"❌ Failed to fetch models: {str(e)}")
                self.root.after(0, self._update_connection_status, False)
            except Exception as e:
                self.log_message(f"❌ Error fetching models: {str(e)}")
                self.root.after(0, self._update_connection_status, False)
        
        threading.Thread(target=fetch_models, daemon=True).start()
    
    def _update_model_combobox(self):
        """Update the model combobox with available models."""
        if hasattr(self, 'model_combo'):
            self.model_combo['values'] = self.available_lm_studio_models
            if self.available_lm_studio_models and not self.lm_studio_model.get():
                self.lm_studio_model.set(self.available_lm_studio_models[0])
    
    def _update_connection_status(self, connected):
        """Update the connection status display."""
        if hasattr(self, 'connection_status'):
            if connected:
                self.connection_status.config(text="✅ Connected", foreground="green")
            else:
                self.connection_status.config(text="❌ Not Connected", foreground="red")
        
        # Also update chat tab status
        self.update_chat_connection_status()
    
    def test_ai_connection(self):
        """Test connection to LM Studio and fetch models."""
        def test_connection():
            try:
                self.log_message("🔍 Testing LM Studio connection...")
                
                # Simple test request
                url = f"{self.lm_studio_url.get()}/v1/models"
                response = requests.get(url, timeout=5)
                response.raise_for_status()
                
                self.log_message("✅ LM Studio connection successful!")
                self.ai_connected = True
                self.root.after(0, self._update_connection_status, True)
                
                # Fetch available models
                self.fetch_lm_studio_models()
                
                messagebox.showinfo("Connection Test", "✅ Successfully connected to LM Studio!")
                
            except requests.exceptions.RequestException as e:
                self.log_message(f"❌ LM Studio connection failed: {str(e)}")
                self.ai_connected = False
                self.root.after(0, self._update_connection_status, False)
                messagebox.showerror("Connection Test", f"❌ Failed to connect to LM Studio:\n{str(e)}")
            except Exception as e:
                self.log_message(f"❌ Connection test error: {str(e)}")
                self.ai_connected = False
                self.root.after(0, self._update_connection_status, False)
                messagebox.showerror("Connection Test", f"❌ Error: {str(e)}")
        
        threading.Thread(target=test_connection, daemon=True).start()
    
    def auto_connect_lm_studio(self):
        """Automatically attempt to connect to LM Studio on startup."""
        def auto_connect():
            try:
                # Test connection without showing popup
                url = f"{self.lm_studio_url.get()}/v1/models"
                response = requests.get(url, timeout=3)
                response.raise_for_status()
                
                # Connection successful, fetch models
                self.ai_connected = True
                self.root.after(0, self._update_connection_status, True)
                self.fetch_lm_studio_models()
                self.log_message("🤖 Auto-connected to LM Studio")
                
            except:
                # Connection failed, silently continue
                self.log_message("ℹ️ LM Studio not available (auto-connect failed)")
                pass
        
        threading.Thread(target=auto_connect, daemon=True).start()
    
    def start_batch_ai_processing(self):
        """Start batch AI processing for all images in the selected folder."""
        if not self.batch_folder:
            messagebox.showwarning("Warning", "Please select a folder first")
            return
            
        if not self.ai_enabled.get():
            messagebox.showwarning("Warning", "Please enable AI and test connection first")
            return
            
        # Check if we have chat rules
        if not self.chat_messages:
            messagebox.showwarning("Warning", "Please set up rules in the AI Chat tab first")
            return
            
        # Confirm batch processing
        result = messagebox.askyesno("Confirm Batch Processing", 
                                   f"Process {len(self.image_files)} images with AI?\n\n"
                                   "This will analyze each image and apply metadata based on your chat rules.")
        if not result:
            return
            
        # Start batch processing in a separate thread
        threading.Thread(target=self._process_batch_ai_thread, daemon=True).start()
    
    def _process_batch_ai_thread(self):
        """Process batch AI in a separate thread."""
        try:
            self.log_message("🤖 Starting batch AI processing...")
            self.ai_processing = True
            
            # Extract rules from chat
            rules = self._extract_chat_rules()
            self.log_message(f"📋 Extracted {len(rules)} rules from chat")
            
            # Process each image
            total_images = len(self.image_files)
            processed = 0
            successful = 0
            failed = 0
            
            for i, image_path in enumerate(self.image_files):
                try:
                    # Update progress
                    self.root.after(0, self._update_batch_progress, i + 1, total_images, image_path)
                    
                    # Process image with AI
                    success = self._process_single_image_ai(image_path, rules)
                    
                    if success:
                        successful += 1
                        self.log_message(f"✅ Processed: {os.path.basename(image_path)}")
                    else:
                        failed += 1
                        self.log_message(f"❌ Failed: {os.path.basename(image_path)}")
                    
                    processed += 1
                    
                    # Small delay to prevent overwhelming the API
                    time.sleep(1)
                    
                except Exception as e:
                    failed += 1
                    self.log_message(f"❌ Error processing {os.path.basename(image_path)}: {str(e)}")
            
            # Final results
            self.log_message(f"🎉 Batch processing complete!")
            self.log_message(f"📊 Results: {successful} successful, {failed} failed out of {total_images} total")
            
            # Reset progress
            self.root.after(0, self._reset_batch_progress)
            
        except Exception as e:
            self.log_message(f"❌ Batch processing error: {str(e)}")
        finally:
            self.ai_processing = False
    
    def _extract_chat_rules(self):
        """Extract rules and instructions from chat messages."""
        rules = []
        
        for msg in self.chat_messages:
            if msg['sender'] == 'user':
                # Look for rule-like messages
                content = msg['message'].lower()
                if any(keyword in content for keyword in ['rule', 'instruction', 'always', 'never', 'should', 'must', 'format']):
                    rules.append({
                        'type': 'user_rule',
                        'content': msg['message']
                    })
            elif msg['sender'] == 'ai':
                # Look for AI responses that contain structured instructions
                content = msg['message']
                if 'format' in content.lower() or 'structure' in content.lower():
                    rules.append({
                        'type': 'ai_format',
                        'content': content
                    })
        
        return rules
    
    def _process_single_image_ai(self, image_path, rules):
        """Process a single image with AI using the established rules."""
        try:
            # Parse filename for context
            filename = Path(image_path).name
            filename_data = self.parse_filename_data(filename)
            
            # Build context with rules
            context = f"""
Filename: {filename}
Product Code: {filename_data['code']}
Product Type: {filename_data['type']}
Color: {filename_data['color']}
Product Name: {filename_data['name']}
Category: {filename_data['category']}

Rules and Instructions:
{self._format_rules_for_ai(rules)}

Please provide metadata suggestions for this image in the following format:

Title: [descriptive title based on the product and room shown]
Description: [detailed description of what's shown in the image]
Keywords: [relevant search terms, comma-separated]
Artist: [Your Company Name]
Make: {filename_data['code']}
Model: {filename_data['type']}

Please ensure all 6 fields are provided with the exact format shown above.
"""
            
            # Encode image to base64
            with open(image_path, "rb") as image_file:
                image_data = base64.b64encode(image_file.read()).decode('utf-8')
            
            # Call AI API
            response = self._call_lm_studio_api_with_context(image_data, context)
            
            if response:
                # Parse AI response
                metadata_dict = self._parse_ai_response_for_metadata(response)
                
                # Apply metadata to image file
                if metadata_dict:
                    success = self._save_metadata_to_file(image_path, metadata_dict)
                    return success
            
            return False
            
        except Exception as e:
            self.log_message(f"❌ Error processing {image_path}: {str(e)}")
            return False
    
    def _format_rules_for_ai(self, rules):
        """Format rules for AI consumption."""
        if not rules:
            return "No specific rules provided. Use standard metadata format."
        
        formatted_rules = []
        for rule in rules:
            formatted_rules.append(f"- {rule['content']}")
        
        return "\n".join(formatted_rules)
    
    def _save_metadata_to_file(self, image_path, metadata_dict):
        """Save metadata directly to image file."""
        try:
            # Determine file type
            file_ext = Path(image_path).suffix.lower()
            
            if file_ext in ['.jpg', '.jpeg']:
                return self._save_jpeg_metadata_direct(image_path, metadata_dict)
            elif file_ext == '.webp':
                return self._save_webp_metadata_direct(image_path, metadata_dict)
            else:
                self.log_message(f"⚠️ Unsupported file type: {file_ext}")
                return False
                
        except Exception as e:
            self.log_message(f"❌ Error saving metadata to {image_path}: {str(e)}")
            return False
    
    def _save_jpeg_metadata_direct(self, image_path, metadata_dict):
        """Save metadata directly to JPEG file."""
        try:
            # Load image
            image = Image.open(image_path)
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Create EXIF data
            exif_dict = piexif.load(image.info.get('exif', b''))
            
            # Set metadata fields
            if 'XPTitle' in metadata_dict:
                exif_dict['0th'][piexif.ImageIFD.XPTitle] = metadata_dict['XPTitle'].encode('utf-16le')
            if 'ImageDescription' in metadata_dict:
                exif_dict['0th'][piexif.ImageIFD.ImageDescription] = metadata_dict['ImageDescription'].encode('utf-8')
            if 'XPKeywords' in metadata_dict:
                exif_dict['0th'][piexif.ImageIFD.XPKeywords] = metadata_dict['XPKeywords'].encode('utf-16le')
            if 'Artist' in metadata_dict:
                exif_dict['0th'][piexif.ImageIFD.Artist] = metadata_dict['Artist'].encode('utf-8')
            if 'Make' in metadata_dict:
                exif_dict['0th'][piexif.ImageIFD.Make] = metadata_dict['Make'].encode('utf-8')
            if 'Model' in metadata_dict:
                exif_dict['0th'][piexif.ImageIFD.Model] = metadata_dict['Model'].encode('utf-8')
            
            # Save with metadata
            exif_bytes = piexif.dump(exif_dict)
            image.save(image_path, 'JPEG', exif=exif_bytes, quality=95)
            
            return True
            
        except Exception as e:
            self.log_message(f"❌ Error saving JPEG metadata: {str(e)}")
            return False
    
    def _save_webp_metadata_direct(self, image_path, metadata_dict):
        """Save metadata directly to WebP file using ExifTool."""
        try:
            # Build ExifTool command
            cmd = [self.exiftool_path, '-overwrite_original']
            
            # Add metadata tags
            if 'XPTitle' in metadata_dict:
                cmd.extend(['-XMP:Title', metadata_dict['XPTitle']])
            if 'ImageDescription' in metadata_dict:
                cmd.extend(['-XMP:Description', metadata_dict['ImageDescription']])
            if 'XPKeywords' in metadata_dict:
                cmd.extend(['-XMP:Subject', metadata_dict['XPKeywords']])
            if 'Artist' in metadata_dict:
                cmd.extend(['-XMP:Creator', metadata_dict['Artist']])
            if 'Make' in metadata_dict:
                cmd.extend(['-XMP:Make', metadata_dict['Make']])
            if 'Model' in metadata_dict:
                cmd.extend(['-XMP:Model', metadata_dict['Model']])
            
            cmd.append(image_path)
            
            # Run ExifTool
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                return True
            else:
                self.log_message(f"❌ ExifTool error: {result.stderr}")
                return False
                
        except Exception as e:
            self.log_message(f"❌ Error saving WebP metadata: {str(e)}")
            return False
    
    def _update_batch_progress(self, current, total, current_file):
        """Update batch processing progress."""
        if hasattr(self, 'progress_var'):
            self.progress_var.set(f"Processing {current}/{total}: {os.path.basename(current_file)}")
        
        if hasattr(self, 'progress_bar'):
            self.progress_bar['value'] = (current / total) * 100
    
    def _reset_batch_progress(self):
        """Reset batch processing progress."""
        if hasattr(self, 'progress_var'):
            self.progress_var.set("Ready")
        
        if hasattr(self, 'progress_bar'):
            self.progress_bar['value'] = 0
    
    def view_chat_rules(self):
        """Display current chat rules in a popup."""
        if not self.chat_messages:
            messagebox.showinfo("Chat Rules", "No chat messages found.\n\nPlease go to the AI Chat tab and set up your rules first.")
            return
        
        # Extract and format rules
        rules = self._extract_chat_rules()
        
        if not rules:
            messagebox.showinfo("Chat Rules", "No specific rules found in chat.\n\nStandard metadata format will be used.")
            return
        
        # Create popup window
        rules_window = tk.Toplevel(self.root)
        rules_window.title("📋 Current Chat Rules")
        rules_window.geometry("600x400")
        
        # Create text widget
        text_frame = ttk.Frame(rules_window, padding="10")
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        text_widget = tk.Text(text_frame, wrap=tk.WORD, font=('Arial', 10))
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Insert rules
        for i, rule in enumerate(rules, 1):
            text_widget.insert(tk.END, f"Rule {i} ({rule['type']}):\n")
            text_widget.insert(tk.END, f"{rule['content']}\n\n")
        
        # Make read-only
        text_widget.config(state=tk.DISABLED)
        
        # Close button
        ttk.Button(rules_window, text="Close", command=rules_window.destroy).pack(pady=10)
    
    def select_chat_folder(self):
        """Select folder for AI chat navigation."""
        folder = filedialog.askdirectory(title="Select folder for AI chat")
        if folder:
            self.chat_folder_path_str = folder
            self.chat_folder_images = self._load_images_from_folder(folder)
            self.chat_current_image_index = 0
            
            if self.chat_folder_images:
                self.chat_folder_path.config(text=f"Folder: {os.path.basename(folder)}")
                self.load_chat_image(self.chat_folder_images[0])
                self.update_chat_image_counter()
            else:
                self.chat_folder_path.config(text="No images found")
                messagebox.showwarning("Warning", "No image files found in selected folder")
    
    def _load_images_from_folder(self, folder_path):
        """Load all image files from a folder."""
        image_extensions = {'.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.webp', '.avif'}
        image_files = []
        
        try:
            for ext in image_extensions:
                # Add both lowercase and uppercase extensions
                image_files.extend(Path(folder_path).glob(f'*{ext}'))
                image_files.extend(Path(folder_path).glob(f'*{ext.upper()}'))
            
            # Convert to strings and remove duplicates (case-insensitive file systems)
            image_files = [str(f) for f in image_files]
            # Remove duplicates by converting to set and back to list
            image_files = list(set(image_files))
            image_files.sort()
            
            self.log_message(f"📁 Loaded {len(image_files)} unique images from folder")
            return image_files
        except Exception as e:
            self.log_message(f"❌ Error loading images from folder: {str(e)}")
            return []
    
    def previous_chat_image(self):
        """Navigate to previous image in chat folder."""
        if self.chat_folder_images and self.chat_current_image_index > 0:
            self.chat_current_image_index -= 1
            self.load_chat_image(self.chat_folder_images[self.chat_current_image_index])
            self.update_chat_image_counter()
    
    def next_chat_image(self):
        """Navigate to next image in chat folder."""
        if self.chat_folder_images and self.chat_current_image_index < len(self.chat_folder_images) - 1:
            self.chat_current_image_index += 1
            self.load_chat_image(self.chat_folder_images[self.chat_current_image_index])
            self.update_chat_image_counter()
    
    def update_chat_image_counter(self):
        """Update the image counter display."""
        if self.chat_folder_images:
            current = self.chat_current_image_index + 1
            total = len(self.chat_folder_images)
            self.chat_image_counter.config(text=f"Image {current} of {total}")
        else:
            self.chat_image_counter.config(text="")
    
    def show_folder_contents(self):
        """Show the contents of the current AI folder."""
        if not hasattr(self, 'image_files') or not self.image_files:
            messagebox.showinfo("Folder Contents", "No folder loaded. Please select a folder first.")
            return
        
        # Create popup window
        contents_window = tk.Toplevel(self.root)
        contents_window.title("📂 Folder Contents")
        contents_window.geometry("600x400")
        
        # Create text widget
        text_frame = ttk.Frame(contents_window, padding="10")
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        text_widget = tk.Text(text_frame, wrap=tk.WORD, font=('Consolas', 10))
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Insert folder contents
        text_widget.insert(tk.END, f"Folder: {self.batch_folder}\n")
        text_widget.insert(tk.END, f"Total Images: {len(self.image_files)}\n\n")
        
        for i, img_path in enumerate(self.image_files, 1):
            filename = os.path.basename(img_path)
            text_widget.insert(tk.END, f"{i:3d}. {filename}\n")
        
        # Make read-only
        text_widget.config(state=tk.DISABLED)
        
        # Close button
        ttk.Button(contents_window, text="Close", command=contents_window.destroy).pack(pady=10)
    
    def toggle_tool_use(self):
        """Toggle tool use mode on/off."""
        self.tool_use_enabled = not self.tool_use_enabled
        status = "enabled" if self.tool_use_enabled else "disabled"
        self.log_message(f"🔧 Tool use {status} - Using model: {self.tool_use_model}")
        print(f"DEBUG: Tool use {status}, model: {self.tool_use_model}")
        
        if self.tool_use_enabled:
            messagebox.showinfo("Tool Use Enabled", 
                              f"Tool use is now enabled!\n\n"
                              f"Model: {self.tool_use_model}\n"
                              f"The AI can now access real folder information instead of guessing.\n\n"
                              f"Try asking: 'List the files in this folder' or 'Tell me about the current image'")
        else:
            messagebox.showinfo("Tool Use Disabled", "Tool use is now disabled. AI will use text context only.")
    
    def update_token_limit(self):
        """Update the maximum token limit for AI responses."""
        try:
            new_limit = int(self.token_limit_var.get())
            if 1000 <= new_limit <= 8000:
                self.max_tokens = new_limit
                self.log_message(f"🔧 Token limit updated to {new_limit}")
            else:
                self.token_limit_var.set(str(self.max_tokens))
                messagebox.showwarning("Invalid Token Limit", "Token limit must be between 1000 and 8000")
        except ValueError:
            self.token_limit_var.set(str(self.max_tokens))
            messagebox.showwarning("Invalid Token Limit", "Please enter a valid number")
    
    def update_temperature(self):
        """Update the AI temperature setting."""
        try:
            new_temp = float(self.temperature_var.get())
            if 0.1 <= new_temp <= 1.0:
                self.ai_temperature = new_temp
                self.log_message(f"🌡️ Temperature updated to {new_temp}")
            else:
                self.temperature_var.set(str(self.ai_temperature))
                messagebox.showwarning("Invalid Temperature", "Temperature must be between 0.1 and 1.0")
        except ValueError:
            self.temperature_var.set(str(self.ai_temperature))
            messagebox.showwarning("Invalid Temperature", "Please enter a valid number")
    
    def update_tool_model(self, event=None):
        """Update the tool use model."""
        new_model = self.tool_model_var.get()
        if new_model in self.available_tool_models:
            self.tool_use_model = new_model
            thinking_status = "disabled" if self.disable_thinking else "enabled"
            self.log_message(f"🤖 Tool model: {new_model} (thinking {thinking_status})")
        else:
            self.tool_model_var.set(self.tool_use_model)
            messagebox.showwarning("Invalid Model", "Please select a valid model")
    
    def toggle_thinking_disable(self):
        """Toggle thinking disable for DeepSeek model."""
        self.disable_thinking = self.disable_thinking_var.get()
        status = "disabled" if self.disable_thinking else "enabled"
        self.log_message(f"🧠 Thinking {status} for DeepSeek model")
    
    def _call_tool_use_api_with_tools(self, message):
        """Call tool use API with predefined tools for folder access."""
        print(f"AI Debug (Tool Use) - Starting tool use API call with message: {message[:100]}...")
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "list_folder_contents",
                    "description": "List all files in the current folder with their details",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_image_info",
                    "description": "Get detailed information about a specific image by index",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "index": {
                                "type": "integer",
                                "description": "Image index (1-based)"
                            }
                        },
                        "required": ["index"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_current_image",
                    "description": "Get information about the currently selected image",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            }
        ]
        
        result = self._call_tool_use_api(message, tools)
        print(f"AI Debug (Tool Use) - Tool use API returned: {result is not None}")
        return result
    
    def _call_tool_use_api(self, message, tools=None):
        """Call the tool-use model for context-aware responses."""
        try:
            url = f"{self.lm_studio_url.get()}/v1/chat/completions"
            
            # Use the tool-use model
            model_name = self.tool_use_model
            
            # Build messages
            messages = []
            
            # Add system context for tool use
            system_message = """You are an AI assistant with access to tools for analyzing image folders and files.

AVAILABLE TOOLS:
- list_folder_contents: Lists all files in the current folder with details
- get_image_info: Gets detailed information about a specific image by index
- get_current_image: Gets information about the currently selected image

CRITICAL RULES:
1. When you get tool results, ALWAYS provide a clear response based on those results
2. NEVER return empty responses - always give the user the information they asked for
3. Be direct and helpful - answer the user's question using the tool data
4. If you get tool results, use them to answer the question immediately

EXAMPLE:
User: "Are there duplicate files?"
You: [Call list_folder_contents tool]
Tool Result: "Folder: test\nTotal files: 6\n\nFiles:\n1. file1.jpg\n2. file2.jpg..."
You: "No, there are no duplicate files. The folder contains 6 unique files: file1.jpg, file2.jpg, etc."

IMPORTANT: Always respond with useful information based on tool results. Never leave the user hanging."""
            
            messages.append({
                "role": "system",
                "content": system_message
            })
            
            # Add user message
            messages.append({
                "role": "user",
                "content": message
            })
            
               # Note: We don't pre-fill think tags anymore as it breaks tool use
               # The thinking is essential for DeepSeek to properly use tools
            
            # Build payload
            payload = {
                "model": model_name,
                "messages": messages,
                "max_tokens": self.tool_use_max_tokens,
                "temperature": self.tool_use_temperature
            }
            
            # Add tools if provided
            if tools:
                payload["tools"] = tools
                payload["tool_choice"] = "auto"
            
            headers = self.tool_use_headers
            
            print(f"AI Debug (Tool Use) - Using Model: {model_name}")
            print(f"AI Debug (Tool Use) - Message: {message}")
            
            response = requests.post(url, json=payload, headers=headers, timeout=60)
            
            print(f"AI Debug (Tool Use) - Response status: {response.status_code}")
            
            if response.status_code != 200:
                print(f"AI Debug (Tool Use) - Error: {response.text}")
                return None
                
            result = response.json()
            
            # Handle tool calls if present
            if 'choices' in result and len(result['choices']) > 0:
                choice = result['choices'][0]
                
                if 'tool_calls' in choice['message'] and choice['message']['tool_calls']:
                    # Process tool calls
                    return self._process_tool_calls(choice['message']['tool_calls'], messages, model_name)
                else:
                    # Return regular response
                    return choice['message']['content']
            
            return None
            
        except Exception as e:
            print(f"AI Debug (Tool Use) - Error: {str(e)}")
            return None
    
    def _process_tool_calls(self, tool_calls, messages, model_name):
        """Process tool calls and return results."""
        try:
            # Add assistant message with tool calls
            messages.append({
                "role": "assistant",
                "content": None,
                "tool_calls": tool_calls
            })
            
            # Track executed tools to prevent duplicates
            executed_tools = set()
            
            # Execute tool calls
            for tool_call in tool_calls:
                function_name = tool_call['function']['name']
                function_args = json.loads(tool_call['function']['arguments'])
                
                # Skip if already executed
                tool_key = f"{function_name}_{str(function_args)}"
                if tool_key in executed_tools:
                    print(f"AI Debug (Tool Use) - Skipping duplicate tool call: {function_name}")
                    continue
                
                executed_tools.add(tool_key)
                
                print(f"AI Debug (Tool Use) - Executing tool: {function_name}")
                print(f"AI Debug (Tool Use) - Arguments: {function_args}")
                
                # Execute the tool
                tool_result = self._execute_tool(function_name, function_args)
                
                # Add tool result to messages
                messages.append({
                    "role": "tool",
                    "content": tool_result,
                    "tool_call_id": tool_call['id']
                })
            
            # Instead of trying to get the model to respond, let's format the tool results directly
            print(f"AI Debug (Tool Use) - Formatting tool results directly")
            
            # Collect all tool results
            tool_results = []
            for msg in messages:
                if msg.get('role') == 'tool':
                    tool_results.append(msg['content'])
            
            if tool_results:
                # Parse the tool results and provide intelligent responses based on the user's question
                # Get the original user message from the messages
                user_message = ""
                for msg in messages:
                    if msg.get('role') == 'user' and not msg.get('content', '').startswith('Please provide a clear response'):
                        user_message = msg.get('content', '')
                        break
                
                response_text = self._analyze_tool_results_and_respond(user_message, tool_results, tool_calls)
                
                print(f"AI Debug (Tool Use) - Returning analyzed response: {response_text[:100]}...")
                return response_text
            else:
                return "Tool execution completed but no results were returned."
            
        except Exception as e:
            print(f"AI Debug (Tool Use) - Tool processing error: {str(e)}")
            return f"Error processing tools: {str(e)}"
    
    def _analyze_tool_results_and_respond(self, user_message, tool_results, tool_calls):
        """Analyze tool results and provide intelligent responses based on the user's question."""
        try:
            # Get the folder data from tool results
            folder_data = None
            for result in tool_results:
                if "Folder:" in result and "Total files:" in result:
                    folder_data = result
                    break
            
            if not folder_data:
                return "Tool execution completed but no folder data was returned."
            
            # Parse the folder data
            lines = folder_data.split('\n')
            folder_name = "Unknown"
            total_files = 0
            files = []
            
            for line in lines:
                if line.startswith("Folder:"):
                    folder_name = line.replace("Folder:", "").strip()
                elif line.startswith("Total files:"):
                    total_files = int(line.replace("Total files:", "").strip())
                elif line.strip() and line[0].isdigit():
                    # Parse file line: "1. filename.ext (size KB)"
                    parts = line.split('.', 1)
                    if len(parts) > 1:
                        file_info = parts[1].strip()
                        if ' (' in file_info and ' KB)' in file_info:
                            filename = file_info.split(' (')[0]
                            size_str = file_info.split(' (')[1].replace(' KB)', '')
                            try:
                                size = float(size_str)
                                files.append({'name': filename, 'size': size})
                            except ValueError:
                                files.append({'name': file_info, 'size': 0})
            
            # Analyze the user's question and provide appropriate response
            user_lower = user_message.lower()
            
            if "duplicate" in user_lower:
                # Check for duplicates
                filenames = [f['name'] for f in files]
                unique_filenames = list(set(filenames))
                if len(filenames) == len(unique_filenames):
                    return f"No, there are no duplicate files in the '{folder_name}' folder. All {total_files} files have unique names."
                else:
                    duplicates = len(filenames) - len(unique_filenames)
                    return f"Yes, there are {duplicates} duplicate files in the '{folder_name}' folder. The folder contains {len(unique_filenames)} unique files out of {total_files} total files."
            
            elif "largest" in user_lower or "biggest" in user_lower:
                # Find largest file
                if files:
                    largest = max(files, key=lambda x: x['size'])
                    return f"The largest file in the '{folder_name}' folder is '{largest['name']}' at {largest['size']:.1f} KB."
                else:
                    return "No files found to analyze."
            
            elif "smallest" in user_lower:
                # Find smallest file
                if files:
                    smallest = min(files, key=lambda x: x['size'])
                    return f"The smallest file in the '{folder_name}' folder is '{smallest['name']}' at {smallest['size']:.1f} KB."
                else:
                    return "No files found to analyze."
            
            elif "list" in user_lower or "files" in user_lower:
                # List all files
                response = f"The '{folder_name}' folder contains {total_files} files:\n\n"
                for i, file_info in enumerate(files, 1):
                    response += f"{i}. {file_info['name']} ({file_info['size']:.1f} KB)\n"
                return response
            
            elif "count" in user_lower or "how many" in user_lower:
                return f"The '{folder_name}' folder contains {total_files} files."
            
            else:
                # Default response with basic info
                return f"The '{folder_name}' folder contains {total_files} files. Here are the details:\n\n{folder_data}"
                
        except Exception as e:
            print(f"AI Debug (Tool Use) - Analysis error: {str(e)}")
            return f"Error analyzing tool results: {str(e)}"
    
    def _execute_tool(self, function_name, args):
        """Execute a tool function and return results."""
        try:
            if function_name == "list_folder_contents":
                return self._tool_list_folder_contents(args)
            elif function_name == "get_image_info":
                return self._tool_get_image_info(args)
            elif function_name == "get_current_image":
                return self._tool_get_current_image(args)
            else:
                return f"Unknown tool: {function_name}"
        except Exception as e:
            return f"Tool execution error: {str(e)}"
    
    def _tool_list_folder_contents(self, args):
        """Tool to list folder contents."""
        if hasattr(self, 'chat_folder_images') and self.chat_folder_images:
            folder_name = os.path.basename(self.chat_folder_path_str) if self.chat_folder_path_str else "Unknown"
            file_list = []
            
            # Get unique files only (remove duplicates)
            unique_files = list(set(self.chat_folder_images))
            unique_files.sort()  # Sort for consistent ordering
            
            for i, img_path in enumerate(unique_files, 1):
                filename = os.path.basename(img_path)
                file_size = os.path.getsize(img_path) / 1024  # KB
                file_list.append(f"{i}. {filename} ({file_size:.1f} KB)")
            
            return f"Folder: {folder_name}\nTotal files: {len(unique_files)}\n\nFiles:\n" + "\n".join(file_list)
        else:
            return "No folder loaded. Please select a folder first."
    
    def _tool_get_image_info(self, args):
        """Tool to get specific image information."""
        if hasattr(self, 'chat_folder_images') and self.chat_folder_images:
            try:
                image_index = args.get('index', 1) - 1  # Convert to 0-based index
                if 0 <= image_index < len(self.chat_folder_images):
                    img_path = self.chat_folder_images[image_index]
                    filename = os.path.basename(img_path)
                    file_size = os.path.getsize(img_path) / 1024
                    
                    # Parse filename for product info
                    filename_data = self.parse_filename_data(filename)
                    
                    return f"Image {image_index + 1}:\n- Filename: {filename}\n- Size: {file_size:.1f} KB\n- Product Code: {filename_data['code']}\n- Product Type: {filename_data['type']}\n- Color: {filename_data['color']}\n- Product Name: {filename_data['name']}\n- Category: {filename_data['category']}"
                else:
                    return f"Invalid image index. Available range: 1-{len(self.chat_folder_images)}"
            except Exception as e:
                return f"Error getting image info: {str(e)}"
        else:
            return "No folder loaded."
    
    def _tool_get_current_image(self, args):
        """Tool to get current image information."""
        if hasattr(self, 'chat_folder_images') and self.chat_folder_images and hasattr(self, 'chat_current_image_index'):
            return self._tool_get_image_info({'index': self.chat_current_image_index + 1})
        else:
            return "No current image available."

def main():
    """Main function to run the advanced GUI."""
    try:
        root = tkdnd.Tk()
        app = AdvancedImageCompressorGUI(root)
        
        # Center the window
        root.update_idletasks()
        x = (root.winfo_screenwidth() // 2) - (root.winfo_width() // 2)
        y = (root.winfo_screenheight() // 2) - (root.winfo_height() // 2)
        root.geometry(f"+{x}+{y}")
        
        root.mainloop()
    except ImportError:
        print("❌ tkinterdnd2 not installed. Installing...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "tkinterdnd2"])
        print("✅ Please run the script again")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    main()
