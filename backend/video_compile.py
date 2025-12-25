from moviepy.editor import VideoFileClip, concatenate_videoclips
import os
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def makeVideo(segments, input_path: str = "data/video.mp4", output_path: str = "output/relevant_segments.mp4"):
    """
    Create a video from segments - OPTIMIZED VERSION with better performance.
    
    Args:
        segments: List of (start, end) tuples
        input_path: Path to the input video
        output_path: Path where the output video will be saved
    
    Returns:
        Path to the output video file
    """
    if not segments:
        raise ValueError("No segments provided")
    
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input video not found: {input_path}")
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    logger.info(f"📥 Loading video: {input_path}")
    video = None
    try:
        # Load video with optimized settings
        video = VideoFileClip(input_path)
        
        # Validate segments
        valid_segments = []
        for start, end in segments:
            if start < 0:
                start = 0
            if end > video.duration:
                end = video.duration
            if start < end:
                valid_segments.append((start, end))
        
        if not valid_segments:
            raise ValueError("No valid segments found")
        
        logger.info(f"✂️ Trimming {len(valid_segments)} segments...")
        # Create clips with error handling
        clips = []
        for i, (start, end) in enumerate(valid_segments):
            try:
                clip = video.subclip(start, end)
                clips.append(clip)
                logger.info(f"  Segment {i+1}: {start:.2f}s - {end:.2f}s")
            except Exception as e:
                logger.warning(f"  Failed to create segment {i+1}: {e}")
                continue
        
        if not clips:
            raise ValueError("No clips were successfully created")
        
        logger.info(f"📎 Concatenating {len(clips)} clips...")
        final_clip = concatenate_videoclips(clips, method="compose")
        
        logger.info(f"💾 Saving final video to {output_path}...")
        # Optimized encoding settings for faster processing
        final_clip.write_videofile(
            output_path,
            codec="libx264",
            audio_codec="aac",
            bitrate="2000k",  # Reasonable quality
            preset="medium",  # Balance between speed and compression
            threads=4,  # Use multiple threads
            verbose=False,
            logger=None,  # Suppress verbose output
            fps=24  # Standard frame rate
        )
        
        logger.info(f"✅ Done! Saved to: {output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"❌ Error processing video: {e}")
        raise
    finally:
        # Clean up resources
        if video:
            video.close()
        if 'final_clip' in locals():
            final_clip.close()
        if 'clips' in locals():
            for clip in clips:
                clip.close()

