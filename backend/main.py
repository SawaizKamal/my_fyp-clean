import sys, os, uuid, re, json
from enum import Enum
from typing import List, Optional, Dict
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, File, UploadFile, Form, Request, Query
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

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------- APP ----------------
# Initialize DB
database.init_db()

app = FastAPI()

# ---------------- CACHED MODELS ----------------
# Cache Whisper model to avoid reloading on each request
_whisper_model_cache = None

def get_whisper_model():
    """Get cached Whisper model or load it if not cached"""
    global _whisper_model_cache
    if _whisper_model_cache is None:
        logger.info("Loading Whisper model (first time)...")
        _whisper_model_cache = whisper.load_model("base")
        logger.info("Whisper model loaded and cached")
    return _whisper_model_cache

@app.get("/api/health")
def health():
    try:
        # Check DB connection
        with database.engine.connect() as conn:
            conn.execute(database.text("SELECT 1"))
        return {"status": "ok", "database": "connected", "model": "gpt-4o"}
    except Exception as e:
        return {"status": "error", "database": str(e)}

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
async def get_gpt4o_response(prompt: str, temperature: float = 0.3):
    """
    Get response from GPT-4o model.
    Lower temperature (0.3) for more deterministic, focused responses.
    """
    try:
        res = OPENAI_CLIENT.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=3000,
            temperature=temperature
        )
        return res.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"GPT ERROR: {e}", exc_info=True)
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
    """Background task to transcribe uploaded video"""
    try:
        logger.info(f"Starting transcription task: {task_id} for video: {video_id}")
        tasks[task_id] = {"status": TaskStatus.UPLOADING, "progress": 10}
        
        # Verify file exists
        if not os.path.exists(video_path):
            raise Exception(f"Video file not found: {video_path}")
        
        tasks[task_id] = {"status": TaskStatus.TRANSCRIBING, "progress": 20}
        logger.info("Loading Whisper model...")
        model = get_whisper_model()
        logger.info("Starting transcription...")
        result = model.transcribe(video_path, verbose=False, condition_on_previous_text=False)
        logger.info(f"Transcription complete. Found {len(result.get('segments', []))} segments")
        
        tasks[task_id] = {"status": TaskStatus.TRANSCRIBING, "progress": 60}
        
        # Format transcript with timestamps
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
        logger.info(f"Formatted transcript with {len(transcript_segments)} segments")
        
        tasks[task_id] = {"status": TaskStatus.FILTERING, "progress": 80}
        
        # Use GPT-4 to identify solution segments if user_query is provided
        solution_segments = []
        if user_query:
            logger.info(f"Identifying solution segments using GPT-4 for query: {user_query[:100]}")
            
            # Build transcript with clear, prominent index labels for better GPT accuracy
            indexed_transcript_lines = []
            for idx, seg in enumerate(transcript_segments):
                timestamp_str = seg['timestamp']
                text = seg['text']
                # Make index VERY clear and prominent to reduce indexing errors
                indexed_transcript_lines.append(f"SEGMENT_INDEX_{idx} | [{timestamp_str}] {text}")
            
            indexed_transcript = "\n".join(indexed_transcript_lines)
            
            solution_prompt = f"""You are an expert at identifying solution segments in educational video transcripts. Analyze the transcript below and identify ONLY the segments that directly contain solutions, explanations, or key teaching moments relevant to the user's question.

USER'S QUESTION/QUERY: "{user_query}"

TRANSCRIPT (each line format: SEGMENT_INDEX_X | [MM:SS] text):
Pay close attention to the SEGMENT_INDEX number at the start of each line - use this EXACT number in your response.

{indexed_transcript}

INSTRUCTIONS:
1. Read through ALL segments carefully
2. Identify segments by their SEGMENT_INDEX number (the number after SEGMENT_INDEX_) that DIRECTLY address the user's question
3. Use the EXACT SEGMENT_INDEX number as shown in the transcript above (e.g., if a line starts with "SEGMENT_INDEX_5", use 5 in your response)
4. Focus on segments that:
   - Explain HOW to solve the specific problem mentioned
   - Show code implementations, fixes, or corrections
   - Provide step-by-step instructions or procedures
   - Explain core concepts clearly related to the query
   - Give practical examples that directly answer the question
   - Contain actionable advice or solutions

5. EXCLUDE segments that:
   - Are introductions, greetings, or filler ("hey", "um", "let's get started")
   - Are off-topic or unrelated to the query
   - Are outros, sign-offs, or closing remarks
   - Only mention the problem without providing solutions
   - Are vague or don't add value to answering the question

6. Be PRECISE: Only include segments that genuinely contain solutions or explanations. Quality over quantity.

OUTPUT FORMAT:
Return ONLY a valid JSON array of SEGMENT_INDEX numbers (integers), nothing else.
Example valid responses: [2, 5, 12] or [0, 3, 7, 15] or []

CRITICAL: 
- Use the SEGMENT_INDEX numbers EXACTLY as shown in the transcript (the number after SEGMENT_INDEX_)
- Return ONLY the JSON array, no explanations, no markdown, no other text
- Do NOT use any numbering other than the SEGMENT_INDEX numbers provided"""
            
            try:
                solution_response = await get_gpt4o_response(solution_prompt, temperature=0.2)
                import json
                import re
                
                if not solution_response:
                    logger.warning("GPT-4o returned empty response for solution segments")
                    solution_segments = []
                else:
                    # Try multiple parsing strategies
                    solution_segments = []
                    
                    # Strategy 1: Look for JSON array pattern in response
                    json_match = re.search(r'\[[\d,\s]*\]', solution_response)
                    if json_match:
                        try:
                            solution_segments = json.loads(json_match.group())
                        except json.JSONDecodeError:
                            pass
                    
                    # Strategy 2: Try parsing entire response as JSON
                    if not solution_segments:
                        try:
                            parsed = json.loads(solution_response)
                            if isinstance(parsed, list):
                                solution_segments = parsed
                            elif isinstance(parsed, dict) and "segments" in parsed:
                                solution_segments = parsed["segments"]
                        except json.JSONDecodeError:
                            pass
                    
                    # Strategy 3: Extract numbers from response
                    if not solution_segments:
                        numbers = re.findall(r'\d+', solution_response)
                        solution_segments = [int(n) for n in numbers if n.isdigit()]
                    
                    # Validate and filter
                    if not isinstance(solution_segments, list):
                        solution_segments = []
                    solution_segments = [int(i) for i in solution_segments if isinstance(i, (int, str)) and str(i).isdigit()]
                    solution_segments = [i for i in solution_segments if 0 <= i < len(transcript_segments)]
                    # Remove duplicates and sort
                    solution_segments = sorted(list(set(solution_segments)))
                    
                    logger.info(f"Identified {len(solution_segments)} solution segments: {solution_segments[:10]}{'...' if len(solution_segments) > 10 else ''}")
                    if solution_response:
                        logger.debug(f"GPT-4o response preview: {solution_response[:200]}...")
            except Exception as e:
                logger.error(f"Failed to identify solution segments: {e}", exc_info=True)
                solution_segments = []
        
        # Store results in task
        video_url_value = f"/api/video/upload/{video_id}"
        # #region agent log
        import json
        import time
        log_path = os.path.join(BASE_DIR, '.cursor', 'debug.log')
        try:
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"main.py:425","message":"Setting video_url in task","data":{"task_id":task_id,"video_id":video_id,"video_url":video_url_value,"video_url_type":type(video_url_value).__name__},"timestamp":int(time.time()*1000)})+'\n')
        except Exception as log_err:
            logger.error(f"Log write failed: {log_err}", exc_info=True)
        # #endregion
        tasks[task_id] = {
            "status": TaskStatus.COMPLETED,
            "progress": 100,
            "video_id": video_id,
            "video_url": video_url_value,
            "filename": filename,
            "segments": transcript_segments,
            "solution_segments": solution_segments,
            "full_transcript": full_transcript,
            "duration": result.get("duration", 0),
            "language": result.get("language", "unknown"),
            "total_segments": len(transcript_segments)
        }
        logger.info(f"Transcription task {task_id} completed successfully")
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Transcription task error for {task_id}: {e}")
        logger.error(f"Full traceback: {error_details}")
        tasks[task_id] = {
            "status": TaskStatus.FAILED,
            "error": str(e),
            "progress": 0
        }

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

