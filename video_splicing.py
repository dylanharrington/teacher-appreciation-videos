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
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Common video formats as of 2025
VIDEO_EXTENSIONS = ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v', '.wmv', '.flv']

# Number of parallel workers for video processing
MAX_WORKERS = 4


def print_progress(current, total, prefix="Progress", bar_length=40):
    """Print a simple progress bar to the console."""
    percent = current / total if total > 0 else 1
    filled = int(bar_length * percent)
    bar = "█" * filled + "░" * (bar_length - filled)
    sys.stdout.write(f"\r{prefix}: |{bar}| {current}/{total} ({percent*100:.0f}%)")
    sys.stdout.flush()
    if current == total:
        print()  # New line when complete


def create_title_card(text, output_path, duration=2.0, font_size=48, bg_color="black", text_color="white"):
    """
    Create a title card video with text using FFmpeg.
    """
    # Escape special characters for FFmpeg drawtext filter
    escaped_text = text.replace("'", "'\\''").replace(":", "\\:")

    cmd = [
        'ffmpeg',
        '-y',
        '-f', 'lavfi',
        '-i', f'color=c={bg_color}:s=720x1280:d={duration}:r=30',
        '-f', 'lavfi',
        '-i', f'anullsrc=r=48000:cl=stereo',
        '-t', str(duration),
        '-vf', f"drawtext=text='{escaped_text}':fontsize={font_size}:fontcolor={text_color}:x=(w-text_w)/2:y=(h-text_h)/2",
        '-c:v', 'libx264',
        '-pix_fmt', 'yuv420p',
        '-profile:v', 'baseline',
        '-level', '3.0',
        '-c:a', 'aac',
        '-b:a', '256k',
        '-ar', '48000',
        '-ac', '2',
        '-movflags', '+faststart',
        '-shortest',
        output_path
    ]

    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logging.info(f"Created title card: {text}")
        return output_path
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to create title card: {e.stderr.decode() if e.stderr else str(e)}")
        return None


def format_teacher_name(teacher_key):
    """Convert teacher_first_teacher_last to 'Teacher First Last' format."""
    parts = teacher_key.split('_')
    if len(parts) >= 2:
        return f"{parts[0].title()} {parts[1].title()}"
    return teacher_key.replace('_', ' ').title()


