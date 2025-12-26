"""
Video Transcript Analyzer Module
Fetches YouTube transcripts and extracts pattern-specific timestamps
"""

from typing import Optional, Dict, List, Tuple
from youtube_transcript_api import YouTubeTranscriptApi
import re


def extract_video_id(url: str) -> Optional[str]:
    """
    Extract YouTube video ID from URL.
    
    Args:
        url: YouTube video URL
    
    Returns:
        Video ID or None
    """
    patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/)([^&\n?]*)',
        r'youtube\.com/embed/([^&\n?]*)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def check_audio_availability(video_url: str) -> Tuple[bool, Optional[str]]:
    """
    Check if video has transcript/audio available.
    
    Args:
        video_url: YouTube video URL
    
    Returns:
        Tuple of (has_transcript, reason_if_unavailable)
    """
    video_id = extract_video_id(video_url)
    if not video_id:
        return False, "Invalid video URL"
    
    try:
        # Try to get transcript - first try without language code (auto-detect)
        try:
            YouTubeTranscriptApi.get_transcript(video_id)
            return True, None
        except Exception:
            # If that fails, try to list available transcripts
            try:
                transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
                # Check if any transcript is available
                for t in transcript_list:
                    return True, None
                return False, "No transcripts available"
            except Exception as e2:
                error_msg = str(e2).lower()
                if "transcript" in error_msg or "disabled" in error_msg or "no transcript" in error_msg:
                    return False, "Transcript unavailable - video skipped"
                elif "video unavailable" in error_msg:
                    return False, "Video unavailable"
                else:
                    return False, f"Transcript access failed: {str(e2)[:50]}"
    except Exception as e:
        error_msg = str(e).lower()
        if "transcript" in error_msg or "disabled" in error_msg or "no transcript" in error_msg:
            return False, "Transcript unavailable - video skipped"
        elif "video unavailable" in error_msg:
            return False, "Video unavailable"
        else:
            return False, f"Transcript access failed: {str(e)[:50]}"


def get_video_transcript(video_url: str) -> Optional[List[Dict]]:
    """
    Fetch video transcript from YouTube.
    
    Args:
        video_url: YouTube video URL
    
    Returns:
        List of transcript segments with {text, start, duration} or None
    """
    video_id = extract_video_id(video_url)
    if not video_id:
        print(f"❌ Invalid video URL: {video_url}")
        return None
    
    try:
        # Try to get transcript - first try without language code (auto-detect)
        try:
            transcript = YouTubeTranscriptApi.get_transcript(video_id)
            return transcript
        except Exception:
            # If that fails, try to get available transcripts and use the first one
            try:
                transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
                # Try to get manually created transcript first, then auto-generated
                transcript = None
                for t in transcript_list:
                    try:
                        transcript = t.fetch()
                        break
                    except:
                        continue
                
                # If no manual transcript, try auto-generated
                if not transcript:
                    for t in transcript_list:
                        try:
                            transcript = t.translate('en').fetch() if hasattr(t, 'translate') else None
                            if transcript:
                                break
                        except:
                            continue
                
                return transcript
            except Exception as e2:
                print(f"❌ Transcript fetch failed for {video_id}: {e2}")
                return None
    except Exception as e:
        print(f"❌ Transcript fetch failed for {video_id}: {e}")
        return None


def find_pattern_in_transcript(
    transcript: List[Dict],
    pattern_name: str,
    pattern_keywords: List[str]
) -> Optional[Tuple[float, float]]:
    """
    Find timestamps where pattern is explained in transcript.
    
    Args:
        transcript: List of transcript segments
        pattern_name: Name of the pattern
        pattern_keywords: Keywords to search for
    
    Returns:
        Tuple of (start_time, end_time) or None
    """
    if not transcript:
        return None
    
    # Convert keywords to lowercase for case-insensitive matching
    keywords_lower = [kw.lower() for kw in pattern_keywords]
    
    # Score each segment based on keyword matches
    segment_scores = []
    for i, segment in enumerate(transcript):
        text_lower = segment['text'].lower()
        score = sum(1 for kw in keywords_lower if kw in text_lower)
        segment_scores.append((i, score, segment['start']))
    
    # Find segment with highest score
    if not segment_scores or max(seg[1] for seg in segment_scores) == 0:
        # No matches found, return first 2 minutes as default
        return (0, min(120, transcript[-1]['start'] + transcript[-1].get('duration', 5)))
    
    # Get best match segment
    best_segment_idx = max(segment_scores, key=lambda x: x[1])[0]
    best_segment = transcript[best_segment_idx]
    
    # Expand to include context (±10-20 seconds)
    start_time = max(0, best_segment['start'] - 15)
    
    # Find end time by looking ahead for related content
    end_idx = best_segment_idx
    for i in range(best_segment_idx, min(best_segment_idx + 10, len(transcript))):
        text_lower = transcript[i]['text'].lower()
        if any(kw in text_lower for kw in keywords_lower):
            end_idx = i
    
    end_segment = transcript[end_idx]
    end_time = end_segment['start'] + end_segment.get('duration', 5) + 15
    
    # Ensure reasonable segment length (max 5 minutes)
    if end_time - start_time > 300:
        end_time = start_time + 300
    
    return (start_time, end_time)


def extract_solution_timestamps(
    video_url: str,
    pattern_name: str,
    pattern_keywords: List[str]
) -> Optional[Dict]:
    """
    Extract solution timestamps from video transcript WITH highlighted text.
    
    Args:
        video_url: YouTube video URL
        pattern_name: Pattern to search for
        pattern_keywords: Keywords related to pattern
    
    Returns:
        Dict with {start_time, end_time, start_formatted, end_formatted, confidence, 
                   transcript_text, highlighted_portion}
        or None if transcript unavailable
    """
    # Check availability first
    has_transcript, reason = check_audio_availability(video_url)
    if not has_transcript:
        return None
    
    # Get transcript
    transcript = get_video_transcript(video_url)
    if not transcript:
        return None
    
    # Find pattern timestamps
    timestamps = find_pattern_in_transcript(transcript, pattern_name, pattern_keywords)
    if not timestamps:
        return None
    
    start_time, end_time = timestamps
    
    # Format timestamps as MM:SS
    def format_time(seconds: float) -> str:
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins}:{secs:02d}"
    
    # Extract transcript text for the solution section
    solution_text = []
    full_transcript_text = []
    keywords_lower = [kw.lower() for kw in pattern_keywords]
    
    for segment in transcript:
        segment_time = segment['start']
        segment_text = segment['text']
        
        # Build full transcript
        timestamp_str = format_time(segment_time)
        full_transcript_text.append(f"[{timestamp_str}] {segment_text}")
        
        # Extract solution portion (within our timestamp range)
        if start_time <= segment_time <= end_time:
            # Check if this segment contains keywords (HIGHLIGHT)
            has_keywords = any(kw in segment_text.lower() for kw in keywords_lower)
            if has_keywords:
                solution_text.append(f"**[{timestamp_str}] {segment_text}**")  # Highlighted
            else:
                solution_text.append(f"[{timestamp_str}] {segment_text}")
    
    return {
        "start_time": start_time,
        "end_time": end_time,
        "start_formatted": format_time(start_time),
        "end_formatted": format_time(end_time),
        "confidence": "high" if timestamps else "medium",
        "transcript_text": "\n".join(full_transcript_text),  # Full transcript
        "highlighted_portion": "\n".join(solution_text)  # Solution section with highlights
    }


def format_timestamp_for_url(seconds: float) -> str:
    """Convert seconds to YouTube URL timestamp format (t=XXs)"""
    return f"t={int(seconds)}s"