@app.get("/api/video/{video_id}")
async def video(video_id: str, token: Optional[str] = Query(None)):
    """
    Stream an uploaded video file for playback with range request support for seeking.
    Accepts authentication via token query parameter (for video elements).
    """
    # Validate token from query parameter
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    user = await auth.get_current_user_optional(token)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
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
    
    # FileResponse automatically handles Range requests for video seeking
    # Explicitly set Accept-Ranges header to ensure browsers can seek properly
    return FileResponse(
        video_path, 
        media_type=media_type,
        headers={
            "Accept-Ranges": "bytes"
        }
    )


@app.post("/api/transcribe/local")
async def transcribe_local_video(
    file: UploadFile = File(...),
    user_query: Optional[str] = Form(None),
    bg: BackgroundTasks = BackgroundTasks(),
    user=Depends(auth.get_current_user)
):
    """
    Transcribe a locally uploaded video file with GPT-4 solution segment detection.
    Uses background tasks to avoid timeout on Render.
    Returns task_id immediately, use /api/transcribe/status/{task_id} to check progress.
    Max file size: 500MB
    
    Args:
        file: Video file to upload
        user_query: Optional query/question to help identify solution segments
    """
    # Validate file type
    if not file.content_type or not file.content_type.startswith('video/'):
        raise HTTPException(400, "File must be a video")
    
    # File size limit: 500MB (for transcription)
    MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB
    
    # Generate IDs
    task_id = str(uuid.uuid4())
    video_id = str(uuid.uuid4())
    
    # Preserve original file extension if available, otherwise default to .mp4
    original_filename = file.filename or "video"
    file_extension = os.path.splitext(original_filename)[1] or ".mp4"
    video_path = os.path.join(DATA_DIR, f"{video_id}{file_extension}")
    
    try:
        logger.info(f"Received video upload request: {file.filename}, content_type: {file.content_type}")
        
        # Read file content first to check size
        content = await file.read()
        file_size = len(content)
        logger.info(f"File size: {file_size} bytes ({file_size / (1024*1024):.2f} MB)")
        
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(400, f"File too large. Maximum size is {MAX_FILE_SIZE / (1024*1024):.0f}MB")
        
        if file_size == 0:
            raise HTTPException(400, "Uploaded file is empty")
        
        # Save video file for later playback
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(video_path, 'wb') as f:
            f.write(content)
        
        logger.info(f"Video saved to: {video_path}")
        logger.info(f"Video file exists: {os.path.exists(video_path)}")
        logger.info(f"Video file size on disk: {os.path.getsize(video_path) if os.path.exists(video_path) else 0} bytes")
        
        # Initialize task status
        tasks[task_id] = {"status": TaskStatus.PENDING, "progress": 0}
        
        # Start background transcription task
        bg.add_task(transcribe_uploaded_video_task, task_id, video_path, video_id, file.filename, user_query)
        logger.info(f"Transcription task {task_id} started for video {video_id}")
        
        # Return task_id immediately (non-blocking)
        return {
            "task_id": task_id,
            "status": "pending",
            "message": "Video uploaded. Transcription in progress. Use /api/transcribe/status/{task_id} to check progress."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Video upload error: {e}")
        logger.error(f"Full traceback: {error_details}")
        # Clean up video file on error
        if os.path.exists(video_path):
            try:
                os.unlink(video_path)
            except:
                pass
        raise HTTPException(500, f"Upload failed: {str(e)}")


@app.get("/api/transcribe/status/{task_id}")
async def get_transcription_status(task_id: str, user=Depends(auth.get_current_user)):
    """
    Get transcription status and results for a task.
    Returns the full transcript data when status is 'completed'.
    """
    # #region agent log
    import json
    import time
    log_path = os.path.join(BASE_DIR, '.cursor', 'debug.log')
    try:
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"AUTH","location":"main.py:642","message":"Status endpoint reached","data":{"task_id":task_id,"user_authenticated":user is not None,"username":user.get("username") if user else None},"timestamp":int(time.time()*1000)})+'\n')
    except Exception:
        pass
    # #endregion
    if task_id not in tasks:
        raise HTTPException(404, "Task not found")
    
    task = tasks[task_id]
    
    # If completed, return full results
    if task.get("status") == TaskStatus.COMPLETED:
        response_data = {
            "task_id": task_id,
            "status": "completed",
            "progress": task.get("progress", 100),
            "video_id": task.get("video_id"),
            "video_url": task.get("video_url"),
            "filename": task.get("filename"),
            "segments": task.get("segments", []),
            "solution_segments": task.get("solution_segments", []),
            "full_transcript": task.get("full_transcript", ""),
            "duration": task.get("duration", 0),
            "language": task.get("language", "unknown"),
            "total_segments": task.get("total_segments", 0)
        }
        # #region agent log
        import json
        import time
        log_path = os.path.join(BASE_DIR, '.cursor', 'debug.log')
        try:
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"main.py:660","message":"Status endpoint returning video_url","data":{"task_id":task_id,"video_url":response_data.get("video_url"),"video_url_type":type(response_data.get("video_url")).__name__,"video_id":response_data.get("video_id")},"timestamp":int(time.time()*1000)})+'\n')
        except Exception as log_err:
            logger.error(f"Log write failed: {log_err}", exc_info=True)
        # #endregion
        return response_data
    
    # If failed, return error
    if task.get("status") == TaskStatus.FAILED:
        return {
            "task_id": task_id,
            "status": "failed",
            "error": task.get("error", "Unknown error"),
            "progress": task.get("progress", 0)
        }
    
    # Otherwise return current status
    return {
        "task_id": task_id,
        "status": task.get("status", "pending"),
        "progress": task.get("progress", 0)
    }