def format_student_name(student_name):
    """Format student name for display."""
    return student_name.replace('_', ' ').title()

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
    Concatenate video files using FFmpeg with consistent settings.
    Since all videos have been normalized with the same audio settings,
    we can safely concatenate them without audio issues.
    """
    if not video_files:
        logging.warning(f"No videos to concatenate for {output_file}")
        return False
    
    # Create a temporary concat file
    concat_file = os.path.join(temp_dir, f"concat_{os.path.basename(output_file)}.txt")
    create_concat_file(video_files, concat_file)
    
    # Use the concat demuxer with consistent settings
    cmd = [
        'ffmpeg',
        '-y',
        '-f', 'concat',
        '-safe', '0',
        '-i', concat_file,
        '-c:v', 'copy',  # Copy video stream to preserve quality
        '-c:a', 'copy',  # Copy audio stream (already normalized)
        '-movflags', '+faststart',  # Optimize for streaming
        output_file
    ]
    
    try:
        logging.info(f"Running FFmpeg command: {' '.join(cmd)}")
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logging.info(f"Successfully created {output_file}")
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"FFmpeg encoding error: {e.stderr.decode() if e.stderr else str(e)}")
        # If the simple concatenation fails, try with minimal re-encoding
        try:
            logging.info("Trying alternative concatenation method...")
            alt_cmd = [
                'ffmpeg',
                '-y',
                '-f', 'concat',
                '-safe', '0',
                '-i', concat_file,
                '-c:v', 'libx264',  # Re-encode video
                '-pix_fmt', 'yuv420p',  # Ensure QuickTime compatibility
                '-profile:v', 'baseline',  # Use baseline profile for better compatibility
                '-level', '3.0',
                '-c:a', 'aac',  # Convert audio to AAC
                '-b:a', '256k',  # Use a high bitrate for good audio quality
                '-ar', '48000',  # Standard audio sample rate
                '-ac', '2',      # Stereo audio (2 channels)
                '-movflags', '+faststart',  # Optimize for streaming
                output_file
            ]
            logging.info(f"Running alternative FFmpeg command: {' '.join(alt_cmd)}")
            subprocess.run(alt_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            logging.info(f"Successfully created {output_file} with alternative method")
            return True
        except subprocess.CalledProcessError as e2:
            logging.error(f"Alternative method also failed: {e2.stderr.decode() if e2.stderr else str(e2)}")
            return False

def normalize_single_video(args):
    """
    Normalize a single video file. Used for parallel processing.
    Returns (index, normalized_path) or (index, None) on failure.
    """
    i, video_file, temp_dir = args

    # Standard resolution and frame rate for all videos - using portrait orientation
    target_width = 720
    target_height = 1280
    target_fps = 30

    base_name = os.path.basename(video_file)
    # Ensure output is always .mp4
    base_name_no_ext = os.path.splitext(base_name)[0]
    normalized_path = os.path.join(temp_dir, f"norm_{i}_{base_name_no_ext}.mp4")

    # Normalize with loudnorm for consistent audio levels
    # Using two-pass loudnorm would be ideal but single-pass is good enough
    cmd = [
        'ffmpeg',
        '-y',
        '-i', video_file,
        '-vf', f'scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2',
        '-af', 'loudnorm=I=-16:TP=-1.5:LRA=11',  # EBU R128 loudness normalization
        '-r', str(target_fps),
        '-c:v', 'libx264',
        '-pix_fmt', 'yuv420p',
        '-profile:v', 'baseline',
        '-level', '3.0',
        '-movflags', '+faststart',
        '-preset', 'medium',
        '-crf', '23',
        '-c:a', 'aac',
        '-b:a', '256k',
        '-ar', '48000',
        '-ac', '2',
        normalized_path
    ]

    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logging.info(f"Normalized {video_file}")
        return (i, normalized_path)
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to normalize {video_file}: {e.stderr.decode() if e.stderr else str(e)}")
        # Fallback without loudnorm
        try:
            simple_cmd = [
                'ffmpeg',
                '-y',
                '-i', video_file,
                '-c:v', 'libx264',
                '-pix_fmt', 'yuv420p',
                '-profile:v', 'baseline',
                '-level', '3.0',
                '-movflags', '+faststart',
                '-c:a', 'aac',
                '-b:a', '256k',
                '-ar', '48000',
                '-ac', '2',
                normalized_path
            ]
            subprocess.run(simple_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            logging.info(f"Simple conversion of {video_file}")
            return (i, normalized_path)
        except subprocess.CalledProcessError:
            logging.warning(f"All normalization attempts failed for {video_file}")
            return (i, None)


def normalize_videos(video_files, temp_dir):
    """
    Normalize videos to ensure they can be concatenated properly.
    Uses parallel processing for faster execution.
    Includes audio loudness normalization for consistent volume.
    """
    if not video_files:
        return []

    total = len(video_files)
    results = [None] * total
    completed = 0

    print(f"\nNormalizing {total} video(s)...")

    # Prepare arguments for parallel processing
    args_list = [(i, video_file, temp_dir) for i, video_file in enumerate(video_files)]

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(normalize_single_video, args): args[0] for args in args_list}

        for future in as_completed(futures):
            idx, normalized_path = future.result()
            results[idx] = normalized_path
            completed += 1
            print_progress(completed, total, prefix="Normalizing")

    # Filter out None values (failed normalizations) while preserving order
    return [path for path in results if path is not None]

def add_transitions(videos, temp_dir):
    """
    Add visual fade transitions between videos.
    Shows progress during processing.
    """
    if len(videos) <= 1:
        return videos

    total = len(videos)
    processed_videos = []

    print(f"\nAdding transitions to {total} video(s)...")

    for i, video in enumerate(videos):
        duration_cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'csv=p=0',
            video
        ]

        try:
            duration = float(subprocess.run(duration_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout.decode().strip())

            fade_file = os.path.join(temp_dir, f"fade_{i}.mp4")

            cmd = [
                'ffmpeg',
                '-y',
                '-i', video,
                '-vf', f'fade=t=in:st=0:d=0.5,fade=t=out:st={max(0, duration-0.5)}:d=0.5',
                '-c:v', 'libx264',
                '-pix_fmt', 'yuv420p',
                '-profile:v', 'baseline',
                '-level', '3.0',
                '-movflags', '+faststart',
                '-c:a', 'copy',
                fade_file
            ]

            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            processed_videos.append(fade_file)
            logging.info(f"Added fade effects to video {i}")
        except (subprocess.CalledProcessError, ValueError) as e:
            logging.error(f"Failed to add fade effects: {str(e)}")
            processed_videos.append(video)

        print_progress(i + 1, total, prefix="Transitions")

    return processed_videos

def process_videos(input_dir, output_dir, temp_dir, normalize=True, title_cards=True):
    """
    Process all videos in the input directory, grouping them by teacher
    and concatenating them into single videos in the output directory.
    """
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(temp_dir, exist_ok=True)

    # Group videos by teacher, keeping track of student names
    teacher_videos = defaultdict(list)

    for filename in os.listdir(input_dir):
        if is_video_file(filename):
            filepath = os.path.join(input_dir, filename)
            teacher_name, student_name = parse_filename(filename)

            if teacher_name:
                teacher_videos[teacher_name].append((filepath, student_name))
                logging.info(f"Added video for {teacher_name} from {student_name}")
            else:
                logging.warning(f"Skipping {filename} - doesn't match expected format")

    # Process each teacher's videos
    results = []
    total_teachers = len(teacher_videos)

    for teacher_idx, (teacher_name, video_tuples) in enumerate(teacher_videos.items(), 1):
        print(f"\n{'='*60}")
        print(f"Processing teacher {teacher_idx}/{total_teachers}: {format_teacher_name(teacher_name)}")
        print(f"{'='*60}")

        # Sort by student name
        video_tuples.sort(key=lambda x: x[1])
        videos = [v[0] for v in video_tuples]
        student_names = [v[1] for v in video_tuples]

        # Normalize videos if requested
        if normalize:
            processed_videos = normalize_videos(videos, temp_dir)
        else:
            processed_videos = videos

        # Add transitions
        videos_with_transitions = add_transitions(processed_videos, temp_dir)

        # Add title cards if requested
        final_video_list = []
        if title_cards and videos_with_transitions:
            print(f"\nCreating title cards...")

            # Create teacher intro card
            teacher_display = format_teacher_name(teacher_name)
            intro_card = os.path.join(temp_dir, f"intro_{teacher_name}.mp4")
            intro_result = create_title_card(
                f"For {teacher_display}",
                intro_card,
                duration=3.0,
                font_size=56
            )
            if intro_result:
                final_video_list.append(intro_result)

            # Add student name cards before each video
            for idx, (video, student_name) in enumerate(zip(videos_with_transitions, student_names)):
                student_display = format_student_name(student_name)
                student_card = os.path.join(temp_dir, f"card_{teacher_name}_{idx}.mp4")
                card_result = create_title_card(
                    f"From: {student_display}",
                    student_card,
                    duration=1.5,
                    font_size=44
                )
                if card_result:
                    final_video_list.append(card_result)
                final_video_list.append(video)

            print_progress(len(student_names), len(student_names), prefix="Title cards")
        else:
            final_video_list = videos_with_transitions

        # Create output filename
        output_file = os.path.join(output_dir, f"{teacher_name}_appreciation.mp4")

        # Concatenate videos
        print(f"\nConcatenating final video...")
        success = concatenate_videos(final_video_list, output_file, temp_dir)

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
    parser.add_argument('--no-title-cards', action='store_true', help='Skip title cards')
    parser.add_argument('--keep-temp', action='store_true', help='Keep temporary files')

    args = parser.parse_args()

    print("\n" + "="*60)
    print("  Teacher Appreciation Video Splicing Tool")
    print("="*60)

    logging.info("Starting video processing")
    logging.info(f"Input directory: {args.input}")
    logging.info(f"Output directory: {args.output}")

    results = process_videos(
        args.input,
        args.output,
        args.temp,
        normalize=not args.no_normalize,
        title_cards=not args.no_title_cards
    )

    # Print summary
    print("\n" + "="*60)
    print("  Processing Complete!")
    print("="*60)
    print(f"\nProcessed videos for {len(results)} teacher(s):")
    for result in results:
        teacher_display = format_teacher_name(result['teacher'])
        print(f"  - {teacher_display}: {result['video_count']} videos -> {result['output_file']}")

    if not args.keep_temp:
        cleanup(args.temp)

if __name__ == "__main__":
    main()