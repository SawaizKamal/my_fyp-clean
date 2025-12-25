import sys, os, uuid, re
from enum import Enum
from typing import List, Optional, Dict
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, File, UploadFile
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

class VideoSegment(BaseModel):
    title: str
    url: str
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
async def transcribe_local_video(file: UploadFile = File(...), user=Depends(auth.get_current_user)):
    """
    Transcribe a locally uploaded video file.
    Accepts video file upload and returns transcript with timestamps.
    Max file size: 500MB
    """
    import tempfile
    import shutil
    
    # Validate file type
    if not file.content_type or not file.content_type.startswith('video/'):
        raise HTTPException(400, "File must be a video")
    
    # File size limit: 500MB (for transcription)
    MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB
    
    # Save uploaded file temporarily with size checking
    temp_path = None
    file_size = 0
    try:
        # Read file content first to check size
        content = await file.read()
        file_size = len(content)
        
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(400, f"File too large. Maximum size is {MAX_FILE_SIZE / (1024*1024):.0f}MB")
        
        # Write to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp_file:
            temp_path = tmp_file.name
            tmp_file.write(content)
        
        logger.info(f"Transcribing local video: {file.filename}")
        
        # Use cached Whisper model
        model = get_whisper_model()
        result = model.transcribe(temp_path, verbose=False)
        
        # Format transcript with timestamps
        transcript_segments = [
            {
                "start": seg["start"],
                "end": seg["end"],
                "text": seg["text"].strip(),
                "timestamp": f"[{seg['start']:.2f} - {seg['end']:.2f}]"
            }
            for seg in result.get("segments", [])
        ]
        
        full_transcript = "\n".join(
            f"[{seg['start']:.2f} - {seg['end']:.2f}] {seg['text']}" 
            for seg in result.get("segments", [])
        )
        
        return {
            "filename": file.filename,
            "segments": transcript_segments,
            "full_transcript": full_transcript,
            "duration": result.get("duration", 0),
            "language": result.get("language", "unknown")
        }
        
    except Exception as e:
        logger.error(f"Transcription error: {e}", exc_info=True)
        raise HTTPException(500, f"Transcription failed: {str(e)}")
    finally:
        # Clean up temporary file
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except:
                pass



# ---------------- CHAT ----------------
@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, user=Depends(auth.get_current_user)):
    """
    ENHANCED Pattern Intelligence Layer - Chat endpoint
    PRIMARY PATTERN FIRST - MANDATORY RULE ENFORCEMENT
    """
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
        
        # Add video even if transcript is not available (but note it)
        if timestamps:
            # Video with timestamps - full featured
            video_segments.append(VideoSegment(
                title=video_title,
                url=video_url,
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

