import sys, os, uuid, re
from enum import Enum
from typing import List, Optional, Dict
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

import database

# ---------------- LOCAL MODULES ----------------
import video_compile, youtube_download
import auth
from config import OPENAI_API_KEY, YOUTUBE_API_KEY, ALLOWED_ORIGINS
import pattern_detector
import knowledge_search
import debug_analyzer
import video_transcript_analyzer
import advanced_code_analyzer
from openai import OpenAI
OPENAI_CLIENT = OpenAI(api_key=OPENAI_API_KEY)

import whisper
from googleapiclient.discovery import build
import logging
import subprocess
import json
import tempfile
from fastapi.responses import StreamingResponse

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------- APP ----------------
# Initialize DB
database.init_db()

app = FastAPI()

# Check ffmpeg availability on startup
try:
    from . import check_ffmpeg_available
except ImportError:
    # Function defined below, will check after definition
    pass

# ---------------- CACHED MODELS ----------------
# Cache Whisper model to avoid reloading on each request
_whisper_model_cache = None

def get_whisper_model(model_size: str = "base"):
    """Get cached Whisper model or load it if not cached
    
    Args:
        model_size: Model size to use. Options: "tiny", "base", "small", "medium", "large"
                    Default: "base" for balance between speed and accuracy
    """
    global _whisper_model_cache
    cache_key = model_size
    if _whisper_model_cache is None or not hasattr(_whisper_model_cache, '_model_size') or _whisper_model_cache._model_size != model_size:
        logger.info(f"Loading Whisper model '{model_size}' (first time)...")
        _whisper_model_cache = whisper.load_model(model_size)
        _whisper_model_cache._model_size = model_size
        logger.info(f"Whisper model '{model_size}' loaded and cached")
    return _whisper_model_cache

@app.get("/api/health")
def health():
    try:
        # Check DB connection
        with database.engine.connect() as conn:
            conn.execute(database.text("SELECT 1"))
        
        # Check ffmpeg availability
        ffmpeg_available, ffmpeg_error = check_ffmpeg_available()
        
        health_status = {
            "status": "ok",
            "database": "connected",
            "model": "gpt-4o",
            "ffmpeg_available": ffmpeg_available
        }
        
        if not ffmpeg_available:
            health_status["ffmpeg_warning"] = ffmpeg_error
        
        return health_status
    except Exception as e:
        return {"status": "error", "database": str(e), "ffmpeg_available": False}

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OUTPUT_DIR = os.path.join(BASE_DIR, "output")
DATA_DIR = os.path.join(BASE_DIR, "data")
DIST_DIR = os.path.join(BASE_DIR, "dist_build")

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

app.mount("/output", StaticFiles(directory=OUTPUT_DIR), name="output")

# ---------------- TASKS ----------------
tasks = {}
class TaskStatus(str, Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    TRANSCRIBING = "transcribing"
    FILTERING = "filtering"
    COMPILING = "compiling"
    COMPLETED = "completed"
    FAILED = "failed"
    UPLOADING = "uploading"  # For local video uploads

# ---------------- MODELS ----------------
class UserRegister(BaseModel):
    username: str
    password: str
    email: Optional[str] = None

class UserLogin(BaseModel):
    username: str
    password: str

class ProcessRequest(BaseModel):
    video_id: str
    goal: str

class ChatRequest(BaseModel):
    message: str
    code: Optional[str] = None
    use_advanced_analysis: Optional[bool] = False  # New flag for advanced analysis

class VideoUploadRequest(BaseModel):
    user_query: Optional[str] = None  # Optional query to help identify solution segments

class VideoSegment(BaseModel):
    title: str
    url: str
    video_id: Optional[str] = None  # YouTube video ID for embedding
    thumbnail: Optional[str] = None
    channel: Optional[str] = None
    start_time:Optional[str] = None
    end_time: Optional[str] = None
    relevance_note: Optional[str] = None
    transcript_text: Optional[str] = None  # Full transcript
    highlighted_portion: Optional[str] = None  # Solution section with ** highlights

class ChatResponse(BaseModel):
    # PRIMARY Pattern (ALWAYS FIRST - Rule Enforced)
    primary_pattern: str
    primary_pattern_explanation: str
    
    # Secondary Issues (syntax, types, etc.)
    secondary_issues: List[str]
    
    # Pattern Intelligence Fields
    pattern_name: str  # Legacy - same as primary_pattern
    pattern_explanation: str
    confidence_score: float
    learning_intent: str
    
    # Solutions
    explanation: str
    corrected_code: Optional[str]
    
    # External Knowledge
    github_repos: List[dict]
    stackoverflow_links: List[dict]
    dev_articles: List[dict]
    
    # Video Segments (with timestamps)
    video_segments: List[VideoSegment]
    video_skip_reasons: List[str]  # Transparency for skipped videos
    
    # Debugging Insights
    debugging_insight: Dict[str, str]
    
    # Legacy fields for backward compatibility
    links: List[str] = []
    youtube_videos: List[dict] = []
    error_analysis: Optional[str] = None

# ---------------- HELPERS ----------------
async def get_gpt4o_response(prompt: str):
    try:
        res = OPENAI_CLIENT.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=3000
        )
        return res.choices[0].message.content.strip()
    except Exception as e:
        print("GPT ERROR:", e)
        return None

def parse_segments(text: str):
    pattern = r"\[(\d+\.?\d*)\s*-\s*(\d+\.?\d*)\]"
    return [(float(s), float(e)) for s, e in re.findall(pattern, text)]

async def search_youtube(query: str):
    """Search YouTube videos - returns list of video dicts"""
    if not YOUTUBE_API_KEY:
        logger.warning("YOUTUBE_API_KEY not set - using fallback video recommendations")
        # Return empty list instead of placeholder videos
        # Placeholder videos cause issues with transcript checking
        return []
    
    try:
        youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
        res = youtube.search().list(q=query, part="snippet", type="video", maxResults=3).execute()
        
        videos = []
        for i in res.get("items", []):
            videos.append({
                "title": i["snippet"]["title"],
                "url": f"https://youtube.com/watch?v={i['id']['videoId']}",
                "thumbnail": i["snippet"]["thumbnails"]["high"]["url"],
                "channel": i["snippet"]["channelTitle"],
            })
        
        return videos
    except Exception as e:
        logger.error(f"YouTube search error: {e}", exc_info=True)
        return []  # Return empty list on error

