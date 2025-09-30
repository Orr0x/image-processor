# Automated Batch Processing System - Implementation Plan

## Overview
Create a fully automated batch processing system that combines folder structure analysis with image analysis to generate intelligent metadata for all files in a folder.

## Core Workflow
1. **Load Folder** → User selects folder with images
2. **Set Rules** → User defines metadata generation rules
3. **Analyze Structure** → Tool use model analyzes folder hierarchy
4. **Process Images** → Vision model analyzes each image with full context
5. **Apply Rules** → Combine folder structure + image analysis
6. **Save Metadata** → Automatically save to all files

## Key Features

### 1. Rule-Based Metadata Generation
- **Title**: Combine parent folder + image description
- **Make**: Grandparent folder name
- **Model**: Parent folder name  
- **Description**: AI vision analysis with folder context
- **Keywords**: Extract from folder names + image content
- **Artist**: Configurable (e.g., "EGGER" or folder-based)

### 2. Dual AI Model Integration
- **Tool Use Model**: Analyzes folder structure, file patterns, relationships
- **Vision Model**: Analyzes image content with full conversation context
- **Context Sharing**: Vision model sees all folder analysis from tool use model

### 3. Automated Processing
- **One-Click Operation**: Load folder → Set rules → Click "Start Batch"
- **Progress Tracking**: Real-time progress updates
- **Error Handling**: Continue processing even if individual files fail
- **Backup Safety**: Original files preserved

## Implementation Components

### UI Components (AI Chat Tab)
```python
# Automated Batch Processing section
batch_frame = ttk.LabelFrame(chat_container, text="🚀 Automated Batch Processing", padding="10")

# Rules configuration text area
self.batch_rules_text = scrolledtext.ScrolledText(batch_frame, wrap=tk.WORD, height=4)

# Default rules template
default_rules = """Use folder structure for metadata:
- Title: Combine parent folder + file description
- Make: Grandparent folder name
- Model: Parent folder name
- Description: AI vision analysis with folder context
- Keywords: Extract from folder names + image content"""

# Control buttons
ttk.Button(batch_buttons, text="🚀 Start Automated Batch", command=self.start_automated_batch)
ttk.Button(batch_buttons, text="📊 Preview Rules", command=self.preview_batch_rules)
```

### Core Methods

#### `start_automated_batch()`
- Validates folder is loaded
- Parses user rules from text area
- Starts background thread for processing
- Updates UI with progress

#### `_automated_batch_thread()`
**Phase 1: Folder Structure Analysis**
- Use tool use model to analyze folder hierarchy
- Extract parent/grandparent folder names
- Identify file patterns and relationships
- Store context in conversation history

**Phase 2: Image Processing**
- For each image in folder:
  - Load image and convert to base64
  - Call vision model with full conversation context
  - Apply folder structure rules
  - Generate structured metadata

**Phase 3: Save Metadata**
- Apply generated metadata to each file
- Use existing JPEG/WebP metadata saving methods
- Log success/failure for each file

#### `_parse_folder_structure_rules(rules_text)`
- Parse user-defined rules from text area
- Extract patterns like "Make: Grandparent folder name"
- Create mapping dictionary for rule application
- Handle complex rules with multiple folder levels

#### `_process_image_with_context(image_path, folder_context, rules)`
- Call vision model with conversation history
- Include folder structure context in prompt
- Apply folder-based rules to metadata
- Return structured metadata object

#### `_apply_folder_rules_to_metadata(metadata, image_path, rules)`
- Extract parent/grandparent folder names from path
- Apply rules to metadata fields
- Handle special cases and edge cases
- Validate and clean metadata values

### Enhanced Vision Model Integration

#### Update `_call_lm_studio_api_with_context()`
```python
# Add conversation history for context (last 10 messages)
if hasattr(self, 'chat_messages') and self.chat_messages:
    recent_messages = self.chat_messages[-10:]
    for msg in recent_messages:
        if msg['sender'] == 'user':
            messages.append({"role": "user", "content": msg['message']})
        elif msg['sender'] == 'ai':
            messages.append({"role": "assistant", "content": msg['message']})
```

#### Enhanced System Prompt
```python
system_prompt = """You are an expert at analyzing interior design images and creating SEO-optimized metadata. 

You have access to:
1. The current image content (visual analysis)
2. Full conversation history (folder structure, file patterns, relationships)
3. Folder hierarchy context (parent/grandparent folder names)

Use this combined context to create intelligent metadata that combines:
- Visual analysis of the image
- Folder structure information
- File naming patterns
- Product relationships

Always provide structured responses for metadata fields."""
```

## Example Usage Scenarios

### Scenario 1: EGGER Product Images
```
Folder: /EGGER_iMAGES/rooms/jpg/
Rules: 
- Make: "EGGER" (from grandparent)
- Model: "rooms" (from parent)
- Title: "EGGER rooms - [image description]"
- Description: AI vision analysis + folder context
```

### Scenario 2: Kitchen Design Series
```
Folder: /Designs/Kitchen/Modern/
Rules:
- Make: "Designs" (grandparent)
- Model: "Kitchen" (parent)  
- Title: "Modern Kitchen - [specific design description]"
- Keywords: "kitchen, modern, [extracted from image]"
```

## Technical Implementation Details

### File Path Analysis
```python
def extract_folder_structure(image_path):
    path_parts = Path(image_path).parts
    return {
        'filename': Path(image_path).stem,
        'parent_folder': path_parts[-2] if len(path_parts) > 1 else '',
        'grandparent_folder': path_parts[-3] if len(path_parts) > 2 else '',
        'full_path': str(image_path)
    }
```

### Rule Parsing
```python
def parse_rules(rules_text):
    rules = {}
    for line in rules_text.split('\n'):
        if ':' in line and line.strip():
            field, rule = line.split(':', 1)
            rules[field.strip()] = rule.strip()
    return rules
```

### Progress Tracking
```python
def update_batch_progress(current, total, filename):
    progress = f"Processing {current}/{total}: {Path(filename).name}"
    self.batch_progress_label.config(text=progress)
    self.root.update()
```

## Error Handling
- Continue processing if individual files fail
- Log errors to chat history
- Provide detailed error messages
- Allow user to retry failed files

## Future Enhancements
- Save/load rule templates
- Batch processing presets
- Advanced folder pattern matching
- Metadata validation and preview
- Export processing reports

## Files to Modify
1. `image_compressor_gui_advanced.py` - Main implementation
2. Add batch processing UI to AI Chat tab
3. Enhance vision model with conversation history
4. Add rule parsing and application logic
5. Integrate with existing metadata saving methods

## Testing Strategy
1. Test with simple folder structure
2. Test with complex nested folders
3. Test rule parsing with various formats
4. Test error handling with invalid files
5. Test progress tracking and UI updates
