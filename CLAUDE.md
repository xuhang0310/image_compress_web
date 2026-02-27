# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Quick Start

```bash
# Run with uv (recommended)
./run.sh

# Or run directly
python3 main.py
```

## Build & Run

```bash
# Sync dependencies with uv
uv sync --link-mode copy --extra cpu

# Run the application
uv run python main.py

# Or with pip
pip install -r requirements.txt
python3 main.py
```

### Common Commands

```bash
# Start with custom parameters
python3 main.py --device=cpu --port=8000
python3 main.py --device=mps --debug
python3 main.py --no-gui

# View logs
tail -f app.log
```

## Architecture Overview

This is an **Image Compression & Watermark Removal Web Application** built with FastAPI.

### High-Level Structure

```
image_compress_web/
├── main.py                 # Application entry point (argparse, uvicorn launcher)
├── backend.py              # FastAPI app definition, middleware, route registration
├── api/                    # REST API endpoints
│   ├── deps.py             # Dependency injection, global model config
│   ├── models.py           # Pydantic request/response models
│   ├── file_ops.py         # File scanning, preview, rename APIs
│   ├── compress.py         # Image compression task APIs
│   └── watermark.py        # Inpainting/watermark removal APIs
├── compressor/             # Image compression module
│   ├── image_compressor.py # Core compression logic (PIL-based)
│   └── file_manager.py     # Backup and file replacement utilities
├── watermark/              # Watermark detection & removal module
│   ├── core.py             # AutoWatermarkRemover (main entry point)
│   ├── detector/           # Watermark detection strategies
│   ├── removal/            # Inpainting-based removal
│   └── lama/               # LaMa model integration
└── frontend/               # Static assets (vanilla HTML/CSS/JS)
    ├── index.html
    ├── css/
    └── js/modules/
```

### Key Components

- **Compression Pipeline**: `api/compress.py` → `compressor/image_compressor.py`
  - Uses PIL for image processing
  - Binary search for optimal quality
  - Automatic resolution scaling if needed

- **Watermark Removal Pipeline**: `api/watermark.py` → `watermark/core.py` → `watermark/lama/`
  - Strategy pattern for mask generation (`ManualMaskStrategy`, `AutoDetectionStrategy`)
  - LaMa inpainting model for image restoration
  - Position-based detection for common watermark locations

- **Model Management**: `api/deps.py`
  - Singleton pattern for `ModelManager` and `AutoWatermarkRemover`
  - Auto-detects device (CUDA/MPS/CPU)

### Tech Stack

- **Backend**: FastAPI, PyTorch, Pillow, OpenCV, lama-cleaner
- **Frontend**: Vanilla HTML/CSS/JavaScript (no bundler)
- **Package Management**: uv (preferred) or pip
- **Python**: 3.11
