#!/bin/bash
# Teacher Appreciation Video Splicing Tool - Helper Script

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not installed."
    exit 1
fi

# Check if FFmpeg is installed
if ! command -v ffmpeg &> /dev/null; then
    echo "Error: FFmpeg is required but not installed."
    echo "Please install FFmpeg:"
    echo "  - macOS: brew install ffmpeg"
    echo "  - Linux: sudo apt install ffmpeg (Ubuntu/Debian) or sudo yum install ffmpeg (CentOS/RHEL)"
    echo "  - Windows: Download from FFmpeg.org or install via Chocolatey: choco install ffmpeg"
    exit 1
fi

# Default directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_INPUT_DIR="$SCRIPT_DIR/input"
DEFAULT_OUTPUT_DIR="$SCRIPT_DIR/output"
DEFAULT_TEMP_DIR="$SCRIPT_DIR/temp"

# Create default directories if they don't exist
mkdir -p "$DEFAULT_INPUT_DIR"
mkdir -p "$DEFAULT_OUTPUT_DIR"

# Display welcome message
echo "========================================================"
echo "  Teacher Appreciation Video Splicing Tool"
echo "========================================================"
echo ""
echo "This tool will combine student videos for each teacher."
echo "Videos should be named: teacherfirstname_teacherlastname_studentname.extension"
echo ""
echo "Default directories:"
echo "  - Input:  $DEFAULT_INPUT_DIR"
echo "  - Output: $DEFAULT_OUTPUT_DIR"
echo ""

# Ask for input directory
read -p "Enter input directory [$DEFAULT_INPUT_DIR]: " INPUT_DIR
INPUT_DIR=${INPUT_DIR:-$DEFAULT_INPUT_DIR}

# Ask for output directory
read -p "Enter output directory [$DEFAULT_OUTPUT_DIR]: " OUTPUT_DIR
OUTPUT_DIR=${OUTPUT_DIR:-$DEFAULT_OUTPUT_DIR}

# Ask for normalization preference
read -p "Normalize videos for consistent quality? [Y/n]: " NORMALIZE
NORMALIZE=${NORMALIZE:-Y}
NORMALIZE_FLAG=""
if [[ $NORMALIZE =~ ^[Nn] ]]; then
    NORMALIZE_FLAG="--no-normalize"
fi

# Ask to keep temporary files
read -p "Keep temporary files for debugging? [y/N]: " KEEP_TEMP
KEEP_TEMP=${KEEP_TEMP:-N}
KEEP_TEMP_FLAG=""
if [[ $KEEP_TEMP =~ ^[Yy] ]]; then
    KEEP_TEMP_FLAG="--keep-temp"
fi

echo ""
echo "Starting video processing..."
echo "This may take some time depending on the number and size of videos."
echo ""

# Run the Python script
python3 "$SCRIPT_DIR/video_splicing.py" \
    --input "$INPUT_DIR" \
    --output "$OUTPUT_DIR" \
    --temp "$DEFAULT_TEMP_DIR" \
    $NORMALIZE_FLAG \
    $KEEP_TEMP_FLAG

# Check if the script ran successfully
if [ $? -eq 0 ]; then
    echo ""
    echo "Processing complete! Check the output directory:"
    echo "$OUTPUT_DIR"
    echo ""
    echo "Thank you for using the Teacher Appreciation Video Splicing Tool!"
else
    echo ""
    echo "An error occurred during processing."
    echo "Please check the error messages above for more information."
fi