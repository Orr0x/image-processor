# Advanced Image Metadata Processor

A comprehensive Python application for processing and enhancing image metadata using AI-powered analysis and automated batch processing.

## Features

### 🖼️ Image Processing
- **Compression**: Advanced image compression with quality control
- **Format Support**: JPEG, WebP, PNG, TIFF, BMP, AVIF
- **Metadata Management**: Full EXIF, IPTC, and XMP support
- **Single File**: Process individual images for testing
- **Batch Processing**: Process entire folders automatically

### 🤖 AI-Powered Analysis
- **Dual AI Models**: 
  - **Vision Model** (Qwen2.5-VL-7B): Image content analysis
  - **Tool Use Model** (DeepSeek): Folder structure analysis
- **Context Sharing**: Vision model sees folder analysis from tool use model
- **Smart Metadata**: Combines visual analysis with folder structure
- **Conversation Memory**: Maintains context across interactions

### 🚀 Automated Batch Processing
- **Rule-Based Generation**: Define custom metadata rules
- **Folder Structure Analysis**: Extract parent/grandparent folder names
- **One-Click Processing**: Automate entire folder processing
- **Progress Tracking**: Real-time status updates
- **Template System**: Save and load processing rules

### 📝 Metadata Management
- **Standard Fields**: Title, Description, Keywords, Artist, Make, Model
- **Format Support**: JPEG (EXIF) and WebP (XMP) metadata
- **Validation**: Verify metadata before and after saving
- **Simple Interface**: Dedicated tab for manual metadata entry

## Installation

### Prerequisites
- Python 3.8 or higher
- LM Studio running locally (for AI features)

### Setup
1. Clone the repository:
```bash
git clone https://github.com/Orr0x/image-processor.git
cd image-processor
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Install ExifTool:
   - Download from [ExifTool website](https://exiftool.org/)
   - Extract to `./exiftool/` directory
   - Or use the provided `install_exiftool.bat` script

4. Start LM Studio:
   - Load Qwen2.5-VL-7B vision model
   - Load DeepSeek tool use model
   - Ensure API is running on `http://localhost:1234`

5. Run the application:
```bash
python advanced_image_processor.py
```

## Usage

### Basic Image Processing
1. **Load Images**: Use "Select Folder" or "Single File" options
2. **Compress**: Adjust quality settings and process
3. **Preview**: Compare original vs compressed images

### AI-Powered Metadata
1. **Connect AI**: Enter LM Studio URL and select models
2. **Analyze Image**: Use "Send with Current Image" for analysis
3. **Apply Metadata**: Use quick action buttons to apply AI results

### Automated Batch Processing
1. **Load Folder**: Select folder containing images
2. **Set Rules**: Define metadata generation rules in AI Chat tab
3. **Start Batch**: Click "Start Automated Batch" button
4. **Monitor Progress**: Watch real-time processing status

### Example Rules
```
Title: [parent_folder] - [ai_description]
Make: [grandparent_folder]
Model: [parent_folder]
Description: [ai_vision_analysis]
Keywords: [folder_keywords], [ai_keywords]
Artist: [Your Company Name]
```

## Configuration

### AI Models
- **Vision Model**: `qwen/qwen2.5-vl-7b` (for image analysis)
- **Tool Use Model**: `deepseek/deepseek-r1-0528-qwen3-8b` (for folder analysis)
- **Settings**: Adjustable in AI Chat tab

### Metadata Fields
- **JPEG**: Uses EXIF tags (XPTitle, ImageDescription, XPKeywords, etc.)
- **WebP**: Uses XMP tags (Title, Description, Subject, etc.)
- **Encoding**: UTF-8 for most fields, UTF-16LE for Windows-specific fields

## File Structure
```
advanced-image-processor/
├── advanced_image_processor.py       # Main application
├── requirements.txt                  # Python dependencies
├── install_exiftool.bat             # ExifTool installation script
├── exiftool/                        # ExifTool executable and dependencies
├── BATCH_PROCESSING_PLAN.md         # Implementation documentation
├── BATCH_PROCESSING_IMPLEMENTATION.py # Code additions
└── README.md                        # This file
```

## Development

### Adding New Features
1. Review `BATCH_PROCESSING_PLAN.md` for architecture overview
2. Check `BATCH_PROCESSING_IMPLEMENTATION.py` for code examples
3. Follow existing patterns for UI and AI integration

### AI Integration
- Vision model handles image analysis and metadata generation
- Tool use model handles folder structure analysis
- Both models share conversation context for intelligent processing

## Troubleshooting

### Common Issues
1. **ExifTool not found**: Ensure ExifTool is in `./exiftool/` directory
2. **AI connection failed**: Check LM Studio is running and accessible
3. **Metadata not saving**: Verify file permissions and format support
4. **Batch processing errors**: Check folder structure and image formats

### Debug Mode
- Enable debug logging in Processing Log tab
- Check console output for detailed error messages
- Use "Test AI Connection" to verify API connectivity

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- **LM Studio** for AI model hosting
- **ExifTool** for metadata processing
- **Qwen2.5-VL-7B** for vision analysis
- **DeepSeek** for tool use capabilities