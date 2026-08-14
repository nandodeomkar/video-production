# 🎬 Video Production Stylization Toolkit

A modular, high-performance toolkit designed to stylize images and short video sections into standardized, highly recognizable inserts for professional video production and explainers. Built on pure **NumPy**, **OpenCV**, **FFmpeg**, and **ImageMagick**.

---

## 🏗️ Repository Architecture

The codebase is organized **by concern** — each top-level folder owns exactly one job, so adding new pipelines or GUIs is a single-folder addition.

```
Video Production/
├── apps/                       # End-user GUI applications
│   ├── smart-char-art/         # CharArt live-preview GUI + launcher
│   └── smart-logo-remover/     # Interactive logo/watermark remover GUI + launcher
│
├── pipelines/                  # Custom multi-stage video workflows
│   ├── tiled-clip/             # Mosaic-tile stylization pipeline (also owns shared stages 1-2)
│   ├── char-clip/              # Character Art stylization pipeline
│   └── pop-clip/               # Pop-Art / Comic Book stylization pipeline
│
├── engines/                    # Custom Python rendering engines
│   ├── charart/                # NumPy character rendering engine + tests
│   ├── popart/                 # Comic book processing engine + 17 unit tests
│   ├── tiler/                  # Mosaic builder + its own venv (vendored as a unit)
│   └── logo-remover/           # Interactive delogo engine + CLI launcher + venv
│
├── vendor/                     # Third-party binaries and packages
│   ├── ffmpeg/                 # FFmpeg + FFprobe static binaries
│   ├── imagemagick/            # ImageMagick distribution
│   ├── yt-dlp/                 # yt-dlp.exe
│   ├── rvc/                    # Retrieval-based voice conversion
│   ├── whisper/                # Whisper transcription
│   ├── manim/                  # Manim animation
│   ├── remotion/               # Remotion React video
│   ├── deeplivecam/            # Real-time face manipulation
│   └── scikit-image/           # scikit-image package
│
├── bin/                        # Thin CLI wrappers for vendor binaries
│   ├── ffmpeg.cmd              # → vendor/ffmpeg/
│   ├── ffprobe.cmd             # → vendor/ffmpeg/
│   ├── magick.cmd              # → vendor/imagemagick/
│   ├── yt-dlp.cmd              # → vendor/yt-dlp/
│   ├── rvc.cmd                 # → vendor/rvc/
│   ├── diagnostics.cmd         # Environment verification (Wrapper)
│   └── diagnostics.ps1         # Environment verification (PowerShell)
│
├── docs/                       # All prose documentation
│   ├── workflows/              # In-depth per-pipeline guides
│   │   ├── tiled-clip.md
│   │   ├── char-clip.md
│   │   └── pop-clip.md
│   └── superpowers/            # Specs and implementation plans
│
├── Work/                       # Per-clip scratch space (git-ignored)
│   └── <clipname>/             # Downloaded streams, extracted frames, audio tracks
│
└── Output/                     # Final stylized MP4 videos
```

### Why this layout
- **`apps/` vs `pipelines/`** — apps are interactive GUIs you double-click; pipelines are `.cmd` workflows you invoke from a terminal.
- **`engines/` vs `vendor/`** — `engines/` is Python you wrote; `vendor/` is third-party. Different update cadences.
- **`bin/` is vendor-wrappers only.** Pipeline orchestration lives in `pipelines/`. CLI launchers for custom engines (Tiler, logo-remover) live with their engine.

---

## 🎨 Core Stylization Pipelines

The toolkit features three distinct visual stylization pipelines that share intermediate assets (such as frame sequences and audio extraction) to optimize disk space and rendering performance.

```
YouTube / Video URL
       │
       ▼
 [1] 1-download.cmd    ──► Work/<clip>/source.mp4       (Shared download)
       │
       ▼
 [2] 2-extract-frames.cmd ──► Work/<clip>/frames/f_*.png (Shared frame extraction)
       │                      Work/<clip>/audio.m4a
       │
       ├───────────────────────────────┼───────────────────────────────┐
       ▼                               ▼                               ▼
 [3] Tiled-Clip Pipeline         [3] Char-Clip Pipeline          [3] Pop-Clip Pipeline
     (pipelines\tiled-clip\)     (pipelines\char-clip\)          (pipelines\pop-clip\)
     3-tile-frames.cmd           3-charize-frames.cmd            3-popart-frames.cmd
       │                               │                               │
       ▼                               ▼                               ▼
 [4] 4-stitch.cmd      ──► Output/<clip>_tiled.mp4      Output/<clip>_popart.mp4
                       ──► Output/<clip>_char.mp4
```

### 1. 🟥 Tiled-Clip (Mosaic Grid)
Converts video frames into a gorgeous mosaic, where every frame is rebuilt out of a grid of custom image tiles. Useful to establish a standardized, highly structured visual look.
- **Workflow Guide**: [docs/workflows/tiled-clip.md](docs/workflows/tiled-clip.md)
- **Quick Start**:
  ```batch
  pipelines\tiled-clip\run-all.cmd "https://www.youtube.com/watch?v=dQw4w9WgXcQ" 00:01:12 00:01:16 newsclip1
  ```
- **Output**: `Output\newsclip1_tiled.mp4`