@app.get("/api/video/upload/{video_id}")
async def stream_uploaded_video(video_id: str, request: Request, token: Optional[str] = None):
    """
    Stream an uploaded video file for playback.
    Accepts authentication via Authorization header or token query parameter (for video elements).
    """
    # #region agent log
    import json
    import time
    log_path = os.path.join(BASE_DIR, '.cursor', 'debug.log')
    try:
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"E","location":"main.py:618","message":"Video stream endpoint called","data":{"video_id":video_id,"has_token_param":token is not None,"token_length":len(token) if token else 0},"timestamp":int(time.time()*1000)})+'\n')
    except Exception as log_err:
        logger.error(f"Log write failed: {log_err}", exc_info=True)
    # #endregion
    
    user = None
    
    # Try to get token from Authorization header first
    if request:
        auth_header = request.headers.get("Authorization")
        # #region agent log
        try:
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"E","location":"main.py:630","message":"Auth header check","data":{"has_auth_header":auth_header is not None,"auth_header_start":auth_header[:20] if auth_header else None},"timestamp":int(time.time()*1000)})+'\n')
        except Exception:
            pass
        # #endregion
        if auth_header and auth_header.startswith("Bearer "):
            header_token = auth_header.split("Bearer ")[1]
            user = await auth.get_current_user_optional(header_token)
    
    # If no user from header, try query parameter token
    if not user and token:
        # #region agent log
        try:
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"E","location":"main.py:637","message":"Trying query param token","data":{"has_token":True},"timestamp":int(time.time()*1000)})+'\n')
        except Exception:
            pass
        # #endregion
        user = await auth.get_current_user_optional(token)
    
    # #region agent log
    try:
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"E","location":"main.py:642","message":"Auth result","data":{"user_authenticated":user is not None,"has_username":user.get("username") if user else False},"timestamp":int(time.time()*1000)})+'\n')
    except Exception:
        pass
    # #endregion
    
    # Require authentication
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
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
                        logger.info("Identifying solution segments with OpenAI GPT-4o...")
                        solution_prompt = f"""You are an expert at analyzing educational video transcripts to identify solution segments. Your task is to find segments that contain actual solutions, explanations, or key teaching moments.

TRANSCRIPT (each line format: [MM:SS] text):
{full_transcript}

INSTRUCTIONS:
1. Carefully read through ALL transcript segments
2. Identify segments (by their 0-based index) that contain:
   - Step-by-step solutions to problems
   - Code implementations, fixes, or corrections
   - Clear explanations of how things work
   - Practical examples that demonstrate solutions
   - Actionable instructions or procedures
   - Key concepts explained in detail
   - Troubleshooting steps or fixes

3. EXCLUDE segments that are:
   - Introductions, greetings, or sign-offs ("hey", "welcome", "thanks for watching")
   - Filler words, pauses, or "um", "uh", "let me think"
   - Off-topic discussions or tangents
   - Questions without answers
   - Vague statements without substance
   - Outros or closing remarks

4. Be PRECISE: Only include segments that genuinely contain solutions or valuable explanations. Quality over quantity.

5. Consider context: A segment explaining "how to fix X" is more valuable than "I had a problem with X" without the solution.

OUTPUT FORMAT:
Return ONLY a valid JSON array of segment indices (0-based integers), nothing else.
Example valid responses: [2, 5, 12] or [0, 3, 7, 15] or []

CRITICAL: Return ONLY the JSON array, no explanations, no markdown formatting, no other text. Just the array."""
                        
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
        logger.info("Identifying solution segments with OpenAI GPT-4o...")
        solution_prompt = f"""You are an expert at analyzing educational video transcripts to identify solution segments. Your task is to find segments that contain actual solutions, explanations, or key teaching moments.

TRANSCRIPT (each line format: [MM:SS] text):
{full_transcript}

INSTRUCTIONS:
1. Carefully read through ALL transcript segments
2. Identify segments (by their 0-based index) that contain:
   - Step-by-step solutions to problems
   - Code implementations, fixes, or corrections
   - Clear explanations of how things work
   - Practical examples that demonstrate solutions
   - Actionable instructions or procedures
   - Key concepts explained in detail
   - Troubleshooting steps or fixes

3. EXCLUDE segments that are:
   - Introductions, greetings, or sign-offs ("hey", "welcome", "thanks for watching")
   - Filler words, pauses, or "um", "uh", "let me think"
   - Off-topic discussions or tangents
   - Questions without answers
   - Vague statements without substance
   - Outros or closing remarks

4. Be PRECISE: Only include segments that genuinely contain solutions or valuable explanations. Quality over quantity.

5. Consider context: A segment explaining "how to fix X" is more valuable than "I had a problem with X" without the solution.

OUTPUT FORMAT:
Return ONLY a valid JSON array of segment indices (0-based integers), nothing else.
Example valid responses: [2, 5, 12] or [0, 3, 7, 15] or []

CRITICAL: Return ONLY the JSON array, no explanations, no markdown formatting, no other text. Just the array."""
        
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
async def stream_video(video_id: str, request: Request, token: Optional[str] = None):
    """
    Stream a downloaded video file.
    Accepts authentication via Authorization header or token query parameter (for video elements).
    """
    user = None
    
    # Try to get token from Authorization header first
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        header_token = auth_header.split("Bearer ")[1]
        user = await auth.get_current_user_optional(header_token)
    
    # If no user from header, try query parameter token
    if not user and token:
        user = await auth.get_current_user_optional(token)
    
    # Require authentication
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
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
    print(f"[OK] dist_build found at {DIST_DIR}")
    print("Files:", os.listdir(DIST_DIR))
    app.mount("/", StaticFiles(directory=DIST_DIR, html=True), name="frontend")