# ---------------- VIDEO PROCESSING HELPERS ----------------
def check_ffmpeg_available() -> tuple[bool, str]:
    """
    Check if ffmpeg and ffprobe are available in the system PATH.
    Returns: (is_available, error_message)
    """
    try:
        # Check ffmpeg
        result = subprocess.run(
            ['ffmpeg', '-version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode != 0:
            return False, "ffmpeg is installed but not working correctly"
        
        # Check ffprobe
        result = subprocess.run(
            ['ffprobe', '-version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode != 0:
            return False, "ffprobe is installed but not working correctly"
        
        return True, ""
    except FileNotFoundError:
        return False, "ffmpeg/ffprobe not found in PATH. Please install ffmpeg and add it to your system PATH."
    except subprocess.TimeoutExpired:
        return False, "ffmpeg/ffprobe check timed out"
    except Exception as e:
        return False, f"Error checking ffmpeg: {str(e)}"

# Check ffmpeg on module load (after function definition)
ffmpeg_available, ffmpeg_error = check_ffmpeg_available()
if not ffmpeg_available:
    logger.warning(f"⚠️  ffmpeg not available: {ffmpeg_error}")
    logger.warning("⚠️  Video upload features will not work until ffmpeg is installed.")
    logger.warning("⚠️  See LOCALHOST_SETUP.md for installation instructions.")
else:
    logger.info("✅ ffmpeg and ffprobe are available")

def get_video_duration(video_path: str) -> float:
    """Get video duration in seconds using ffprobe (low memory)"""
    try:
        result = subprocess.run(
            [
                'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1', video_path
            ],
            capture_output=True,
            text=True,
            check=True
        )
        duration = float(result.stdout.strip())
        return duration
    except subprocess.CalledProcessError as e:
        logger.error(f"ffprobe error: {e.stderr}")
        raise Exception(f"Failed to get video duration: {e.stderr}")
    except ValueError:
        raise Exception("Invalid video duration format")
    except FileNotFoundError:
        raise Exception("ffprobe not found. Please install ffmpeg.")

def extract_audio_chunk(video_path: str, start_time: float, duration: float, output_path: str) -> str:
    """Extract audio chunk from video without loading full video into memory"""
    try:
        subprocess.run(
            [
                'ffmpeg', '-i', video_path,
                '-ss', str(start_time),
                '-t', str(duration),
                '-vn', '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1',
                '-y', output_path
            ],
            capture_output=True,
            check=True
        )
        return output_path
    except subprocess.CalledProcessError as e:
        logger.error(f"ffmpeg error: {e.stderr.decode()}")
        raise Exception(f"Failed to extract audio chunk: {e.stderr.decode()}")
    except FileNotFoundError:
        raise Exception("ffmpeg not found. Please install ffmpeg.")

def transcribe_chunk(model, audio_path: str, chunk_start: float) -> List[Dict]:
    """Transcribe a single audio chunk and adjust timestamps"""
    try:
        result = model.transcribe(audio_path, verbose=False, condition_on_previous_text=False)
        segments = []
        for seg in result.get("segments", []):
            # Adjust timestamps to account for chunk offset
            segments.append({
                "start": seg["start"] + chunk_start,
                "end": seg["end"] + chunk_start,
                "text": seg["text"].strip()
            })
        return segments
    except Exception as e:
        logger.error(f"Transcription error for chunk at {chunk_start}: {e}")
        return []

async def analyze_problem_solution_sections(transcript_segments: List[Dict], user_query: Optional[str] = None) -> Dict:
    """Analyze transcript to identify problem explanation and solution explanation sections"""
    if not transcript_segments:
        return {
            "problem_segments": [],
            "solution_segments": [],
            "problem_timestamps": [],
            "solution_timestamps": []
        }
    
    # Build transcript text with timestamps
    transcript_text = "\n".join(
        f"[{seg['start']:.2f} - {seg['end']:.2f}] {seg['text']}"
        for seg in transcript_segments
    )
    
    prompt = f"""Analyze this video transcript and identify two types of sections:

1. PROBLEM EXPLANATION sections: Where the problem, issue, or challenge is described/explained
2. SOLUTION EXPLANATION sections: Where the solution, fix, or answer is provided

{"User's Question/Query: " + user_query if user_query else ""}

Transcript with timestamps:
{transcript_text}

Return a JSON object with this exact structure:
{{
  "problem_segments": [list of 0-based segment indices that explain the problem],
  "solution_segments": [list of 0-based segment indices that explain the solution],
  "problem_timestamps": [["start_time", "end_time"], ...] in seconds,
  "solution_timestamps": [["start_time", "end_time"], ...] in seconds
}}

Focus on:
- Problem sections: Error descriptions, issue explanations, what's wrong, challenges faced
- Solution sections: How to fix, step-by-step solutions, code implementations, answers

Return ONLY valid JSON, no other text."""

    try:
        response = await get_gpt4o_response(prompt)
        # Extract JSON from response
        import re
        json_match = re.search(r'\{[^{}]*"problem_segments"[^{}]*\}', response or "", re.DOTALL)
        if json_match:
            analysis = json.loads(json_match.group())
        else:
            # Try parsing entire response
            analysis = json.loads(response or "{}")
        
        # Validate and clean up
        problem_segments = analysis.get("problem_segments", [])
        solution_segments = analysis.get("solution_segments", [])
        
        # Ensure they're lists of integers
        problem_segments = [int(i) for i in problem_segments if isinstance(i, (int, str)) and str(i).isdigit()]
        solution_segments = [int(i) for i in solution_segments if isinstance(i, (int, str)) and str(i).isdigit()]
        
        # Validate indices
        max_index = len(transcript_segments) - 1
        problem_segments = [i for i in problem_segments if 0 <= i <= max_index]
        solution_segments = [i for i in solution_segments if 0 <= i <= max_index]
        
        # Extract timestamps from segments
        problem_timestamps = [
            [transcript_segments[i]["start"], transcript_segments[i]["end"]]
            for i in problem_segments
        ]
        solution_timestamps = [
            [transcript_segments[i]["start"], transcript_segments[i]["end"]]
            for i in solution_segments
        ]
        
        return {
            "problem_segments": problem_segments,
            "solution_segments": solution_segments,
            "problem_timestamps": problem_timestamps,
            "solution_timestamps": solution_timestamps
        }
    except Exception as e:
        logger.warning(f"Failed to analyze problem/solution sections: {e}")
        # Fallback: if user_query provided, try to identify solution segments only
        if user_query:
            return await analyze_solution_segments_fallback(transcript_segments, user_query)
        return {
            "problem_segments": [],
            "solution_segments": [],
            "problem_timestamps": [],
            "solution_timestamps": []
        }

async def analyze_solution_segments_fallback(transcript_segments: List[Dict], user_query: str) -> Dict:
    """Fallback: Simple solution segment identification"""
    transcript_text = "\n".join(
        f"[{seg['start']:.2f} - {seg['end']:.2f}] {seg['text']}"
        for seg in transcript_segments
    )
    
    prompt = f"""User's Question: {user_query}

Transcript:
{transcript_text}

Return a JSON array of segment indices (0-based) that contain solutions or answers to the user's question.
Format: [0, 5, 12] or []"""

    try:
        response = await get_gpt4o_response(prompt)
        import re
        json_match = re.search(r'\[[\d,\s]*\]', response or "")
        if json_match:
            solution_segments = json.loads(json_match.group())
        else:
            solution_segments = []
        
        solution_segments = [int(i) for i in solution_segments if isinstance(i, (int, str)) and str(i).isdigit()]
        max_index = len(transcript_segments) - 1
        solution_segments = [i for i in solution_segments if 0 <= i <= max_index]
        
        solution_timestamps = [
            [transcript_segments[i]["start"], transcript_segments[i]["end"]]
            for i in solution_segments
        ]
        
        return {
            "problem_segments": [],
            "solution_segments": solution_segments,
            "problem_timestamps": [],
            "solution_timestamps": solution_timestamps
        }
    except Exception as e:
        logger.warning(f"Fallback analysis failed: {e}")
        return {
            "problem_segments": [],
            "solution_segments": [],
            "problem_timestamps": [],
            "solution_timestamps": []
        }

# ---------------- VIDEO TASK ----------------
async def process_video_task(task_id, url, goal):
    """Process video task with optimized performance"""
    try:
        logger.info(f"Starting video processing task: {task_id}")
        
        # Step 1: Download video
        tasks[task_id] = {"status": TaskStatus.DOWNLOADING, "progress": 0}
        video_path = os.path.join(DATA_DIR, f"{task_id}.mp4")
        real_path = youtube_download.download_youtube_video(url, video_path)
        logger.info(f"Video downloaded: {real_path}")

        # Step 2: Transcribe using cached model (MUCH FASTER)
        tasks[task_id] = {"status": TaskStatus.TRANSCRIBING, "progress": 30}
        model = get_whisper_model()  # Use cached model
        logger.info("Starting transcription...")
        result = model.transcribe(real_path, verbose=False)
        logger.info("Transcription complete")

        # Build script with timestamps
        script = "\n".join(
            f"[{s['start']:.2f} - {s['end']:.2f}] {s['text']}" for s in result.get("segments", [])
        )

        # Step 3: Filter segments using GPT
        tasks[task_id] = {"status": TaskStatus.FILTERING, "progress": 60}
        prompt = f"""Goal: {goal}

Transcript with timestamps:
{script}

Analyze the transcript and return ONLY the timestamps (in format [start - end]) for segments that directly address the goal.
Return timestamps in chronological order.
Format: [start_time - end_time]
Example: [10.5 - 25.3]
[45.2 - 60.1]"""
        
        filtered = await get_gpt4o_response(prompt)
        logger.info("Segment filtering complete")

        # Parse segments
        segments = parse_segments(filtered or "")
        if not segments:
            raise Exception("No relevant segments found for the goal")

        # Step 4: Compile video
        tasks[task_id] = {"status": TaskStatus.COMPILING, "progress": 80}
        output = os.path.join(OUTPUT_DIR, f"{task_id}.mp4")
        video_compile.makeVideo(segments, real_path, output)
        logger.info(f"Video compilation complete: {output}")

        tasks[task_id] = {
            "status": TaskStatus.COMPLETED, 
            "output_path": output,
            "progress": 100,
            "segments_count": len(segments)
        }

    except Exception as e:
        logger.error(f"Video processing error for task {task_id}: {e}", exc_info=True)
        tasks[task_id] = {"status": TaskStatus.FAILED, "error": str(e), "progress": 0}

async def transcribe_uploaded_video_task(task_id: str, video_path: str, video_id: str, filename: str, user_query: Optional[str] = None):
    """
    Background task to transcribe uploaded video using chunked processing.
    Processes video in 20-second chunks sequentially for low-RAM efficiency and live updates.
    Never loads full video into memory. Deletes temp files immediately after each chunk.
    """
    temp_audio_dir = None
    try:
        logger.info(f"Starting chunked transcription task: {task_id} for video: {video_id}")
        tasks[task_id] = {"status": TaskStatus.UPLOADING, "progress": 5, "segments": []}
        
        # Verify file exists
        if not os.path.exists(video_path):
            raise Exception(f"Video file not found: {video_path}")
        
        # Step 1: Check video duration (max 5 minutes)
        logger.info("Checking video duration...")
        try:
            duration = get_video_duration(video_path)
            MAX_DURATION = 5 * 60  # 5 minutes in seconds
            if duration > MAX_DURATION:
                error_msg = f"Video duration ({duration/60:.1f} minutes) exceeds maximum allowed (5 minutes)."
                suggestion = "Please upload a shorter video or trim it to 5 minutes or less."
                raise Exception(f"{error_msg} {suggestion}")
            logger.info(f"Video duration: {duration:.2f} seconds")
        except Exception as e:
            if "ffprobe not found" in str(e) or "ffmpeg not found" in str(e):
                error_msg = "Video processing tools (ffmpeg) not available on server."
                suggestion = "Please contact administrator to install ffmpeg, or try a different video format."
                raise Exception(f"{error_msg} {suggestion}")
            raise
        
        # Step 2: Load Whisper model (prefer tiny/base for low-RAM)
        tasks[task_id] = {"status": TaskStatus.TRANSCRIBING, "progress": 10, "segments": []}
        logger.info("Loading Whisper model (base for balance)...")
        model = get_whisper_model("base")  # Use base model (can be changed to "tiny" for even lower RAM)
        logger.info("Whisper model loaded")
        
        # Step 3: Process video in 20-second chunks (for low-resource servers)
        CHUNK_DURATION = 20.0  # 20 seconds per chunk (≤20s as required)
        temp_audio_dir = tempfile.mkdtemp(prefix=f"whisper_chunks_{task_id}_")
        logger.info(f"Created temp directory: {temp_audio_dir}")
        
        all_segments = []
        chunk_index = 0
        total_chunks = int(duration / CHUNK_DURATION) + (1 if duration % CHUNK_DURATION > 0 else 0)
        logger.info(f"Processing {total_chunks} chunks of {CHUNK_DURATION}s each")
        
        current_time = 0.0
        detected_language = "unknown"
        
        while current_time < duration:
            chunk_start = current_time
            chunk_end = min(current_time + CHUNK_DURATION, duration)
            actual_chunk_duration = chunk_end - chunk_start
            
            logger.info(f"Processing chunk {chunk_index + 1}/{total_chunks} ({chunk_start:.1f}s - {chunk_end:.1f}s)")
            
            # Extract audio chunk (low memory - doesn't load full video)
            audio_chunk_path = os.path.join(temp_audio_dir, f"chunk_{chunk_index}.wav")
            try:
                extract_audio_chunk(video_path, chunk_start, actual_chunk_duration, audio_chunk_path)
            except Exception as e:
                error_msg = f"Failed to extract audio chunk at {chunk_start}s: {str(e)}"
                suggestion = "Video format may be unsupported. Try converting to MP4 with H.264 codec."
                logger.error(f"{error_msg} {suggestion}")
                raise Exception(f"{error_msg} {suggestion}")
            
            # Transcribe chunk
            try:
                chunk_segments = transcribe_chunk(model, audio_chunk_path, chunk_start)
                all_segments.extend(chunk_segments)
                
                # Detect language from first chunk
                if chunk_index == 0 and chunk_segments:
                    # Try to get language from whisper result
                    try:
                        temp_result = model.transcribe(audio_chunk_path, verbose=False)
                        detected_language = temp_result.get("language", "unknown")
                    except:
                        pass
                
                # Update task with new segments (for live updates)
                progress = 10 + int((chunk_index + 1) / total_chunks * 60)  # 10-70% for transcription
                tasks[task_id] = {
                    "status": TaskStatus.TRANSCRIBING,
                    "progress": progress,
                    "segments": all_segments.copy(),  # Include all segments so far
                    "chunks_processed": chunk_index + 1,
                    "total_chunks": total_chunks
                }
                logger.info(f"Chunk {chunk_index + 1} transcribed: {len(chunk_segments)} segments")
                
            except Exception as e:
                # Log error but continue with next chunk (graceful degradation)
                logger.error(f"Transcription failed for chunk {chunk_index + 1}: {e}")
                # Don't fail entire process - continue with next chunk
                # The error will be visible in final transcript (missing segment)
            
            # CRITICAL: Clean up audio chunk file immediately after processing (never keep in memory)
            try:
                if os.path.exists(audio_chunk_path):
                    os.unlink(audio_chunk_path)
                    logger.debug(f"Deleted temp chunk file: {audio_chunk_path}")
            except Exception as cleanup_err:
                logger.warning(f"Failed to delete temp chunk file {audio_chunk_path}: {cleanup_err}")
                # Continue - don't fail entire process on cleanup error
            
            current_time = chunk_end
            chunk_index += 1
        
        # Step 4: Format transcript segments
        logger.info(f"Formatting {len(all_segments)} total segments...")
        transcript_segments = []
        full_transcript_lines = []
        
        for seg in all_segments:
            start = seg["start"]
            end = seg["end"]
            text = seg["text"].strip()
            
            if not text:  # Skip empty segments
                continue
            
            transcript_segments.append({
                "start": start,
                "end": end,
                "text": text,
                "timestamp": f"{int(start // 60)}:{int(start % 60):02d}"
            })
            
            full_transcript_lines.append(f"[{int(start // 60)}:{int(start % 60):02d}] {text}")
        
        full_transcript = "\n".join(full_transcript_lines)
        logger.info(f"Formatted {len(transcript_segments)} transcript segments")
        
        # Step 5: Analyze problem vs solution sections using GPT
        tasks[task_id] = {"status": TaskStatus.FILTERING, "progress": 75, "segments": transcript_segments}
        logger.info("Analyzing problem and solution sections...")
        
        analysis_result = await analyze_problem_solution_sections(transcript_segments, user_query)
        problem_segments = analysis_result.get("problem_segments", [])
        solution_segments = analysis_result.get("solution_segments", [])
        problem_timestamps = analysis_result.get("problem_timestamps", [])
        solution_timestamps = analysis_result.get("solution_timestamps", [])
        
        logger.info(f"Identified {len(problem_segments)} problem segments and {len(solution_segments)} solution segments")
        
        # Step 6: Store final results
        tasks[task_id] = {
            "status": TaskStatus.COMPLETED,
            "progress": 100,
            "video_id": video_id,
            "video_url": f"/video/upload/{video_id}",
            "filename": filename,
            "segments": transcript_segments,
            "solution_segments": solution_segments,
            "problem_segments": problem_segments,
            "solution_timestamps": solution_timestamps,
            "problem_timestamps": problem_timestamps,
            "full_transcript": full_transcript,
            "duration": duration,
            "language": detected_language,
            "total_segments": len(transcript_segments)
        }
        logger.info(f"Transcription task {task_id} completed successfully")
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Transcription task error for {task_id}: {e}")
        logger.error(f"Full traceback: {error_details}")
        
        # Determine error type and provide clear message (502 Bad Gateway for backend errors)
        error_message = str(e)
        error_type = "processing"
        
        if "ffmpeg" in error_message.lower() or "ffprobe" in error_message.lower():
            error_type = "backend_tools"
            suggestion = "Server configuration issue: ffmpeg not available. Please contact administrator."
        elif "duration" in error_message.lower() or "5 minutes" in error_message:
            error_type = "validation"
            suggestion = "Please upload a video that is 5 minutes or shorter."
        elif "format" in error_message.lower() or "codec" in error_message.lower():
            error_type = "format"
            suggestion = "Video format may be unsupported. Try converting to MP4 with H.264 codec."
        elif "memory" in error_message.lower() or "ram" in error_message.lower():
            error_type = "resources"
            suggestion = "Server resources insufficient. Try a shorter or lower quality video."
        else:
            suggestion = "Backend processing failed. Please try again or contact support."
        
        tasks[task_id] = {
            "status": TaskStatus.FAILED,
            "error": error_message,
            "error_type": error_type,
            "error_suggestion": suggestion,
            "progress": 0
        }
    finally:
        # Clean up temporary audio directory
        if temp_audio_dir and os.path.exists(temp_audio_dir):
            try:
                import shutil
                shutil.rmtree(temp_audio_dir)
                logger.info(f"Cleaned up temp directory: {temp_audio_dir}")
            except Exception as e:
                logger.warning(f"Failed to clean up temp directory: {e}")

# ---------------- AUTH ROUTES ----------------
@app.post("/api/auth/register")
async def register(user: UserRegister):
    print(f"DEBUG: Registering user {user.username}, email: {user.email}")
    try:
        return auth.register_user(user.username, user.password, user.email)
    except Exception as e:
        print(f"DEBUG: Register failed: {e}")
        raise e

@app.post("/api/auth/login")
async def login(user: UserLogin):
    print(f"DEBUG: Login attempt for {user.username}")
    try:
        return auth.authenticate_user(user.username, user.password)
    except Exception as e:
        print(f"DEBUG: Login failed: {e}")
        raise e

@app.get("/api/auth/me")
async def me(user=Depends(auth.get_current_user)):
    return user

# ---------------- VIDEO ROUTES ----------------
@app.get("/api/search")
async def search(q: str = None, max_results: int = 12, user=Depends(auth.get_current_user)):
    """
    Search YouTube videos.
    
    Args:
        query: Search query string
        max_results: Maximum number of results to return (default: 12)
    
    Returns:
        List of video results with video_id, title, thumbnail, channel, etc.
    """
    if not q:
        raise HTTPException(400, "Query parameter 'q' is required")
    
    query = q  # Use q as query for consistency
    
    try:
        # Use YouTube API if available, otherwise return empty or fallback
        if not YOUTUBE_API_KEY:
            logger.warning("YOUTUBE_API_KEY not set - cannot search YouTube videos")
            return {"results": [], "message": "YouTube API key not configured. Please set YOUTUBE_API_KEY environment variable."}
        
        youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
        res = youtube.search().list(
            q=query,
            part="snippet",
            type="video",
            maxResults=min(max_results, 50)  # Limit to 50 max
        ).execute()
        
        results = [
            {
                "video_id": i["id"]["videoId"],
                "title": i["snippet"]["title"],
                "thumbnail": i["snippet"]["thumbnails"]["high"]["url"],
                "channel": i["snippet"]["channelTitle"],
                "description": i["snippet"]["description"][:200] + "..." if len(i["snippet"]["description"]) > 200 else i["snippet"]["description"],
                "published_at": i["snippet"]["publishedAt"]
            }
            for i in res.get("items", [])
        ]
        
        logger.info(f"YouTube search for '{query}': Found {len(results)} videos")
        return {"results": results, "query": query, "count": len(results)}
        
    except Exception as e:
        logger.error(f"YouTube search error: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to search YouTube: {str(e)}")

@app.post("/api/process")
async def process(req: ProcessRequest, bg: BackgroundTasks, user=Depends(auth.get_current_user)):
    task_id = str(uuid.uuid4())
    tasks[task_id] = {"status": TaskStatus.PENDING, "progress": 0}
    url = f"https://youtube.com/watch?v={req.video_id}"
    bg.add_task(process_video_task, task_id, url, req.goal)
    logger.info(f"Video processing task created: {task_id} for video: {req.video_id}")
    return {"task_id": task_id, "status": "pending"}

@app.get("/api/status/{task_id}")
async def status(task_id: str, user=Depends(auth.get_current_user)):
    if task_id not in tasks:
        raise HTTPException(404, "Task not found")
    return tasks[task_id]

@app.get("/api/video/{task_id}")
async def video(task_id: str, user=Depends(auth.get_current_user)):
    task = tasks.get(task_id)
    if not task or task["status"] != TaskStatus.COMPLETED:
        raise HTTPException(400, "Not ready")
    return FileResponse(task["output_path"], media_type="video/mp4")


@app.post("/api/transcribe/local")
async def transcribe_local_video(
    file: UploadFile = File(...),
    user_query: Optional[str] = Form(None),
    bg: BackgroundTasks = BackgroundTasks(),
    user=Depends(auth.get_current_user)  # Authentication checked FIRST by FastAPI
):
    """
    Transcribe a locally uploaded video/audio file with GPT-4 solution segment detection.
    Uses background tasks to avoid timeout on Render.
    Returns task_id immediately, use /api/transcribe/status/{task_id} to check progress.
    Max file size: 500MB, Max duration: 5 minutes
    
    Args:
        file: Video or audio file to upload
        user_query: Optional query/question to help identify solution segments
    
    Returns:
        task_id: Use this to check transcription status
        
    Errors:
        401: Authentication failed (handled by Depends)
        400: Invalid file (missing, wrong type, too large, too long)
        502: Backend processing error (ffmpeg, transcription)
    """
    # Step 1: Validate file exists and is received
    if not file or not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No file received. Please upload a video or audio file."
        )
    
    # Step 2: Validate file type (accept video/ and audio/)
    if not file.content_type:
        # Try to infer from extension as fallback
        filename_lower = file.filename.lower()
        video_extensions = ['.mp4', '.webm', '.mkv', '.avi', '.mov', '.m4v', '.flv']
        audio_extensions = ['.mp3', '.wav', '.m4a', '.ogg', '.flac', '.aac']
        ext = os.path.splitext(filename_lower)[1]
        if ext not in video_extensions + audio_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Accepted formats: video (MP4, WebM, MKV, AVI, MOV) or audio (MP3, WAV, M4A, OGG)."
            )
    elif not (file.content_type.startswith('video/') or file.content_type.startswith('audio/')):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type: {file.content_type}. Please upload a video or audio file."
        )
    
    # Step 3: Validate file size
    MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB
    
    # Generate IDs
    task_id = str(uuid.uuid4())
    video_id = str(uuid.uuid4())
    
    # Preserve original file extension
    original_filename = file.filename
    file_extension = os.path.splitext(original_filename)[1] or ".mp4"
    video_path = os.path.join(DATA_DIR, f"{video_id}{file_extension}")
    
    try:
        logger.info(f"Processing upload request: user={user.get('username')}, file={original_filename}, type={file.content_type}")
        
        # Read file content to check size
        content = await file.read()
        file_size = len(content)
        logger.info(f"File size: {file_size} bytes ({file_size / (1024*1024):.2f} MB)")
        
        # Validate file size
        if file_size == 0:
            raise HTTPException(
                status_code=400,
                detail="Uploaded file is empty. Please upload a valid video or audio file."
            )
        
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File too large ({file_size / (1024*1024):.1f} MB). Maximum size is {MAX_FILE_SIZE / (1024*1024):.0f} MB."
            )
        
        # Step 4: Save file to disk
        os.makedirs(DATA_DIR, exist_ok=True)
        try:
            with open(video_path, 'wb') as f:
                f.write(content)
            logger.info(f"File saved to: {video_path}")
        except Exception as e:
            logger.error(f"Failed to save file: {e}")
            raise HTTPException(
                status_code=502,
                detail=f"Failed to save uploaded file: {str(e)}"
            )
        
        # Step 5: Validate video duration (max 5 minutes) - BEFORE starting background task
        try:
            duration = get_video_duration(video_path)
            MAX_DURATION = 5 * 60  # 5 minutes
            if duration > MAX_DURATION:
                # Clean up file immediately
                try:
                    if os.path.exists(video_path):
                        os.unlink(video_path)
                except:
                    pass
                raise HTTPException(
                    status_code=400,
                    detail=f"Video duration ({duration/60:.1f} minutes) exceeds maximum allowed (5 minutes). Please upload a shorter video."
                )
            logger.info(f"Duration validated: {duration:.2f} seconds")
        except HTTPException:
            # Re-raise HTTP exceptions (validation errors)
            raise
        except Exception as e:
            # If duration check fails (ffmpeg issues), clean up and return 502
            logger.error(f"Failed to check video duration: {e}")
            try:
                if os.path.exists(video_path):
                    os.unlink(video_path)
            except:
                pass
            error_msg = str(e)
            if "ffprobe not found" in error_msg or "ffmpeg not found" in error_msg:
                raise HTTPException(
                    status_code=502,
                    detail="Video processing tools (ffmpeg) not available on server. Please contact administrator."
                )
            raise HTTPException(
                status_code=502,
                detail=f"Failed to validate video file: {error_msg}"
            )
        
        # Step 6: Initialize task and start background processing
        tasks[task_id] = {"status": TaskStatus.PENDING, "progress": 0, "segments": []}
        
        # Start background transcription task
        bg.add_task(transcribe_uploaded_video_task, task_id, video_path, video_id, original_filename, user_query)
        logger.info(f"Transcription task {task_id} started for file {video_id}")
        
        # Return task_id immediately (non-blocking)
        return {
            "task_id": task_id,
            "status": "pending",
            "message": "File uploaded. Transcription in progress. Use /api/transcribe/status/{task_id} to check progress."
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions (401, 400, 502) - don't wrap them
        raise
    except Exception as e:
        # Unexpected errors - clean up and return 502
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Unexpected error in video upload: {e}")
        logger.error(f"Full traceback: {error_details}")
        
        # Clean up video file on error
        try:
            if os.path.exists(video_path):
                os.unlink(video_path)
        except:
            pass
        
        raise HTTPException(
            status_code=502,
            detail=f"Backend processing error: {str(e)}"
        )


@app.get("/api/transcribe/status/{task_id}")
async def get_transcription_status(task_id: str, user=Depends(auth.get_current_user)):
    """
    Get transcription status and results for a task.
    Returns the full transcript data when status is 'completed'.
    Includes live segments as they're processed.
    """
    if task_id not in tasks:
        raise HTTPException(404, "Task not found")
    
    task = tasks[task_id]
    
    # If completed, return full results
    if task.get("status") == TaskStatus.COMPLETED:
        return {
            "task_id": task_id,
            "status": "completed",
            "progress": task.get("progress", 100),
            "video_id": task.get("video_id"),
            "video_url": task.get("video_url"),
            "filename": task.get("filename"),
            "segments": task.get("segments", []),
            "solution_segments": task.get("solution_segments", []),
            "problem_segments": task.get("problem_segments", []),
            "solution_timestamps": task.get("solution_timestamps", []),
            "problem_timestamps": task.get("problem_timestamps", []),
            "full_transcript": task.get("full_transcript", ""),
            "duration": task.get("duration", 0),
            "language": task.get("language", "unknown"),
            "total_segments": task.get("total_segments", 0)
        }
    
    # If failed, return error with suggestion
    if task.get("status") == TaskStatus.FAILED:
        return {
            "task_id": task_id,
            "status": "failed",
            "error": task.get("error", "Unknown error"),
            "error_suggestion": task.get("error_suggestion", "Please try again or contact support."),
            "progress": task.get("progress", 0)
        }
    
    # Otherwise return current status with live segments
    return {
        "task_id": task_id,
        "status": task.get("status", "pending"),
        "progress": task.get("progress", 0),
        "segments": task.get("segments", []),  # Live segments as they're processed
        "chunks_processed": task.get("chunks_processed", 0),
        "total_chunks": task.get("total_chunks", 0)
    }


@app.get("/api/video/upload/{video_id}")
async def stream_uploaded_video(video_id: str, user=Depends(auth.get_current_user)):
    """
    Stream an uploaded video file for playback.
    """
    # Try different video extensions
    base_path = os.path.join(DATA_DIR, video_id)
    possible_extensions = ['.mp4', '.webm', '.mkv', '.avi', '.mov', '.m4v']
    
    video_path = None
    for ext in possible_extensions:
        test_path = base_path + ext
        if os.path.exists(test_path):
            video_path = test_path
            break
    
    if not video_path:
        raise HTTPException(404, "Video not found")
    
    # Determine media type based on extension
    ext = os.path.splitext(video_path)[1].lower()
    media_types = {
        '.mp4': 'video/mp4',
        '.webm': 'video/webm',
        '.mkv': 'video/x-matroska',
        '.avi': 'video/x-msvideo',
        '.mov': 'video/quicktime',
        '.m4v': 'video/x-m4v'
    }
    media_type = media_types.get(ext, 'video/mp4')
    
    return FileResponse(video_path, media_type=media_type)


@app.post("/api/video/transcribe/{video_id}")
async def transcribe_youtube_video(video_id: str, user=Depends(auth.get_current_user)):
    """
    Transcribe a YouTube video with Whisper and identify solution segments using OpenAI.
    Downloads the video, transcribes it, and highlights solution parts.
    
    Returns:
    - video_url: URL to stream/download the video
    - segments: List of transcript segments with timestamps
    - solution_segments: List of segment indices that contain solutions (highlighted)
    - full_transcript: Full transcript text
    """
    import tempfile
    import shutil
    import json
    import time
    
    # #region agent log
    log_path = os.path.join(BASE_DIR, '.cursor', 'debug.log')
    try:
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"ENTRY","location":"main.py:437","message":"transcribe_youtube_video endpoint called","data":{"video_id":video_id},"timestamp":int(time.time()*1000)})+'\n')
        logger.info(f"DEBUG: Logged entry point for video_id={video_id}")
    except Exception as log_err:
        logger.error(f"Log write failed: {log_err}", exc_info=True)
    # #endregion
    
    video_url = f"https://youtube.com/watch?v={video_id}"
    video_path = None
    
    try:
        logger.info(f"Starting transcription for video: {video_id}")
        
        # Step 1: Download video (check for existing file with any extension)
        base_path = os.path.join(DATA_DIR, video_id)
        possible_extensions = ['.mp4', '.webm', '.mkv', '.avi']
        video_path = None
        
        # Check if video already exists
        for ext in possible_extensions:
            test_path = base_path + ext
            if os.path.exists(test_path):
                video_path = test_path
                logger.info(f"Using cached video: {video_path}")
                break
        
        # Download if not found - try multiple methods to get video for Whisper transcription
        if not video_path:
            video_path = base_path + '.mp4'  # Default extension
            logger.info(f"Downloading video: {video_id}")
            download_success = False
            
            # Method 1: Try full video download
            try:
                logger.info("Attempting full video download...")
                downloaded_path = youtube_download.download_youtube_video(video_url, video_path, try_audio_only=False)
                video_path = downloaded_path
                download_success = True
                logger.info(f"✅ Full video download succeeded: {video_path}")
            except Exception as full_download_error:
                error_msg = str(full_download_error)
                logger.warning(f"Full video download failed: {error_msg[:100]}")
                
                # Method 2: Try audio-only download (easier, less likely to be blocked, sufficient for Whisper)
                try:
                    logger.info("Attempting audio-only download for transcription...")
                    audio_path = base_path + '.m4a'
                    downloaded_path = youtube_download.download_youtube_video(video_url, audio_path, try_audio_only=True)
                    video_path = downloaded_path
                    download_success = True
                    logger.info(f"✅ Audio-only download succeeded: {video_path}")
                except Exception as audio_download_error:
                    error_msg = str(audio_download_error)
                    logger.warning(f"Audio-only download also failed: {error_msg[:100]}")
                    download_error = audio_download_error
            
            if not download_success:
                error_msg = str(download_error)
                logger.error(f"Both full video and audio-only downloads failed. Last error: {error_msg}")
                
                # Always try to use YouTube transcript API as fallback when download fails
                # This handles bot detection, network errors, and other download issues
                logger.info("Attempting to use YouTube Transcript API as fallback...")
                # #region agent log
                log_path = os.path.join(BASE_DIR, '.cursor', 'debug.log')
                try:
                    os.makedirs(os.path.dirname(log_path), exist_ok=True)
                    with open(log_path, 'a', encoding='utf-8') as f:
                        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"F","location":"main.py:482","message":"Fallback to transcript API","data":{"error_msg":error_msg},"timestamp":int(time.time()*1000)})+'\n')
                except Exception as log_e:
                    logger.error(f"DEBUG LOG ERROR: {log_e}")
                # #endregion
                
                # Initialize transcript_data before try block
                transcript_data = None
                try:
                    logger.info(f"Attempting to fetch transcript for video: {video_id}")
                    transcript_data = video_transcript_analyzer.get_video_transcript(video_url)
                    if transcript_data:
                        logger.info(f"Successfully fetched transcript: {len(transcript_data)} segments")
                    else:
                        logger.warning(f"Transcript fetch returned None for video: {video_id}")
                except Exception as transcript_error:
                    logger.error(f"YouTube Transcript API error: {transcript_error}", exc_info=True)
                    transcript_data = None
                
                # #region agent log
                log_path = os.path.join(BASE_DIR, '.cursor', 'debug.log')
                try:
                    os.makedirs(os.path.dirname(log_path), exist_ok=True)
                    with open(log_path, 'a', encoding='utf-8') as f:
                        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"G","location":"main.py:485","message":"Transcript API response","data":{"has_transcript":transcript_data is not None,"transcript_len":len(transcript_data) if transcript_data else 0},"timestamp":int(time.time()*1000)})+'\n')
                except Exception as log_e:
                    logger.error(f"DEBUG LOG ERROR: {log_e}")
                # #endregion
                
                if transcript_data and len(transcript_data) > 0:
                        # Convert YouTube transcript format to our format
                        transcript_segments = []
                        full_transcript_lines = []
                        
                        for seg in transcript_data:
                            start = seg.get('start', 0)
                            duration = seg.get('duration', 0)
                            end = start + duration
                            text = seg.get('text', '').strip()
                            
                            transcript_segments.append({
                                "start": start,
                                "end": end,
                                "text": text,
                                "timestamp": f"{int(start // 60)}:{int(start % 60):02d}"
                            })
                            
                            full_transcript_lines.append(f"[{int(start // 60)}:{int(start % 60):02d}] {text}")
                        
                        full_transcript = "\n".join(full_transcript_lines)
                        
                        # Use OpenAI to identify solution segments
                        logger.info("Identifying solution segments with OpenAI...")
                        solution_prompt = f"""Analyze this video transcript and identify segments that contain solutions, explanations, or key teaching moments.

Transcript:
{full_transcript}

Return a JSON array of segment indices (0-based) that contain solutions or key explanations. Focus on segments that:
1. Explain how to solve problems
2. Show code implementations
3. Provide step-by-step instructions
4. Explain concepts clearly
5. Give practical examples

Skip segments that are:
- Introductions or greetings
- Filler words or pauses
- Off-topic discussions
- Outros or sign-offs

Return ONLY a JSON array like: [0, 5, 12, 23] or [] if no clear solutions found.
Do not include any other text, just the JSON array."""
                        
                        try:
                            solution_response = await get_gpt4o_response(solution_prompt)
                            import json
                            import re
                            
                            json_match = re.search(r'\[[\d,\s]*\]', solution_response or "")
                            if json_match:
                                solution_indices = json.loads(json_match.group())
                            else:
                                try:
                                    solution_indices = json.loads(solution_response)
                                except:
                                    solution_indices = []
                            
                            if not isinstance(solution_indices, list):
                                solution_indices = []
                            solution_indices = [int(i) for i in solution_indices if isinstance(i, (int, str)) and str(i).isdigit()]
                            solution_indices = [i for i in solution_indices if 0 <= i < len(transcript_segments)]
                        except Exception as e:
                            logger.warning(f"Failed to identify solution segments: {e}")
                            solution_indices = []
                        
                        # Return transcript-only response (video unavailable)
                        return {
                            "video_id": video_id,
                            "video_url": None,  # Video unavailable
                            "video_unavailable": True,
                            "video_unavailable_reason": "YouTube bot detection - video download blocked. Using transcript only.",
                            "youtube_embed_url": f"https://www.youtube.com/embed/{video_id}",
                            "segments": transcript_segments,
                            "solution_segments": solution_indices,
                            "full_transcript": full_transcript,
                            "duration": transcript_data[-1].get('start', 0) + transcript_data[-1].get('duration', 0) if transcript_data else 0,
                            "language": "unknown",
                            "total_segments": len(transcript_segments)
                        }
                
                # If transcript API also failed, return response with YouTube embed (no 503 error)
                logger.warning("Both video download and transcript API failed. Returning YouTube embed player as fallback.")
                # Always return a response with YouTube embed - never raise 503
                return {
                    "video_id": video_id,
                    "video_url": None,
                    "video_unavailable": True,
                    "video_unavailable_reason": f"Video download failed: {error_msg[:100]}. Transcript also unavailable. Showing YouTube embed player.",
                    "youtube_embed_url": f"https://www.youtube.com/embed/{video_id}",
                    "segments": [],
                    "solution_segments": [],
                    "full_transcript": "",
                    "duration": 0,
                    "language": "unknown",
                    "total_segments": 0,
                    "error_message": f"Video download and transcript both unavailable. You can still watch the video using the embedded player above."
                }
        
        # Step 2: Transcribe with Whisper
        logger.info("Transcribing video with Whisper...")
        model = get_whisper_model()
        result = model.transcribe(video_path, verbose=False)
        
        # Step 3: Format transcript segments
        transcript_segments = []
        full_transcript_lines = []
        
        for seg in result.get("segments", []):
            start = seg["start"]
            end = seg["end"]
            text = seg["text"].strip()
            
            transcript_segments.append({
                "start": start,
                "end": end,
                "text": text,
                "timestamp": f"{int(start // 60)}:{int(start % 60):02d}"
            })
            
            full_transcript_lines.append(f"[{int(start // 60)}:{int(start % 60):02d}] {text}")
        
        full_transcript = "\n".join(full_transcript_lines)
        
        # Step 4: Use OpenAI to identify solution segments
        logger.info("Identifying solution segments with OpenAI...")
        solution_prompt = f"""Analyze this video transcript and identify segments that contain solutions, explanations, or key teaching moments.

Transcript:
{full_transcript}

Return a JSON array of segment indices (0-based) that contain solutions or key explanations. Focus on segments that:
1. Explain how to solve problems
2. Show code implementations
3. Provide step-by-step instructions
4. Explain concepts clearly
5. Give practical examples

Skip segments that are:
- Introductions or greetings
- Filler words or pauses
- Off-topic discussions
- Outros or sign-offs

Return ONLY a JSON array like: [0, 5, 12, 23] or [] if no clear solutions found.
Do not include any other text, just the JSON array."""
        
        try:
            solution_response = await get_gpt4o_response(solution_prompt)
            # Try to extract JSON array from response
            import json
            import re
            
            # Find JSON array in response
            json_match = re.search(r'\[[\d,\s]*\]', solution_response or "")
            if json_match:
                solution_indices = json.loads(json_match.group())
            else:
                # Fallback: try to parse entire response as JSON
                try:
                    solution_indices = json.loads(solution_response)
                except:
                    solution_indices = []
            
            # Ensure solution_indices is a list of integers
            if not isinstance(solution_indices, list):
                solution_indices = []
            solution_indices = [int(i) for i in solution_indices if isinstance(i, (int, str)) and str(i).isdigit()]
            
            # Limit to valid indices
            solution_indices = [i for i in solution_indices if 0 <= i < len(transcript_segments)]
            
        except Exception as e:
            logger.warning(f"Failed to identify solution segments: {e}")
            solution_indices = []
        
        # Step 5: Prepare video URL for streaming
        # For now, we'll return the path that can be served via static files
        # In production, you might want to stream the video differently
        video_stream_url = f"/api/video/stream/{video_id}"
        
        logger.info(f"Transcription complete. Found {len(solution_indices)} solution segments.")
        
        return {
            "video_id": video_id,
            "video_url": video_stream_url,
            "segments": transcript_segments,
            "solution_segments": solution_indices,
            "full_transcript": full_transcript,
            "duration": result.get("duration", 0),
            "language": result.get("language", "unknown"),
            "total_segments": len(transcript_segments)
        }
        
    except Exception as e:
        logger.error(f"Video transcription error: {e}", exc_info=True)
        # Even on unexpected errors, try to return YouTube embed instead of error
        # This ensures users can still watch the video
        error_msg = str(e)
        return {
            "video_id": video_id,
            "video_url": None,
            "video_unavailable": True,
            "video_unavailable_reason": f"Unexpected error during transcription: {error_msg[:100]}",
            "youtube_embed_url": f"https://www.youtube.com/embed/{video_id}",
            "segments": [],
            "solution_segments": [],
            "full_transcript": "",
            "duration": 0,
            "language": "unknown",
            "total_segments": 0,
            "error_message": "An error occurred during transcription. You can still watch the video using the embedded player above."
        }


