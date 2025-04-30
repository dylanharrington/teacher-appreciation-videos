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
import shlex
import tempfile

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
            # Make sure we're using the absolute path to avoid path issues
            if not os.path.isabs(escaped_path):
                escaped_path = os.path.abspath(escaped_path)
            f.write(f"file '{escaped_path}'\n")

def concatenate_videos(video_files, output_file, temp_dir):
    """
    Concatenate video files using FFmpeg.
    Ensures QuickTime compatibility with proper encoding settings.
    """
    if not video_files:
        logging.warning(f"No videos to concatenate for {output_file}")
        return False
    
    # Create a temporary concat file
    concat_file = os.path.join(temp_dir, f"concat_{os.path.basename(output_file)}.txt")
    create_concat_file(video_files, concat_file)
    
    # Use the concat demuxer with QuickTime-compatible settings
    cmd = [
        'ffmpeg',
        '-y',
        '-f', 'concat',
        '-safe', '0',
        '-i', concat_file,
        '-c:v', 'libx264',
        '-pix_fmt', 'yuv420p',  # Ensure QuickTime compatibility
        '-profile:v', 'baseline',  # Use baseline profile for better compatibility
        '-level', '3.0',
        '-movflags', '+faststart',  # Optimize for streaming
        '-c:a', 'aac',
        '-strict', 'experimental',
        '-shortest',  # Use the shortest input as reference
        output_file
    ]
    
    try:
        logging.info(f"Running FFmpeg command: {' '.join(cmd)}")
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logging.info(f"Successfully created {output_file}")
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"FFmpeg encoding error: {e.stderr.decode() if e.stderr else str(e)}")
        return False

def normalize_videos(video_files, temp_dir):
    """
    Normalize videos to ensure they can be concatenated properly.
    Prioritizes portrait mode to make portrait videos take up most of the space.
    Returns a list of normalized video paths with QuickTime compatibility.
    """
    normalized_videos = []
    
    # Standard resolution and frame rate for all videos - using portrait orientation
    target_width = 720
    target_height = 1280
    target_fps = 30
    
    for i, video_file in enumerate(video_files):
        base_name = os.path.basename(video_file)
        normalized_path = os.path.join(temp_dir, f"norm_{i}_{base_name}")
        
        # Normalize all videos to the same resolution and frame rate with QuickTime compatibility
        cmd = [
            'ffmpeg',
            '-y',
            '-i', video_file,
            '-vf', f'scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2',
            '-r', str(target_fps),
            '-c:v', 'libx264',
            '-pix_fmt', 'yuv420p',  # Ensure QuickTime compatibility
            '-profile:v', 'baseline',  # Use baseline profile for better compatibility
            '-level', '3.0',
            '-movflags', '+faststart',  # Optimize for streaming
            '-preset', 'medium',
            '-crf', '23',
            '-c:a', 'aac',
            '-b:a', '128k',
            normalized_path
        ]
        
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            normalized_videos.append(normalized_path)
            logging.info(f"Normalized {video_file} to {normalized_path}")
        except subprocess.CalledProcessError as e:
            logging.error(f"Failed to normalize {video_file}: {e.stderr.decode() if e.stderr else str(e)}")
            # If normalization fails, try a simpler approach with QuickTime compatibility
            try:
                simple_cmd = [
                    'ffmpeg',
                    '-y',
                    '-i', video_file,
                    '-c:v', 'libx264',
                    '-pix_fmt', 'yuv420p',  # Ensure QuickTime compatibility
                    '-profile:v', 'baseline',  # Use baseline profile for better compatibility
                    '-level', '3.0',
                    '-movflags', '+faststart',  # Optimize for streaming
                    '-c:a', 'aac',
                    normalized_path
                ]
                subprocess.run(simple_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                normalized_videos.append(normalized_path)
                logging.info(f"Simple conversion of {video_file} to {normalized_path}")
            except subprocess.CalledProcessError:
                logging.warning(f"All normalization attempts failed for {video_file}, skipping")
                continue
    
    return normalized_videos

def add_transitions(videos, temp_dir):
    """
    Add simple fade transitions between videos in a QuickTime-compatible way.
    """
    if len(videos) <= 1:
        return videos
    
    # Process each video to add fade in/out
    processed_videos = []
    
    for i, video in enumerate(videos):
        # Get video duration
        duration_cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'csv=p=0',
            video
        ]
        
        try:
            duration = float(subprocess.run(duration_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout.decode().strip())
            
            # Create a version with fade in/out
            fade_file = os.path.join(temp_dir, f"fade_{i}.mp4")
            
            # Add fade in at the beginning and fade out at the end
            # Using fixed values instead of "outpoint" which was causing issues
            cmd = [
                'ffmpeg',
                '-y',
                '-i', video,
                '-vf', f'fade=t=in:st=0:d=0.5,fade=t=out:st={max(0, duration-0.5)}:d=0.5',
                '-af', f'afade=t=in:st=0:d=0.5,afade=t=out:st={max(0, duration-0.5)}:d=0.5',
                '-c:v', 'libx264',
                '-pix_fmt', 'yuv420p',  # Ensure QuickTime compatibility
                '-profile:v', 'baseline',  # Use baseline profile for better compatibility
                '-level', '3.0',
                '-movflags', '+faststart',  # Optimize for streaming
                '-c:a', 'aac',
                '-strict', 'experimental',
                fade_file
            ]
            
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            processed_videos.append(fade_file)
            logging.info(f"Added fade effects to video {i}")
        except (subprocess.CalledProcessError, ValueError) as e:
            logging.error(f"Failed to add fade effects: {str(e)}")
            # If processing fails, use the original video
            processed_videos.append(video)
    
    return processed_videos

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
        
        # Add transitions between videos (faster method)
        videos_with_transitions = add_transitions(processed_videos, temp_dir)
        
        # Create output filename
        output_file = os.path.join(output_dir, f"{teacher_name}_appreciation.mp4")
        
        # Concatenate videos
        success = concatenate_videos(videos_with_transitions, output_file, temp_dir)
        
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