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
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    relevance_note: Optional[str] = None

class ChatResponse(BaseModel):
    # Pattern Intelligence Fields
    pattern_name: str
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
        return []
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
    Pattern Intelligence Layer - Chat endpoint
    Detects problem patterns and provides targeted solutions
    """
    print(f"\n{'='*50}")
    print(f"🧠 PATTERN INTELLIGENCE SYSTEM")
    print(f"{'='*50}")
    print(f"User: {user.get('username', 'unknown')}")
    print(f"Message: {req.message[:100]}...")
    
    # Step 1: Pattern Detection
    print("\n[1/6] 🔍 Detecting pattern...")
    pattern_key, confidence = pattern_detector.detect_pattern(
        code=req.code,
        error_message=req.message,
        user_message=req.message
    )
    pattern_info = pattern_detector.PATTERN_LIBRARY.get(pattern_key, {})
    pattern_name = pattern_info.get("name", "Unknown Pattern")
    learning_intent = pattern_detector.get_learning_intent(pattern_key)
    
    print(f"   ✓ Pattern: {pattern_name} (confidence: {confidence}%)")
    
    # Step 2: Pattern Explanation
    print("[2/6] 📝 Generating pattern explanation...")
    pattern_explanation = pattern_detector.generate_pattern_explanation(
        pattern_key=pattern_key,
        code=req.code,
        error=req.message
    )
    print(f"   ✓ Explanation generated")
    
    # Step 3: Generate Solution
    print("[3/6] 💡 Generating pattern-based solution...")
    corrected_code = None
    if req.code:
        corrected_code = pattern_detector.get_pattern_solution(
            pattern_key=pattern_key,
            code=req.code
        )
    print(f"   ✓ Solution generated")
    
    # Step 4: External Knowledge Search
    print("[4/6] 🌐 Searching external knowledge...")
    search_query = pattern_detector.map_pattern_to_search_query(pattern_key)
    external_knowledge = knowledge_search.get_external_knowledge(search_query)
    print(f"   ✓ Found {len(external_knowledge['github_repos'])} repos, "
          f"{len(external_knowledge['stackoverflow_threads'])} SO threads, "
          f"{len(external_knowledge['dev_articles'])} articles")
    
    # Step 5: Video Segment Search with Timestamps
    print("[5/6] 🎥 Finding pattern-specific video segments...")
    video_query = f"{pattern_name} tutorial solution"
    raw_videos = await search_youtube(video_query)
    
    # Convert to VideoSegment format with timestamp placeholders
    video_segments = []
    for vid in raw_videos[:3]:  # Limit to top 3
        video_segments.append(VideoSegment(
            title=vid.get("title", ""),
            url=vid.get("url", ""),
            thumbnail=vid.get("thumbnail"),
            channel=vid.get("channel"),
            start_time=None,  # Would need transcript analysis for exact timestamps
            end_time=None,
            relevance_note=f"Covers {pattern_name}"
        ))
    print(f"   ✓ Found {len(video_segments)} relevant video segments")
    
    # Step 6: Debugging Insights
    print("[6/6] 🐛 Generating debugging insights...")
    debugging_insight = debug_analyzer.generate_debug_insight(
        pattern_name=pattern_name,
        code=req.code,
        error_message=req.message,
        user_message=req.message
    )
    print(f"   ✓ Debugging insight generated")
    
    # Assemble comprehensive response
    print(f"\n{'='*50}")
    print(f"✅ PATTERN INTELLIGENCE RESPONSE READY")
    print(f"{'='*50}\n")
    
    return ChatResponse(
        # Pattern Intelligence
        pattern_name=pattern_name,
        pattern_explanation=pattern_explanation,
        confidence_score=confidence,
        learning_intent=learning_intent,
        
        # Solutions
        explanation=f"**Pattern Detected:** {pattern_name}\n\n{pattern_explanation}",
        corrected_code=corrected_code,
        
        # External Knowledge
        github_repos=external_knowledge["github_repos"],
        stackoverflow_links=external_knowledge["stackoverflow_threads"],
        dev_articles=external_knowledge["dev_articles"],
        
        # Video Segments
        video_segments=video_segments,
        
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