else:
    print(f"[WARNING] dist_build not found at {DIST_DIR}")
    print("Contents of backend:", os.listdir(BASE_DIR))

@app.get("/favicon.ico")
async def favicon():
    return RedirectResponse("https://www.google.com/favicon.ico")

# ---------------- CODE PATTERN & ALGORITHM ANALYSIS ----------------
async def analyze_code_pattern_and_algorithm(code_snippet: str) -> Dict:
    """
    Analyze code snippet at cursor position to identify design patterns and algorithms.
    Uses specialized GPT prompt for pattern and algorithm detection.
    
    Args:
        code_snippet: Code snippet to analyze (from cursor position)
    
    Returns:
        Dict with "pattern" and "algorithm" fields (or "Unknown" if not identified)
    """
    prompt = """You are an expert code pattern and algorithm analyzer. The user will provide a code snippet corresponding to the current cursor position in their editor. Your task is to:

1. Identify any **Design Pattern(s)** present in the snippet (e.g., Singleton, Proxy, Observer, Factory, Strategy, etc.).
2. Identify any **Algorithm(s)** present in the snippet (e.g., Sorting, Searching, Graph algorithms, etc.).

Guidelines:
- Analyze only the code provided around the cursor.
- Ignore unrelated code, imports, or UI elements.
- Return results as a JSON object:
  {
    "pattern": "<pattern_name_or_Unknown>",
    "algorithm": "<algorithm_name_or_Unknown>"
  }
- If you cannot confidently identify a design pattern or algorithm, return "Unknown" for that field.
- Focus on behavior and structure, not just variable or function names.

**Code Snippet:**
```python
{code}
```

**Your Analysis (JSON only):**""".format(code=code_snippet)

    try:
        response = await get_gpt4o_response(prompt, temperature=0.3)
        
        if not response:
            return {"pattern": "Unknown", "algorithm": "Unknown"}
        
        # Try to parse JSON from response
        # Extract JSON from response (handle cases where GPT adds extra text)
        response_clean = response.strip()
        
        # Try to find JSON object in response
        json_start = response_clean.find('{')
        json_end = response_clean.rfind('}') + 1
        
        if json_start >= 0 and json_end > json_start:
            json_str = response_clean[json_start:json_end]
            try:
                result = json.loads(json_str)
                # Ensure both fields exist
                return {
                    "pattern": result.get("pattern", "Unknown"),
                    "algorithm": result.get("algorithm", "Unknown")
                }
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse JSON from GPT response: {json_str}")
        
        # Fallback: return Unknown if parsing fails
        return {"pattern": "Unknown", "algorithm": "Unknown"}
        
    except Exception as e:
        logger.error(f"Code pattern/algorithm analysis error: {e}", exc_info=True)
        return {"pattern": "Unknown", "algorithm": "Unknown"}


@app.post("/api/analyze/code-snippet")
async def analyze_code_snippet(req: ChatRequest, user=Depends(auth.get_current_user)):
    """
    Analyze code snippet at cursor position for design patterns and algorithms.
    
    Request:
    {
        "code": "code snippet here",
        "message": "optional context"
    }
    
    Response:
    {
        "pattern": "Singleton | Factory | Observer | Unknown",
        "algorithm": "QuickSort | BinarySearch | DFS | Unknown"
    }
    """
    if not req.code:
        raise HTTPException(400, "Code snippet is required")
    
    logger.info(f"Code snippet analysis requested by {user.get('username', 'unknown')}")
    
    result = await analyze_code_pattern_and_algorithm(req.code)
    return result

# ---------------- RUN ----------------
if __name__ == "__main__":
    # Use app directly instead of string path to avoid module import issues
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))

