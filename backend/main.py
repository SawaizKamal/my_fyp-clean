import sys, os, uuid, re
from enum import Enum
from typing import List, Optional, Dict
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
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
from config import OPENAI_API_KEY, YOUTUBE_API_KEY
import pattern_detector
import knowledge_search
import debug_analyzer
import video_transcript_analyzer
from openai import OpenAI
OPENAI_CLIENT = OpenAI(api_key=OPENAI_API_KEY)

import whisper
from googleapiclient.discovery import build

# ---------------- APP ----------------
# Initialize DB
database.init_db()

app = FastAPI()

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
    allow_origins=["*"],
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
    if not YOUTUBE_API_KEY:
        print("⚠️ YOUTUBE_API_KEY not set - using fallback video recommendations")
        # Fallback: Return static pattern-based videos when API key not available
        # These are educational programming videos that cover common patterns
        return [
            {
                "title": f"Tutorial: {query}",
                "url": "https://youtube.com/watch?v=dQw4w9WgXcQ",  # Placeholder
                "thumbnail": "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
                "channel": "Educational Programming"
            },
            {
                "title": f"Understanding {query.split()[0] if query else 'Programming Patterns'}",
                "url": "https://youtube.com/watch?v=dQw4w9WgXcQ",  # Placeholder
                "thumbnail": "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
                "channel": "Code Academy"
            },
            {
                "title": f"Best Practices for {query.split()[0] if query else 'Coding'}",
                "url": "https://youtube.com/watch?v=dQw4w9WgXcQ",  # Placeholder
                "thumbnail": "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
                "channel": "Dev Tips"
            }
        ]
    
    youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
    res = youtube.search().list(q=query, part="snippet", type="video", maxResults=3).execute()
    return [
        {
            "title": i["snippet"]["title"],
            "url": f"https://youtube.com/watch?v={i['id']['videoId']}",
            "thumbnail": i["snippet"]["thumbnails"]["high"]["url"],
            "channel": i["snippet"]["channelTitle"],
        } for i in res["items"]
    ]

# ---------------- VIDEO TASK ----------------
async def process_video_task(task_id, url, goal):
    try:
        tasks[task_id] = {"status": TaskStatus.DOWNLOADING}
        video_path = os.path.join(DATA_DIR, f"{task_id}.mp4")
        real_path = youtube_download.download_youtube_video(url, video_path)

        tasks[task_id] = {"status": TaskStatus.TRANSCRIBING}
        model = whisper.load_model("base")
        result = model.transcribe(real_path)

        script = "\n".join(
            f"[{s['start']:.2f} - {s['end']:.2f}] {s['text']}" for s in result["segments"]
        )

        tasks[task_id] = {"status": TaskStatus.FILTERING}
        prompt = f"Goal: {goal}\nTranscript:\n{script}\nReturn timestamps only."
        filtered = await get_gpt4o_response(prompt)

        segments = parse_segments(filtered or "")
        if not segments:
            raise Exception("No segments found")

        tasks[task_id] = {"status": TaskStatus.COMPILING}
        output = os.path.join(OUTPUT_DIR, f"{task_id}.mp4")
        video_compile.makeVideo(segments, real_path, output)

        tasks[task_id] = {"status": TaskStatus.COMPLETED, "output_path": output}

    except Exception as e:
        tasks[task_id] = {"status": TaskStatus.FAILED, "error": str(e)}
        print("PROCESS ERROR:", e)

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
@app.post("/api/process")
async def process(req: ProcessRequest, bg: BackgroundTasks, user=Depends(auth.get_current_user)):
    task_id = str(uuid.uuid4())
    tasks[task_id] = {"status": TaskStatus.PENDING}
    url = f"https://youtube.com/watch?v={req.video_id}"
    bg.add_task(process_video_task, task_id, url, req.goal)
    return {"task_id": task_id}

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
        
        # Check if transcript/audio available (MANDATORY RULE)
        has_transcript, skip_reason = video_transcript_analyzer.check_audio_availability(video_url)
        
        if not has_transcript:
            # SKIP video and record reason (TRANSPARENCY)
            video_skip_reasons.append(f"{vid.get('title', 'Video')[:50]}... - {skip_reason}")
            print(f"   ⏭️  Skipped: {skip_reason}")
            continue
        
        # Extract timestamps using transcript analysis
        timestamps = video_transcript_analyzer.extract_solution_timestamps(
            video_url=video_url,
            pattern_name=primary_pattern_name,
            pattern_keywords=pattern_keywords
        )
        
        if timestamps:
            video_segments.append(VideoSegment(
                title=vid.get("title", ""),
                url=video_url,
                thumbnail=vid.get("thumbnail"),
                channel=vid.get("channel"),
                start_time=timestamps["start_formatted"],
                end_time=timestamps["end_formatted"],
                relevance_note=f"Covers {primary_pattern_name} solution ({timestamps['confidence']} confidence)",
                transcript_text=timestamps.get("transcript_text", ""),  # Full transcript
                highlighted_portion=timestamps.get("highlighted_portion", "")  # Highlighted solution
            ))
            print(f"   ✓ Extracted: [{timestamps['start_formatted']} - {timestamps['end_formatted']}]")
        else:
            video_skip_reasons.append(f"{vid.get('title', '')[:50]}... - Pattern not found in transcript")
    
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