### 2. 🔠 Char-Clip (ASCII, Custom Ramps & Halftone Shading)
Converts video frames into premium character art, mapping cell brightness to customizable characters.
- **Workflow Guide**: [docs/workflows/char-clip.md](docs/workflows/char-clip.md)
- **Styles**: `ascii` (classic brightness ramps), `mono` (stippled halftone fields of one repeating character), `hatch` (sketch-like hatching), or `custom` (arbitrary user-defined ramps mapping to brightness levels).
- **Fills**: `none` (character only), `tint` (tinted blocks), or `image` (dimmed frame background behind glyphs - *highly recommended for facial clarity*).
- **Quick Start (Custom Ramp)**:
  ```batch
  pipelines\char-clip\run-all.cmd "https://youtu.be/dQw4w9WgXcQ" 00:01:12 00:01:16 charclip1 custom 10 ".:-+*#%@" image on
  ```
- **Output**: `Output\charclip1_char.mp4`

### 3. 💥 Pop-Clip (Comic Book / Pop-Art Style)
Applies a stunning, high-saturation comic-book look consisting of five processing passes: **Punch** (saturation boost), **Smooth** (edge-preserving blur), **Quantize** (k-means color grouping), **Halftone** (dot pattern in shadows), and **Outline** (thick black boundary outlines).
- **Workflow Guide**: [docs/workflows/pop-clip.md](docs/workflows/pop-clip.md)
- **Quick Start**:
  ```batch
  pipelines\pop-clip\run-all.cmd "https://youtu.be/dQw4w9WgXcQ" 00:01:12 00:01:16 popclip1 8 100 1.6 6 on
  ```
- **Output**: `Output\popclip1_popart.mp4`

---

## 🛠️ Interactive Utilities

### 🧹 Smart Logo & Watermark Remover
A high-fidelity utility that lets you interactively crop and delete watermarks or station logos from footage locally before editing.
- **How to Launch**: Double-click `apps\smart-logo-remover\launch.cmd`.
- **How to Use**:
  1. Browse and select your source video file in the custom dark-theme GUI.
  2. The tool will automatically open a high-resolution preview frame.
  3. **Click and drag** a bounding box directly over the logo or watermark you wish to remove.
  4. Press **ENTER** or **SPACE** to confirm selection (or **C** to clear and retry).
  5. The program will initialize a high-performance background thread to apply FFmpeg's localized `delogo` filter and render a perfect, unbranded output stream.

### 🔠 Smart CharArt Stylizer GUI
An interactive, high-fidelity desktop application that lets you browse images, dynamically adjust styling knobs, and view live rendering previews in real time.
- **How to Launch**: Double-click `apps\smart-char-art\launch.cmd`.
- **Features & How to Use**:
  1. **Select Source & Save Destination**: Load any custom image (`.png`, `.jpg`, `.webp`) using the browse buttons.
  2. **Tweak Parameters & Live Preview**:
     - Adjust the **Cell Grid Size** slider from 4px to 32px.
     - Pick a **Render Style**: `ascii`, `mono` (halftone), `hatch` (sketching), or `custom`.
     - Input your own characters or custom ramps (e.g. `.:-+*#%@`). The input field enables/disables dynamically based on style!
     - Choose a **Background Fill**: `none` (monochrome), `tint` (block wash), or `image` (dimmed frame background).
     - Toggle **Auto-Normalize** to boost contrast.
  3. **Real-time Rendering**: Any visual adjustments automatically update a fast, downscaled live rendering preview on the right.
  4. **Save Full Artwork**: Press the **Render & Save Full Art** button to trigger a background thread that renders the full-resolution artwork to disk without locking the UI.

---

## ⚙️ Onboarding & Setup

The toolkit relies on two separate Python virtual environments and packaged static binaries to prevent global workspace conflicts.

### 1. System Requirements & External Binaries
Verify static Windows binaries are placed under `vendor/`:
- **FFmpeg**: `vendor\ffmpeg\node_modules\ffmpeg-ffprobe-static\` (wrapped by `bin\ffmpeg.cmd` and `bin\ffprobe.cmd`).
- **yt-dlp**: `vendor\yt-dlp\yt-dlp.exe` (wrapped by `bin\yt-dlp.cmd`).
- **ImageMagick**: `vendor\imagemagick\` (wrapped by `bin\magick.cmd`).

### 2. Setting Up Virtual Environments
To initialize or restore python dependencies:

#### **Tiler venv** (used by Tiler, CharArt, PopArt pipelines):
```powershell
cd engines/tiler
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```
*(Requires: `numpy`, `opencv-python`, `tqdm`)*

#### **Logo-remover venv** (used by the CLI and the Smart Logo Remover GUI):
```powershell
cd engines/logo-remover
python -m venv .venv
.venv\Scripts\pip install numpy opencv-python
```

---

## 🚦 System Health & Diagnostics

To guarantee your environments are healthy and all pipeline command-wrappers resolve correctly, run the system-wide diagnostic check:

```batch
bin\diagnostics.cmd
```

This utility performs:
- **Directory Inspections**: Verifies all required system paths.
- **Binary Wrapper Validation**: Directly invokes `ffmpeg`, `ffprobe`, `yt-dlp`, and `magick` to ensure execution.
- **Python Imports Verification**: Programmatically queries both virtual environments to confirm `numpy`, `cv2`, `tqdm`, and `tkinter` resolve properly.
- **Engine Unit Tests**: Automatically runs the 17 custom PopArt and 13 custom CharArt rendering engine unit tests inside their proper workspace contexts.

