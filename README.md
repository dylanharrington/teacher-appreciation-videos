# Teacher Appreciation Video Splicing Tool

Combine student-submitted videos into polished appreciation videos for each teacher.

## Features

- **Title cards** - Automatic intro card ("For Mrs. Johnson") and student name cards ("From: Sarah") before each clip
- **Audio normalization** - Consistent volume across all clips using EBU R128 loudness standards
- **Fade transitions** - Smooth fade in/out between clips
- **Parallel processing** - Faster processing using multiple CPU cores
- **Progress bars** - Visual feedback during processing
- **Portrait-optimized** - Output in 720x1280 portrait format, ideal for mobile viewing
- **Format flexibility** - Accepts MP4, MOV, AVI, MKV, WebM, and more

## Requirements

- Python 3.6+
- FFmpeg (must be installed and available in your PATH)

## Installation

1. Clone this repository
2. Install FFmpeg:
   - **macOS**: `brew install ffmpeg`
   - **Linux**: `sudo apt install ffmpeg` (Ubuntu/Debian)
   - **Windows**: `choco install ffmpeg` or download from [ffmpeg.org](https://ffmpeg.org/download.html)

## Quick Start

1. Name your videos using this format:
   ```
   teacherfirst_teacherlast_studentname.mp4
   ```
   Examples: `john_smith_alice.mp4`, `jane_doe_bob.mov`

2. Run the interactive script:
   ```bash
   ./splice_videos.sh
   ```

   Or use the Python script directly:
   ```bash
   python video_splicing.py -i ./input -o ./output
   ```

## Command Line Options

```
python video_splicing.py [-h] -i INPUT -o OUTPUT [--temp TEMP] [--no-normalize] [--no-title-cards] [--keep-temp]

Options:
  -i, --input         Directory containing input videos (required)
  -o, --output        Directory for output videos (required)
  -t, --temp          Directory for temporary files (default: ./temp)
  --no-normalize      Skip video normalization (faster, but may cause issues)
  --no-title-cards    Skip title cards between clips
  --keep-temp         Keep temporary files for debugging
```

## How It Works

```
Input Videos                    Output
─────────────────────────────────────────────────────────────
john_smith_alice.mp4  ─┐
john_smith_bob.mp4    ─┼──►  john_smith_appreciation.mp4
john_smith_carol.mp4  ─┘

jane_doe_dan.mp4      ─┬──►  jane_doe_appreciation.mp4
jane_doe_emma.mp4     ─┘
```

**Processing pipeline:**

1. **Parse** - Groups videos by teacher name from filenames
2. **Normalize** - Scales to 720x1280, standardizes frame rate (30fps) and audio (48kHz stereo)
3. **Loudness normalize** - Adjusts audio levels using EBU R128 standard (-16 LUFS)
4. **Add transitions** - Applies 0.5s fade in/out to each clip
5. **Generate title cards** - Creates intro and student name cards
6. **Concatenate** - Combines everything into the final video

## Project Structure

```
teacher-appreciation-videos/
├── video_splicing.py       # Main processing script
├── splice_videos.sh        # Interactive wrapper script
├── generate_test_videos.py # Test video generator
├── input/                  # Place input videos here
├── output/                 # Processed videos appear here
└── temp/                   # Temporary files (auto-cleaned)
```

## Testing

Generate test videos to try out the tool:

```bash
# Generate 15 test videos (default)
python generate_test_videos.py

# Customize
python generate_test_videos.py --count 20 --duration 3

# Then process them
./splice_videos.sh
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| FFmpeg not found | Ensure FFmpeg is installed and in your PATH |
| Videos fail to process | Try `--no-normalize` flag |
| Audio out of sync | Make sure source videos aren't corrupted |
| Title cards look wrong | Check for special characters in filenames |

Use `--keep-temp` to preserve intermediate files for debugging.

## License

MIT License - see [LICENSE](LICENSE) for details.
