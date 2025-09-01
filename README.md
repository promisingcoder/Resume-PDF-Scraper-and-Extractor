# Resume PDF Scraper and Extractor

🚀 **Successfully processed 3,623+ developer resumes!**

An AI-powered tool that combines web automation with intelligent text extraction to process developer resumes at scale.

## Features

- **Smart Web Scraping**: Uses Playwright to navigate SearXNG search results with automatic scrolling
- **Intelligent PDF Discovery**: Finds PDFs via direct links, content-type checks, and on-page analysis
- **AI-Powered Extraction**: Leverages OpenAI GPT models to structure resume data into clean JSON
- **Robust Processing**: Handles timeouts, retries, and fallback extraction methods
- **Batch Configuration**: Process multiple search queries from config files
- **Comprehensive Output**: Extracts names, emails, GitHub profiles, education, and detailed work experiences

## Prerequisites

- **Python 3.10+**
- **OpenAI API key** - Set as environment variable `OPENAI_API_KEY`
- **Playwright browser binaries** - Installed automatically on first setup

## Installation

```powershell
# Clone and setup
git clone <repository-url>
cd scraping_final

# Create virtual environment
python -m venv .venv
. .venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
python -m playwright install chromium

# Set OpenAI API key
$env:OPENAI_API_KEY = "sk-your-api-key-here"
```

## Usage

### Single Query
```powershell
# Search for specific developer type
python -m scraper.main --query '"resume" filetype:pdf "javascript developer" "@gmail.com"' --max-results 100

# Use direct URL
python -m scraper.main --url "https://priv.au/search?q=%22resume%22+filetype%3Apdf+%22python+developer%22" --max-results 50
```

### Batch Processing (Recommended)
```powershell
# Process multiple developer types from config.json
python -m scraper.main --config config.json --max-results 200
```

### Advanced Options
```powershell
python -m scraper.main \
  --query '"resume" filetype:pdf "full stack developer"' \
  --max-results 100 \
  --model gpt-4o-mini \
  --download-dir downloads \
  --out output/resumes.jsonl \
  --download-timeout 1800 \
  --extract-timeout 1800 \
  --no-headless  # Show browser window
```

## Output Format

### Files Generated
- **PDFs**: Organized in `downloads/` directory
- **Structured Data**: `output/resumes.jsonl` (JSON Lines format)

### JSON Structure
Each resume is extracted as a JSON object with:
```json
{
  "name": "John Doe",
  "email": "john.doe@gmail.com",
  "github": "https://github.com/johndoe",
  "education": "University of Technology\nComputer Science - Bachelor's Degree\n2018-2022",
  "experiences": [
    "Senior Developer at TechCorp (2022-Present) - Led team of 5 developers",
    "Junior Developer at StartupXYZ (2020-2022) - Built React applications"
  ],
  "source_url": "https://example.com/resume.pdf",
  "pdf_path": "downloads/resume.pdf",
  "id": "unique_hash_id"
}
```

## Configuration

The `config.json` file contains 50+ pre-configured search queries for different developer types:
- Frontend/Backend/Full-stack developers
- Mobile developers (iOS, Android, Flutter, React Native)
- Cloud engineers (AWS, Azure, GCP)
- DevOps engineers
- Blockchain developers
- Game developers (Unity, Unreal)
- And many more...

## Technical Details

### Dependencies
- **Playwright**: Web automation and PDF discovery
- **OpenAI**: AI-powered text extraction and structuring
- **PyMuPDF**: PDF text extraction
- **BeautifulSoup4**: HTML parsing
- **Tenacity**: Retry logic for robust processing
- **tqdm**: Progress bars

### Error Handling
- Automatic retries for failed downloads
- Fallback regex extraction when AI fails
- Configurable timeouts for large PDFs
- Comprehensive logging and error reporting

### Performance Features
- Headless browser operation
- Concurrent PDF processing
- Smart duplicate detection
- Memory-efficient streaming

## Success Metrics

✅ **3,623+ resumes successfully processed**  
✅ **High-quality structured data extraction**  
✅ **Robust error handling and recovery**  
✅ **Scalable batch processing capabilities**  

## Notes

- The scraper intelligently identifies PDFs through multiple methods
- OpenAI extraction provides high-quality structured data
- Regex fallback ensures no resume is completely lost
- All downloads are organized and deduplicated automatically
