import sys, os, uuid, re
from enum import Enum
from typing import List, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

# ---------------- LOCAL MODULES ----------------
import video_compile, youtube_download
import auth  # testing hardcoded auth
from config import OPENAI_API_KEY, YOUTUBE_API_KEY
from openai import OpenAI
OPENAI_CLIENT = OpenAI(api_key=OPENAI_API_KEY)

import whisper
from googleapiclient.discovery import build

# ---------------- APP ----------------
app = FastAPI()
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

class ChatResponse(BaseModel):
    explanation: str
    corrected_code: Optional[str]
    links: List[str]
    youtube_videos: List[dict]
    error_analysis: Optional[str]

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
    return auth.register_user(user.username, user.password, user.email)

@app.post("/api/auth/login")
async def login(user: UserLogin):
    return auth.authenticate_user(user.username, user.password)

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
    text = await get_gpt4o_response(req.message)
    videos = await search_youtube(req.message)
    return ChatResponse(
        explanation=text or "Error",
        corrected_code=None,
        links=[],
        youtube_videos=videos,
        error_analysis=None
    )

# ---------------- FRONTEND ----------------
if os.path.exists(DIST_DIR):
    app.mount("/", StaticFiles(directory=DIST_DIR, html=True), name="frontend")
else:
    print("⚠️ dist_build not found")

@app.get("/favicon.ico")
async def favicon():
    return RedirectResponse("https://www.google.com/favicon.ico")

# ---------------- RUN ----------------
if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))

