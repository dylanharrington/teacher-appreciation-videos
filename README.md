# Teacher Appreciation Video Splicing Tool

This tool combines student-submitted videos for teacher appreciation into single videos for each teacher.

## Requirements

- Python 3.6+
- FFmpeg (must be installed and available in your PATH)

## Installation

1. Ensure you have Python 3.6 or higher installed
2. Install FFmpeg:
   - **macOS**: `brew install ffmpeg`
   - **Windows**: Download from [FFmpeg.org](https://ffmpeg.org/download.html) or install via Chocolatey: `choco install ffmpeg`
   - **Linux**: `sudo apt install ffmpeg` (Ubuntu/Debian) or `sudo yum install ffmpeg` (CentOS/RHEL)

## Usage

1. Place all student videos in a single directory
2. Run the script with the input and output directories specified:

```bash
python video_splicing.py --input /path/to/videos --output /path/to/output
```

### Video Naming Convention

Videos should follow this naming format:
```
teacherfirstname_teacherlastname_studentname.extension
```

For example:
- `john_smith_alice.mp4`
- `jane_doe_bob.mov`

### Command Line Options

```
usage: video_splicing.py [-h] --input INPUT --output OUTPUT [--temp TEMP] [--no-normalize] [--keep-temp]

Teacher Appreciation Video Splicing Tool

options:
  -h, --help            show this help message and exit
  --input INPUT, -i INPUT
                        Directory containing input videos
  --output OUTPUT, -o OUTPUT
                        Directory for output videos
  --temp TEMP, -t TEMP  Directory for temporary files
  --no-normalize        Skip video normalization
  --keep-temp           Keep temporary files
```

## How It Works

1. The script scans the input directory for video files
2. It parses filenames to group videos by teacher
3. For each teacher, it:
   - Normalizes videos to ensure consistent format (optional)
   - Concatenates all videos into a single output file
4. The final videos are saved in the output directory with names like `firstname_lastname_appreciation.mp4`

## Supported Video Formats

The script supports common video formats including:
- .mp4
- .mov
- .avi
- .mkv
- .webm
- .m4v
- .wmv
- .flv

## Troubleshooting

If you encounter issues:

1. Ensure FFmpeg is properly installed and in your PATH
2. Check that video filenames follow the correct format
3. Try running with the `--no-normalize` flag if videos fail to process
4. Use the `--keep-temp` flag to preserve temporary files for debugging

## Testing with Generated Videos

For testing purposes, you can use the included test video generator script to create dummy videos:

```bash
# Generate 15 test videos (default)
./generate_test_videos.py

# Generate a specific number of test videos
./generate_test_videos.py --count 20

# Generate shorter/longer test videos (in seconds)
./generate_test_videos.py --duration 3

# Specify a different output directory
./generate_test_videos.py --output ./my_test_videos
```

After generating test videos, run the splicing tool:

```bash
./splice_videos.sh
```