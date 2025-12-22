from moviepy.editor import VideoFileClip, concatenate_videoclips
import os


def makeVideo(segments, input_path: str = "data/video.mp4", output_path: str = "output/relevant_segments.mp4"):
    """
    Create a video from segments.
    
    Args:
        segments: List of (start, end) tuples
        input_path: Path to the input video
        output_path: Path where the output video will be saved
    """
    print("📥 Loading video...")
    video = VideoFileClip(input_path)

    print("✂️ Trimming segments...")
    clips = [video.subclip(start, end) for start, end in segments]

    print("📎 Concatenating clips...")
    final_clip = concatenate_videoclips(clips)

    print("💾 Saving final video...")
    final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac")

    print(f"✅ Done! Saved to: {output_path}")
    return output_path

