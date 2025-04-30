#!/usr/bin/env python3
"""
Test Video Generator for Teacher Appreciation Video Splicing Tool

This script generates dummy video files for testing the video splicing tool.
It creates short test videos with different colors for different teachers.
"""

import os
import argparse
import subprocess
import random
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Sample teacher and student names
TEACHERS = [
    ("john", "smith"),
    ("jane", "doe"),
    ("robert", "johnson"),
    ("sarah", "williams"),
    ("michael", "brown")
]

STUDENTS = [
    "emma", "noah", "olivia", "liam", "ava", "william", 
    "sophia", "mason", "isabella", "james", "mia", "benjamin",
    "charlotte", "jacob", "amelia", "elijah", "harper", "lucas"
]

def generate_test_video(output_path, duration=5, color="red", text=None):
    """Generate a test video with FFmpeg."""
    # Create a video with solid color background and optional text
    cmd = [
        'ffmpeg',
        '-y',  # Overwrite output file if it exists
        '-f', 'lavfi',  # Use lavfi input virtual device
        '-i', f'color=c={color}:s=640x480:d={duration}',  # Solid color input
    ]
    
    # Add text if provided
    if text:
        # Add text filter
        cmd.extend([
            '-vf', f"drawtext=text='{text}':fontcolor=white:fontsize=36:x=(w-text_w)/2:y=(h-text_h)/2"
        ])
    
    # Add output file
    cmd.extend([
        '-c:v', 'libx264',  # Use H.264 codec
        '-tune', 'stillimage',  # Optimize for still image
        '-pix_fmt', 'yuv420p',  # Pixel format for compatibility
        output_path
    ])
    
    try:
        logging.info(f"Generating test video: {output_path}")
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"FFmpeg error: {e.stderr.decode() if e.stderr else str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Generate test videos for the Teacher Appreciation Video Splicing Tool')
    parser.add_argument('--output', '-o', default='./input', help='Output directory for test videos')
    parser.add_argument('--count', '-c', type=int, default=15, help='Number of test videos to generate')
    parser.add_argument('--duration', '-d', type=int, default=5, help='Duration of each test video in seconds')
    
    args = parser.parse_args()
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output, exist_ok=True)
    
    # Generate random test videos
    videos_created = 0
    teacher_counts = {}
    
    for _ in range(args.count):
        # Select random teacher and student
        teacher = random.choice(TEACHERS)
        student = random.choice(STUDENTS)
        
        teacher_name = f"{teacher[0]}_{teacher[1]}"
        if teacher_name not in teacher_counts:
            teacher_counts[teacher_name] = 0
        teacher_counts[teacher_name] += 1
        
        # Generate a random color
        colors = ["red", "blue", "green", "yellow", "purple", "orange", "pink", "cyan"]
        color = random.choice(colors)
        
        # Create filename
        filename = f"{teacher[0]}_{teacher[1]}_{student}.mp4"
        output_path = os.path.join(args.output, filename)
        
        # Generate text for the video
        text = f"Teacher: {teacher[0].title()} {teacher[1].title()}\nStudent: {student.title()}"
        
        # Generate the test video
        if generate_test_video(output_path, args.duration, color, text):
            videos_created += 1
    
    # Print summary
    print(f"\nGenerated {videos_created} test videos in {args.output}")
    print("\nVideos per teacher:")
    for teacher, count in teacher_counts.items():
        first, last = teacher.split('_')
        print(f"  - {first.title()} {last.title()}: {count} videos")
    
    print("\nYou can now run the video splicing tool to process these test videos:")
    print(f"./splice_videos.sh")

if __name__ == "__main__":
    main()