# Automated Batch Processing Implementation
# This file contains all the code that needs to be added to image_compressor_gui_advanced.py

"""
================================================================================
SECTION 1: Add to setup_ai_chat_tab() method - INSERT BEFORE LINE 4262
================================================================================
"""

# Automated Batch Processing section (add after Quick Actions)
automated_batch_processing_section = """
        # Automated Batch Processing section
        batch_frame = ttk.LabelFrame(chat_container, text="🚀 Automated Batch Processing", padding="10")
        batch_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Instructions
        instructions_label = ttk.Label(batch_frame, 
                                       text="Define rules for automated metadata generation across all images in folder:",
                                       font=('Arial', 9, 'bold'))
        instructions_label.pack(anchor=tk.W, pady=(0, 5))
        
        # Rules configuration
        rules_text_label = ttk.Label(batch_frame, text="📋 Processing Rules:")
        rules_text_label.pack(anchor=tk.W, pady=(0, 5))
        
        self.batch_rules_text = scrolledtext.ScrolledText(batch_frame, wrap=tk.WORD, height=6,
                                                          font=('Consolas', 9))
        self.batch_rules_text.pack(fill=tk.X, pady=(0, 10))
        
        # Default rules template
        default_rules = '''Title: [parent_folder] - [ai_description]
Make: [grandparent_folder]
Model: [parent_folder]
Description: [ai_vision_analysis]
Keywords: [folder_keywords], [ai_keywords]
Artist: [Your Company Name]

Instructions for AI:
- Analyze folder structure first using tool use
- For each image, combine folder context with visual analysis
- Extract product codes from filenames (e.g., F032_ST78)
- Be specific and descriptive in image descriptions'''
        
        self.batch_rules_text.insert("1.0", default_rules)
        
        # Batch processing buttons
        batch_buttons = ttk.Frame(batch_frame)
        batch_buttons.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Button(batch_buttons, text="🚀 Start Automated Batch", 
                  command=self.start_automated_batch).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(batch_buttons, text="📊 Preview Rules", 
                  command=self.preview_batch_rules).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(batch_buttons, text="💾 Save Rules Template", 
                  command=self.save_rules_template).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(batch_buttons, text="📂 Load Rules Template", 
                  command=self.load_rules_template).pack(side=tk.LEFT, padx=(0, 5))
        
        # Progress display
        self.batch_progress_label = ttk.Label(batch_frame, text="", foreground="blue", font=('Arial', 9))
        self.batch_progress_label.pack(anchor=tk.W, pady=(10, 0))
        
        self.batch_status_text = scrolledtext.ScrolledText(batch_frame, wrap=tk.WORD, height=4,
                                                           font=('Consolas', 8), state=tk.DISABLED)
        self.batch_status_text.pack(fill=tk.X, pady=(5, 0))
"""

"""
================================================================================
SECTION 2: Enhanced Vision Model with Conversation History
UPDATE _call_lm_studio_api_with_context() method around line 4685
================================================================================
"""

enhanced_vision_model_context = """
            # Add system context with enhanced instructions
            messages.append({
                "role": "system",
                "content": '''You are an expert at analyzing interior design images and creating SEO-optimized metadata. 

You have access to:
1. The current image content (visual analysis)
2. Full conversation history (folder structure, file patterns, relationships)
3. Folder hierarchy context (parent/grandparent folder names)
4. Product codes from filenames

Use this combined context to create intelligent metadata that combines:
- Visual analysis of the image content
- Folder structure information from previous tool use analysis
- File naming patterns and product codes
- Relationships between images in the folder

Always provide structured responses with these exact field names:
- Title: Brief, descriptive title
- Make: Manufacturer/brand name
- Model: Product model/series  
- Description: Detailed description of the image
- Keywords: Comma-separated relevant keywords
- Artist: Creator/photographer name

Be specific, accurate, and SEO-friendly.'''
            })
            
            # Add conversation history for context (last 10 messages)
            if hasattr(self, 'chat_messages') and self.chat_messages:
                recent_messages = self.chat_messages[-10:]  # Last 10 messages for context
                for msg in recent_messages:
                    if msg['sender'] == 'user':
                        # Add text-only messages (skip images to avoid format conflicts)
                        messages.append({
                            "role": "user", 
                            "content": msg['message']
                        })
                    elif msg['sender'] == 'ai':
                        messages.append({
                            "role": "assistant", 
                            "content": msg['message']
                        })
            
            # Add current request with image (this comes after conversation history)
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
"""

