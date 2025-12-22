from moviepy.editor import VideoFileClip, concatenate_videoclips
import os

# === CONFIGURATION ===

# Set your input and output paths
input_path = "data/video.mp4"  # Replace with your actual video file path
output_path = "output/relevant_segments.mp4"  # Where the final video will be saved

# Create the output directory if it doesn't exist
os.makedirs(os.path.dirname(output_path), exist_ok=True)

def makeVideo(segments):
    print("📥 Loading video...")
    video = VideoFileClip(input_path)

    print("✂️ Trimming segments...")
    clips = [video.subclip(start, end) for start, end in segments]

    print("📎 Concatenating clips...")
    final_clip = concatenate_videoclips(clips)

    print("💾 Saving final video...")
    final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac")

    print(f"✅ Done! Saved to: {output_path}")