@app.get("/api/video/stream/{video_id}")
async def stream_video(video_id: str, user=Depends(auth.get_current_user)):
    """
    Stream a downloaded video file.
    """
    # Try different video extensions
    base_path = os.path.join(DATA_DIR, video_id)
    possible_extensions = ['.mp4', '.webm', '.mkv', '.avi']
    
    video_path = None
    for ext in possible_extensions:
        test_path = base_path + ext
        if os.path.exists(test_path):
            video_path = test_path
            break
    
    if not video_path:
        raise HTTPException(404, "Video not found. Please transcribe the video first.")
    
    # Determine media type based on extension
    media_types = {
        '.mp4': 'video/mp4',
        '.webm': 'video/webm',
        '.mkv': 'video/x-matroska',
        '.avi': 'video/x-msvideo'
    }
    ext = os.path.splitext(video_path)[1].lower()
    media_type = media_types.get(ext, 'video/mp4')
    
    return FileResponse(video_path, media_type=media_type)



# ---------------- CHAT ----------------
@app.post("/api/chat/advanced")
async def chat_advanced(req: ChatRequest, user=Depends(auth.get_current_user)):
    """
    Advanced Deterministic Code Analysis endpoint
    Returns strict JSON format as specified in requirements
    
    Format:
    {
      "code_type": "",
      "specific_pattern_or_algorithm": "",
      "confidence": "high | medium | low",
      "errors_detected": [{"type": "", "description": ""}],
      "solution": {"fixed_code": "", "explanation": ""},
      "videos": [{
        "title": "",
        "video_id": "",
        "start_time": 0,
        "end_time": 0,
        "key_solution_segments": [{"start": 0, "end": 0, "transcript": ""}]
      }]
    }
    """
    if not req.code:
        raise HTTPException(400, "Code is required for advanced analysis")
    
    logger.info(f"Advanced analysis requested by {user.get('username', 'unknown')}")
    
    # Perform advanced analysis
    analysis_result = advanced_code_analyzer.analyze_code(
        code=req.code,
        error_message=req.message,
        user_message=req.message
    )
    
    # Enhance videos with actual YouTube search and transcript extraction
    code_type = analysis_result["code_type"]
    specific_pattern = analysis_result["specific_pattern_or_algorithm"]
    confidence = analysis_result["confidence"]
    
    # Only search for videos if we have a clear pattern (not edge case)
    if code_type != "edge_case" and specific_pattern != "Uncertain" and confidence != "low":
        # Build search query based on pattern type
        if code_type == "algorithm":
            video_query = f"{specific_pattern} algorithm tutorial implementation"
        elif code_type == "design_pattern":
            video_query = f"{specific_pattern} design pattern tutorial"
        elif code_type == "system_server":
            video_query = f"{specific_pattern} server system tutorial"
        else:
            video_query = f"{specific_pattern} programming tutorial"
        
        # Search YouTube
        raw_videos = await search_youtube(video_query)
        
        # Process videos and extract key solution segments
        enhanced_videos = []
        for vid in raw_videos[:3]:  # Limit to 2-3 videos as specified
            video_url = vid.get("url", "")
            video_id = video_transcript_analyzer.extract_video_id(video_url)
            
            if not video_id:
                continue
            
            # Get transcript
            transcript = video_transcript_analyzer.get_video_transcript(video_url)
            
            # Extract key solution segments
            pattern_keywords = [specific_pattern.lower()] + specific_pattern.lower().split("_")
            key_segments = []
            
            if transcript:
                key_segments = advanced_code_analyzer.extract_key_solution_segments(
                    transcript, pattern_keywords
                )
            
            # Find overall solution time range
            start_time = 0
            end_time = 0
            if key_segments:
                start_time = min(seg["start"] for seg in key_segments)
                end_time = max(seg["end"] for seg in key_segments)
            elif transcript and len(transcript) > 0:
                # Use first 2 minutes if no key segments found
                end_time = min(120, transcript[-1]['start'] + transcript[-1].get('duration', 5))
            else:
                # No transcript available
                continue  # Skip videos without transcripts
            
            enhanced_videos.append({
                "title": vid.get("title", ""),
                "video_id": video_id,
                "start_time": int(start_time),
                "end_time": int(end_time),
                "key_solution_segments": key_segments
            })
        
        analysis_result["videos"] = enhanced_videos
    else:
        # Edge case - return general videos or empty
        analysis_result["videos"] = []
    
    return analysis_result


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, user=Depends(auth.get_current_user)):
    """
    ENHANCED Pattern Intelligence Layer - Chat endpoint
    PRIMARY PATTERN FIRST - MANDATORY RULE ENFORCEMENT
    
    If use_advanced_analysis is True, uses advanced deterministic analysis
    """
    # Check if advanced analysis is requested
    if req.use_advanced_analysis and req.code:
        logger.info("Using advanced analysis mode")
        # Use advanced analyzer but convert to ChatResponse format
        advanced_result = advanced_code_analyzer.analyze_code(
            code=req.code,
            error_message=req.message,
            user_message=req.message
        )
        
        # Convert to ChatResponse format
        return ChatResponse(
            primary_pattern=advanced_result["specific_pattern_or_algorithm"],
            primary_pattern_explanation=advanced_result["solution"]["explanation"],
            secondary_issues=[err["description"] for err in advanced_result["errors_detected"]],
            pattern_name=advanced_result["specific_pattern_or_algorithm"],
            pattern_explanation=advanced_result["solution"]["explanation"],
            confidence_score=90.0 if advanced_result["confidence"] == "high" else 70.0 if advanced_result["confidence"] == "medium" else 50.0,
            learning_intent=f"Understanding {advanced_result['code_type']} - {advanced_result['specific_pattern_or_algorithm']}",
            explanation=advanced_result["solution"]["explanation"],
            corrected_code=advanced_result["solution"]["fixed_code"],
            github_repos=[],
            stackoverflow_links=[],
            dev_articles=[],
            video_segments=[],
            video_skip_reasons=[],
            debugging_insight={"root_cause": "See errors_detected", "faulty_assumption": "", "correct_flow": ""},
            links=[],
            youtube_videos=[],
            error_analysis=None
        )
    
    print(f"\n{'='*60}")
    print(f"🧠 ENHANCED PATTERN INTELLIGENCE SYSTEM")
    print(f"{'='*60}")
    print(f"User: {user.get('username', 'unknown')}")
    print(f"Message: {req.message[:100]}...")
    
    # Step 1: PRIMARY/SECONDARY Pattern Detection (RULE ENFORCED)
    print("\n[1/7] 🔍 Detecting PRIMARY + SECONDARY patterns...")
    pattern_result = pattern_detector.detect_primary_and_secondary_patterns(
        code=req.code,
        error_message=req.message,
        user_message=req.message
    )
    
    primary_pattern_key = pattern_result["primary_pattern"]
    primary_pattern_name = pattern_result["primary_pattern_name"]
    secondary_issues = pattern_result["secondary_issues"]
    confidence = pattern_result["confidence"]
    learning_intent = pattern_detector.get_learning_intent(primary_pattern_key)
    
    print(f"   ✓ PRIMARY: {primary_pattern_name} (confidence: {confidence}%)")
    print(f"   ✓ SECONDARY: {secondary_issues if secondary_issues else 'None'}")
    
    # Step 2: Pattern Explanation
    print("[2/7] 📝 Generating pattern explanation...")
    pattern_explanation = pattern_detector.generate_pattern_explanation(
        pattern_key=primary_pattern_key,
        code=req.code,
        error=req.message
    )
    print(f"   ✓ Explanation generated")
    
    # Step 3: Generate Solution
    print("[3/7] 💡 Generating pattern-based solution...")
    corrected_code = None
    if req.code:
        corrected_code = pattern_detector.get_pattern_solution(
            pattern_key=primary_pattern_key,
            code=req.code
        )
    print(f"   ✓ Solution generated")
    
    # Step 4: External Knowledge Search
    print("[4/7] 🌐 Searching external knowledge...")
    search_query = pattern_detector.map_pattern_to_search_query(primary_pattern_key)
    external_knowledge = knowledge_search.get_external_knowledge(search_query)
    print(f"   ✓ Found {len(external_knowledge['github_repos'])} repos, "
          f"{len(external_knowledge['stackoverflow_threads'])} SO threads, "
          f"{len(external_knowledge['dev_articles'])} articles")
    
    # Step 5: Video Search with TRANSCRIPT-BASED TIMESTAMP EXTRACTION
    print("[5/7] 🎥 Finding pattern-specific video segments with TRANSCRIPT ANALYSIS...")
    video_query = f"{primary_pattern_name} tutorial solution"
    raw_videos = await search_youtube(video_query)
    
    video_segments = []
    video_skip_reasons = []
    pattern_keywords = pattern_detector.get_pattern_keywords(primary_pattern_key)
    
    for vid in raw_videos[:3]:  # Limit to top 3
        video_url = vid.get("url", "")
        video_title = vid.get("title", "Video")
        
        # Check if transcript/audio available
        has_transcript, skip_reason = video_transcript_analyzer.check_audio_availability(video_url)
        
        # Try to extract timestamps if transcript is available
        timestamps = None
        if has_transcript:
            try:
                timestamps = video_transcript_analyzer.extract_solution_timestamps(
                    video_url=video_url,
                    pattern_name=primary_pattern_name,
                    pattern_keywords=pattern_keywords
                )
            except Exception as e:
                logger.warning(f"Failed to extract timestamps from {video_url}: {e}")
                has_transcript = False
                skip_reason = f"Timestamp extraction failed: {str(e)[:50]}"
        
        # Extract video ID for embedding
        video_id = video_transcript_analyzer.extract_video_id(video_url)
        
        # Add video even if transcript is not available (but note it)
        if timestamps:
            # Video with timestamps - full featured
            video_segments.append(VideoSegment(
                title=video_title,
                url=video_url,
                video_id=video_id,
                thumbnail=vid.get("thumbnail"),
                channel=vid.get("channel"),
                start_time=timestamps["start_formatted"],
                end_time=timestamps["end_formatted"],
                relevance_note=f"Covers {primary_pattern_name} solution ({timestamps['confidence']} confidence)",
                transcript_text=timestamps.get("transcript_text", ""),
                highlighted_portion=timestamps.get("highlighted_portion", "")
            ))
            print(f"   ✓ Extracted: [{timestamps['start_formatted']} - {timestamps['end_formatted']}]")
        elif has_transcript:
            # Video has transcript but pattern not found - still show it
            video_segments.append(VideoSegment(
                title=video_title,
                url=video_url,
                video_id=video_id,
                thumbnail=vid.get("thumbnail"),
                channel=vid.get("channel"),
                start_time=None,
                end_time=None,
                relevance_note=f"Video about {primary_pattern_name} (no specific timestamps found)",
                transcript_text="",
                highlighted_portion=""
            ))
            print(f"   ✓ Added video (no timestamps found)")
        else:
            # No transcript - still show video but note it
            video_segments.append(VideoSegment(
                title=video_title,
                url=video_url,
                video_id=video_id,
                thumbnail=vid.get("thumbnail"),
                channel=vid.get("channel"),
                start_time=None,
                end_time=None,
                relevance_note=f"Video about {primary_pattern_name} (transcript unavailable - watch full video)",
                transcript_text="",
                highlighted_portion=""
            ))
            video_skip_reasons.append(f"{video_title[:50]}... - {skip_reason}")
            print(f"   ⚠️  Added video without transcript: {skip_reason}")
    
    print(f"   ✓ Processed {len(video_segments)} videos, skipped {len(video_skip_reasons)}")
    
    # Step 6: Debugging Insights
    print("[6/7] 🐛 Generating debugging insights...")
    debugging_insight = debug_analyzer.generate_debug_insight(
        pattern_name=primary_pattern_name,
        code=req.code,
        error_message=req.message,
        user_message=req.message
    )
    print(f"   ✓ Debugging insight generated")
    
    # Step 7: Assemble Response
    print("[7/7] 📦 Assembling comprehensive response...")
    print(f"\n{'='*60}")
    print(f"✅ ENHANCED PATTERN INTELLIGENCE RESPONSE READY")
    print(f"{'='*60}\n")
    
    return ChatResponse(
        # PRIMARY Pattern (ALWAYS FIRST - Rule Enforced)
        primary_pattern=primary_pattern_name,
        primary_pattern_explanation=pattern_explanation,
        
        # Secondary Issues (syntax, types, etc.)
        secondary_issues=secondary_issues,
        
        # Pattern Intelligence (Legacy compatibility)
        pattern_name=primary_pattern_name,
        pattern_explanation=pattern_explanation,
        confidence_score=confidence,
        learning_intent=learning_intent,
        
        # Solutions
        explanation=f"**PRIMARY PATTERN:** {primary_pattern_name}\n\n{pattern_explanation}",
        corrected_code=corrected_code,
        
        # External Knowledge
        github_repos=external_knowledge["github_repos"],
        stackoverflow_links=external_knowledge["stackoverflow_threads"],
        dev_articles=external_knowledge["dev_articles"],
        
        # Video Segments (with REAL timestamps from transcripts)
        video_segments=video_segments,
        video_skip_reasons=video_skip_reasons,  # TRANSPARENCY
        
        # Debugging Insights
        debugging_insight=debugging_insight,
        
        # Legacy fields (for backward compatibility)
        links=[],
        youtube_videos=raw_videos,
        error_analysis=debugging_insight.get("root_cause", None)
    )

# ---------------- FRONTEND ----------------
if os.path.exists(DIST_DIR):
    print(f"✅ dist_build found at {DIST_DIR}")
    print("Files:", os.listdir(DIST_DIR))
    app.mount("/", StaticFiles(directory=DIST_DIR, html=True), name="frontend")
else:
    print(f"⚠️ dist_build not found at {DIST_DIR}")
    print("Contents of backend:", os.listdir(BASE_DIR))

@app.get("/favicon.ico")
async def favicon():
    return RedirectResponse("https://www.google.com/favicon.ico")

# ---------------- RUN ----------------
if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))

