#!/usr/bin/env python3
"""
Teacher Appreciation Video Splicing Script

This script processes student-submitted videos for teacher appreciation,
combining all videos for each teacher into a single video.

Video naming format: teacherfirstname_teacherlastname_studentname.extension
"""

import os
import re
import subprocess
import argparse
from collections import defaultdict
import shutil
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Common video formats as of 2025
VIDEO_EXTENSIONS = ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v', '.wmv', '.flv']

def parse_filename(filename):
    """
    Parse a filename to extract teacher and student names.
    Expected format: teacherfirstname_teacherlastname_studentname.extension
    """
    base_name = os.path.splitext(filename)[0]
    parts = base_name.split('_')
    
    if len(parts) < 3:
        return None, None
    
    teacher_first_name = parts[0]
    teacher_last_name = parts[1]
    student_name = '_'.join(parts[2:])  # In case student name has underscores
    
    return f"{teacher_first_name}_{teacher_last_name}", student_name

def is_video_file(filename):
    """Check if a file is a video based on its extension."""
    _, ext = os.path.splitext(filename)
    return ext.lower() in VIDEO_EXTENSIONS

def create_concat_file(video_files, concat_file_path):
    """Create a concat file for FFmpeg to use for concatenation."""
    with open(concat_file_path, 'w') as f:
        for video_file in video_files:
            # Escape single quotes in the file path
            escaped_path = video_file.replace("'", "'\\''")
            f.write(f"file '{escaped_path}'\n")

def concatenate_videos(video_files, output_file, temp_dir):
    """Concatenate video files using FFmpeg."""
    if not video_files:
        logging.warning(f"No videos to concatenate for {output_file}")
        return False
    
    # Create a temporary concat file
    concat_file = os.path.join(temp_dir, f"concat_{os.path.basename(output_file)}.txt")
    create_concat_file(video_files, concat_file)
    
    # Build the FFmpeg command
    cmd = [
        'ffmpeg',
        '-y',  # Overwrite output file if it exists
        '-f', 'concat',
        '-safe', '0',
        '-i', concat_file,
        '-c', 'copy',  # Copy streams without re-encoding
        output_file
    ]
    
    try:
        logging.info(f"Running FFmpeg command: {' '.join(cmd)}")
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logging.info(f"Successfully created {output_file}")
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"FFmpeg error: {e.stderr.decode() if e.stderr else str(e)}")
        
        # If copy fails, try re-encoding
        try:
            logging.info("Trying with re-encoding...")
            cmd = [
                'ffmpeg',
                '-y',
                '-f', 'concat',
                '-safe', '0',
                '-i', concat_file,
                '-c:v', 'libx264',  # Use H.264 codec
                '-c:a', 'aac',      # Use AAC for audio
                '-strict', 'experimental',
                output_file
            ]
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            logging.info(f"Successfully created {output_file} with re-encoding")
            return True
        except subprocess.CalledProcessError as e:
            logging.error(f"FFmpeg re-encoding error: {e.stderr.decode() if e.stderr else str(e)}")
            return False

def normalize_videos(video_files, temp_dir):
    """
    Normalize videos to ensure they can be concatenated properly.
    Returns a list of normalized video paths.
    """
    normalized_videos = []
    
    for i, video_file in enumerate(video_files):
        base_name = os.path.basename(video_file)
        normalized_path = os.path.join(temp_dir, f"norm_{i}_{base_name}")
        
        # Get video information
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=width,height,r_frame_rate',
            '-of', 'csv=p=0',
            video_file
        ]
        
        try:
            result = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            info = result.stdout.decode().strip().split(',')
            
            if len(info) >= 3:
                width, height, frame_rate = info
                
                # Normalize to 1080p at 30fps if needed
                cmd = [
                    'ffmpeg',
                    '-y',
                    '-i', video_file,
                    '-vf', f'scale=-1:min(1080,ih)',
                    '-r', '30',
                    '-c:v', 'libx264',
                    '-preset', 'medium',
                    '-crf', '23',
                    '-c:a', 'aac',
                    '-b:a', '128k',
                    normalized_path
                ]
                
                subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                normalized_videos.append(normalized_path)
                logging.info(f"Normalized {video_file} to {normalized_path}")
            else:
                # If we can't get video info, just copy the file
                shutil.copy(video_file, normalized_path)
                normalized_videos.append(normalized_path)
                logging.warning(f"Couldn't get video info for {video_file}, using original")
        except subprocess.CalledProcessError:
            # If normalization fails, use the original file
            shutil.copy(video_file, normalized_path)
            normalized_videos.append(normalized_path)
            logging.warning(f"Failed to normalize {video_file}, using original")
    
    return normalized_videos

def process_videos(input_dir, output_dir, temp_dir, normalize=True):
    """
    Process all videos in the input directory, grouping them by teacher
    and concatenating them into single videos in the output directory.
    """
    # Create output and temp directories if they don't exist
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(temp_dir, exist_ok=True)
    
    # Group videos by teacher
    teacher_videos = defaultdict(list)
    
    for filename in os.listdir(input_dir):
        if is_video_file(filename):
            filepath = os.path.join(input_dir, filename)
            teacher_name, student_name = parse_filename(filename)
            
            if teacher_name:
                teacher_videos[teacher_name].append(filepath)
                logging.info(f"Added video for {teacher_name} from {student_name}")
            else:
                logging.warning(f"Skipping {filename} - doesn't match expected format")
    
    # Process each teacher's videos
    results = []
    for teacher_name, videos in teacher_videos.items():
        logging.info(f"Processing {len(videos)} videos for {teacher_name}")
        
        # Sort videos alphabetically by filename (which includes student name)
        videos.sort(key=lambda x: os.path.basename(x))
        
        # Normalize videos if requested
        if normalize:
            processed_videos = normalize_videos(videos, temp_dir)
        else:
            processed_videos = videos
        
        # Create output filename
        output_file = os.path.join(output_dir, f"{teacher_name}_appreciation.mp4")
        
        # Concatenate videos
        success = concatenate_videos(processed_videos, output_file, temp_dir)
        
        if success:
            results.append({
                'teacher': teacher_name,
                'video_count': len(videos),
                'output_file': output_file
            })
    
    return results

def cleanup(temp_dir):
    """Clean up temporary files."""
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
        logging.info(f"Cleaned up temporary directory: {temp_dir}")

def main():
    parser = argparse.ArgumentParser(description='Teacher Appreciation Video Splicing Tool')
    parser.add_argument('--input', '-i', required=True, help='Directory containing input videos')
    parser.add_argument('--output', '-o', required=True, help='Directory for output videos')
    parser.add_argument('--temp', '-t', default='./temp', help='Directory for temporary files')
    parser.add_argument('--no-normalize', action='store_true', help='Skip video normalization')
    parser.add_argument('--keep-temp', action='store_true', help='Keep temporary files')
    
    args = parser.parse_args()
    
    logging.info("Starting video processing")
    logging.info(f"Input directory: {args.input}")
    logging.info(f"Output directory: {args.output}")
    
    results = process_videos(args.input, args.output, args.temp, normalize=not args.no_normalize)
    
    # Print summary
    print("\nProcessing complete!")
    print(f"Processed videos for {len(results)} teachers:")
    for result in results:
        print(f"  - {result['teacher']}: {result['video_count']} videos -> {result['output_file']}")
    
    if not args.keep_temp:
        cleanup(args.temp)

if __name__ == "__main__":
    main()