"""
================================================================================
SECTION 3: Batch Processing Methods
ADD THESE METHODS TO THE CLASS (around line 6568, before def main())
================================================================================
"""

batch_processing_methods = """
    def start_automated_batch(self):
        '''Start automated batch processing of all images in folder.'''
        # Validate folder is loaded
        if not hasattr(self, 'chat_folder_images') or not self.chat_folder_images:
            messagebox.showwarning("No Folder", "Please select a folder first using 'Select Folder' button.")
            return
        
        # Get rules from text area
        rules_text = self.batch_rules_text.get("1.0", tk.END).strip()
        if not rules_text:
            messagebox.showwarning("No Rules", "Please define processing rules first.")
            return
        
        # Confirm with user
        folder_path = Path(self.chat_folder_images[0]).parent
        num_images = len(self.chat_folder_images)
        
        confirm = messagebox.askyesno(
            "Start Batch Processing",
            f"Process {num_images} images in:\\n{folder_path}\\n\\nThis will:\\n" +
            f"1. Analyze folder structure\\n2. Process each image with AI\\n3. Generate and save metadata\\n\\n" +
            f"Continue?"
        )
        
        if not confirm:
            return
        
        # Start processing thread
        self.add_chat_message("system", f"🚀 Starting automated batch processing for {num_images} images...")
        self.log_message(f"🚀 Starting automated batch processing for {num_images} images")
        
        thread = threading.Thread(target=self._automated_batch_thread, 
                                 args=(rules_text,), daemon=True)
        thread.start()
    
    def _automated_batch_thread(self, rules_text):
        '''Background thread for automated batch processing.'''
        try:
            # Parse rules
            rules = self._parse_batch_rules(rules_text)
            folder_path = Path(self.chat_folder_images[0]).parent
            
            # Phase 1: Analyze folder structure with tool use model
            self._update_batch_status("Phase 1: Analyzing folder structure...")
            self.add_chat_message("system", "📊 Analyzing folder structure with tool use model...")
            
            # Enable tool use temporarily if not already enabled
            original_tool_use = self.tool_use_enabled
            if not self.tool_use_enabled:
                self.tool_use_enabled = True
            
            # Ask tool use model to analyze folder
            folder_analysis_prompt = f'''Analyze the folder structure and files in {folder_path}.
            
            Provide:
            1. Parent folder name and its meaning
            2. Grandparent folder name and its meaning
            3. File naming patterns
            4. Any product codes or identifiers in filenames
            5. Relationships between files
            6. Common themes or categories
            
            This context will be used to generate metadata for all images.'''
            
            # Call tool use API
            folder_analysis = self._call_tool_use_api_with_tools(folder_analysis_prompt)
            
            if folder_analysis:
                self.add_chat_message("ai", folder_analysis)
                self.log_message("✅ Folder structure analysis complete")
            
            # Restore original tool use setting
            self.tool_use_enabled = original_tool_use
            
            # Phase 2: Process each image
            self._update_batch_status(f"Phase 2: Processing {len(self.chat_folder_images)} images...")
            
            success_count = 0
            error_count = 0
            
            for idx, image_path in enumerate(self.chat_folder_images, 1):
                try:
                    # Update progress
                    filename = Path(image_path).name
                    self._update_batch_progress(idx, len(self.chat_folder_images), filename)
                    
                    # Process single image
                    metadata = self._process_image_with_batch_context(image_path, rules)
                    
                    if metadata:
                        # Save metadata to file
                        success = self._save_metadata_for_batch(image_path, metadata)
                        
                        if success:
                            success_count += 1
                            self._log_batch_status(f"✅ {filename}: Saved successfully")
                        else:
                            error_count += 1
                            self._log_batch_status(f"❌ {filename}: Failed to save")
                    else:
                        error_count += 1
                        self._log_batch_status(f"❌ {filename}: Failed to generate metadata")
                
                except Exception as e:
                    error_count += 1
                    self._log_batch_status(f"❌ {Path(image_path).name}: Error - {str(e)}")
            
            # Phase 3: Complete
            self._update_batch_status(f"✅ Complete! Success: {success_count}, Errors: {error_count}")
            self.add_chat_message("system", f"🎉 Batch processing complete!\\n✅ Success: {success_count}\\n❌ Errors: {error_count}")
            self.log_message(f"✅ Batch processing complete - Success: {success_count}, Errors: {error_count}")
            
        except Exception as e:
            self._update_batch_status(f"❌ Error: {str(e)}")
            self.add_chat_message("system", f"❌ Batch processing error: {str(e)}")
            self.log_message(f"❌ Batch processing error: {str(e)}")
    
    def _parse_batch_rules(self, rules_text):
        '''Parse batch processing rules from text.'''
        rules = {}
        instructions = []
        
        for line in rules_text.split('\\n'):
            line = line.strip()
            if not line:
                continue
            
            if ':' in line:
                # Check if it's a metadata field or instruction
                parts = line.split(':', 1)
                field = parts[0].strip()
                value = parts[1].strip()
                
                if field in ['Title', 'Make', 'Model', 'Description', 'Keywords', 'Artist']:
                    rules[field] = value
                elif field == 'Instructions for AI':
                    continue
                else:
                    instructions.append(line)
            elif line.startswith('-'):
                instructions.append(line)
        
        rules['instructions'] = '\\n'.join(instructions)
        return rules
    
    def _process_image_with_batch_context(self, image_path, rules):
        '''Process a single image with full batch context.'''
        try:
            # Extract folder structure
            path_parts = Path(image_path).parts
            parent_folder = path_parts[-2] if len(path_parts) > 1 else ''
            grandparent_folder = path_parts[-3] if len(path_parts) > 2 else ''
            filename = Path(image_path).stem
            
            # Load and encode image
            with open(image_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')
            
            # Create enhanced prompt with folder context and rules
            prompt = f'''Analyze this image and generate metadata following the rules below.

**Image Context:**
- Filename: {filename}
- Parent Folder: {parent_folder}
- Grandparent Folder: {grandparent_folder}
- Full Path: {image_path}

**Metadata Rules:**
{self._format_rules_for_prompt(rules, parent_folder, grandparent_folder, filename)}

**Additional Instructions:**
{rules.get('instructions', '')}

Please analyze the image and provide metadata in this exact format:
Title: [your title here]
Make: [make/brand here]
Model: [model/series here]
Description: [detailed description here]
Keywords: [comma-separated keywords here]
Artist: [artist name here]
'''
            
            # Call vision model with full conversation context
            response = self._call_lm_studio_api_with_context(image_data, prompt)
            
            if response:
                # Parse response into metadata
                metadata = self._parse_ai_response_for_metadata(response)
                return metadata
            
            return None
            
        except Exception as e:
            self.log_message(f"❌ Error processing {Path(image_path).name}: {str(e)}")
            return None
    
    def _format_rules_for_prompt(self, rules, parent_folder, grandparent_folder, filename):
        '''Format rules with actual folder values for prompt.'''
        formatted_rules = []
        
        for field, rule in rules.items():
            if field == 'instructions':
                continue
            
            # Replace placeholders with actual values
            rule = rule.replace('[parent_folder]', parent_folder)
            rule = rule.replace('[grandparent_folder]', grandparent_folder)
            rule = rule.replace('[filename]', filename)
            
            formatted_rules.append(f"{field}: {rule}")
        
        return '\\n'.join(formatted_rules)
    
    def _save_metadata_for_batch(self, image_path, metadata):
        '''Save metadata to image file.'''
        try:
            # Use existing metadata saving methods
            file_ext = Path(image_path).suffix.lower()
            
            if file_ext in ['.jpg', '.jpeg']:
                return self._save_jpeg_metadata(image_path, metadata)
            elif file_ext == '.webp':
                return self._save_webp_metadata(image_path, metadata)
            else:
                self.log_message(f"⚠️ Unsupported format for {Path(image_path).name}")
                return False
        
        except Exception as e:
            self.log_message(f"❌ Error saving metadata for {Path(image_path).name}: {str(e)}")
            return False
    
    def _update_batch_progress(self, current, total, filename):
        '''Update batch progress display.'''
        def update():
            progress_text = f"Processing {current}/{total}: {filename}"
            self.batch_progress_label.config(text=progress_text)
        
        self.root.after(0, update)
    
    def _update_batch_status(self, message):
        '''Update batch status display.'''
        def update():
            self.batch_progress_label.config(text=message)
        
        self.root.after(0, update)
    
    def _log_batch_status(self, message):
        '''Log message to batch status text area.'''
        def update():
            self.batch_status_text.config(state=tk.NORMAL)
            self.batch_status_text.insert(tk.END, f"{message}\\n")
            self.batch_status_text.see(tk.END)
            self.batch_status_text.config(state=tk.DISABLED)
        
        self.root.after(0, update)
    
    def preview_batch_rules(self):
        '''Preview how rules will be applied to images.'''
        if not hasattr(self, 'chat_folder_images') or not self.chat_folder_images:
            messagebox.showinfo("Preview Rules", "Please select a folder first.")
            return
        
        # Get first image as example
        example_path = self.chat_folder_images[0]
        path_parts = Path(example_path).parts
        parent_folder = path_parts[-2] if len(path_parts) > 1 else ''
        grandparent_folder = path_parts[-3] if len(path_parts) > 2 else ''
        filename = Path(example_path).stem
        
        # Parse rules
        rules_text = self.batch_rules_text.get("1.0", tk.END).strip()
        rules = self._parse_batch_rules(rules_text)
        
        # Format preview
        preview = f'''Rule Preview (using first image as example):

Example Image: {filename}
Parent Folder: {parent_folder}
Grandparent Folder: {grandparent_folder}

Metadata Generation:
'''
        
        for field, rule in rules.items():
            if field == 'instructions':
                continue
            
            # Replace placeholders
            example_value = rule.replace('[parent_folder]', parent_folder)
            example_value = example_value.replace('[grandparent_folder]', grandparent_folder)
            example_value = example_value.replace('[filename]', filename)
            
            preview += f"\\n{field}: {example_value}"
        
        preview += f"\\n\\nAI Instructions:\\n{rules.get('instructions', 'None')}"
        
        # Show preview dialog
        messagebox.showinfo("Rules Preview", preview)
    
    def save_rules_template(self):
        '''Save current rules as a template.'''
        rules_text = self.batch_rules_text.get("1.0", tk.END).strip()
        
        if not rules_text:
            messagebox.showwarning("Save Template", "No rules to save.")
            return
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
            title="Save Rules Template"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(rules_text)
                messagebox.showinfo("Success", f"Rules template saved to:\\n{file_path}")
                self.log_message(f"✅ Rules template saved to {file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save template:\\n{str(e)}")
    
    def load_rules_template(self):
        '''Load rules from a template file.'''
        file_path = filedialog.askopenfilename(
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
            title="Load Rules Template"
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    rules_text = f.read()
                
                # Clear current rules and insert new ones
                self.batch_rules_text.delete("1.0", tk.END)
                self.batch_rules_text.insert("1.0", rules_text)
                
                messagebox.showinfo("Success", f"Rules template loaded from:\\n{file_path}")
                self.log_message(f"✅ Rules template loaded from {file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load template:\\n{str(e)}")
"""

print("================================================================================")
print("AUTOMATED BATCH PROCESSING IMPLEMENTATION CODE")
print("================================================================================")
print()
print("This file contains all the code that needs to be added to the main application.")
print()
print("SECTION 1: UI Components for AI Chat Tab")
print("SECTION 2: Enhanced Vision Model with Conversation History")
print("SECTION 3: Batch Processing Methods")
print()
print("Review this code and confirm before applying the changes to the main file.")
print("================================================================================")

