import sys
import os
import uuid
import re
import asyncio
from enum import Enum
from typing import List, Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn

# ------------------ BASE DIR ------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

# ------------------ LOCAL MODULES ------------------
import video_compile
import youtube_download
import database
import auth
from config import OPENAI_API_KEY, YOUTUBE_API_KEY

from openai import OpenAI
OPENAI_CLIENT = OpenAI(api_key=OPENAI_API_KEY)

import whisper
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# ------------------ FASTAPI APP ------------------
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------ DIRS ------------------
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
DATA_DIR = os.path.join(BASE_DIR, "data")
DIST_DIR = os.path.join(BASE_DIR, "dist_build")  # frontend build folder
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

# Mount output for videos
app.mount("/output", StaticFiles(directory=OUTPUT_DIR), name="output")

# ------------------ TASK STATUS ------------------
tasks = {}
class TaskStatus(str, Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    TRANSCRIBING = "transcribing"
    FILTERING = "filtering"
    COMPILING = "compiling"
    COMPLETED = "completed"
    FAILED = "failed"

# ------------------ MODELS ------------------
class ProcessRequest(BaseModel):
    video_id: str
    goal: str

class VideoSearch(BaseModel):
    video_id: str
    title: str
    thumbnail: str
    channel: str
    description: str

class UserRegister(BaseModel):
    username: str
    password: str
    email: Optional[str] = None

class UserLogin(BaseModel):
    username: str
    password: str

class ChatRequest(BaseModel):
    message: str
    code: Optional[str] = None

class ChatResponse(BaseModel):
    explanation: str
    corrected_code: Optional[str] = None
    links: List[str] = []
    youtube_videos: List[dict] = []
    error_analysis: Optional[str] = None

# ------------------ HELPERS ------------------
async def get_gpt4o_response(prompt: str) -> str:
    try:
        response = OPENAI_CLIENT.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=3500
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"GPT error: {e}")
        return None

def parse_segments_from_text(text):
    pattern = r"\[(\d+\.?\d*)\s*-\s*(\d+\.?\d*)\]"
    matches = re.findall(pattern, text)
    return [(float(start), float(end)) for start, end in matches]

async def search_youtube_videos(query: str, max_results: int = 3) -> List[dict]:
    if not YOUTUBE_API_KEY:
        return []
    try:
        youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
        request = youtube.search().list(
            q=query,
            part='snippet',
            type='video',
            maxResults=max_results
        )
        response = request.execute()
        results = []
        for item in response['items']:
            results.append({
                "title": item['snippet']['title'],
                "url": f"https://www.youtube.com/watch?v={item['id']['videoId']}",
                "thumbnail": item['snippet']['thumbnails'].get('high', {}).get('url', ''),
                "channel": item['snippet']['channelTitle'],
                "video_id": item['id']['videoId']
            })
        return results
    except Exception as e:
        print(f"YouTube search error: {e}")
        return []

async def get_chat_response(message: str, code: Optional[str] = None) -> dict:
    try:
        prompt_parts = [
            "You are an expert coding assistant that helps developers resolve errors and understand code.",
            "Analyze user's message and code, provide corrected code, links, and YouTube search terms.",
            "User's message:",
            message
        ]
        if code:
            prompt_parts.extend(["Code to analyze:", "```", code, "```"])
        prompt = "\n".join(prompt_parts)

        response = OPENAI_CLIENT.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4000
        )
        response_text = response.choices[0].message.content.strip()

        # Parse code blocks
        code_block_pattern = r"```(?:\w+)?\n?(.*?)```"
        code_matches = re.findall(code_block_pattern, response_text, re.DOTALL)
        corrected_code = code_matches[-1].strip() if code_matches else None
        explanation = re.sub(code_block_pattern, "", response_text, flags=re.DOTALL).strip()

        # Links
        link_pattern = r"\[([^\]]+)\]\(([^\)]+)\)"
        links = [url for _, url in re.findall(link_pattern, response_text) if url.startswith("http")]

        # YouTube search
        youtube_pattern = r"YOUTUBE_SEARCH:\s*([^\n]+)"
        youtube_match = re.search(youtube_pattern, response_text, re.IGNORECASE)
        youtube_videos = []
        if youtube_match:
            search_query = youtube_match.group(1).split(",")[0].strip()
            youtube_videos = await search_youtube_videos(search_query)

        return {
            "explanation": explanation,
            "corrected_code": corrected_code,
            "links": links,
            "youtube_videos": youtube_videos,
            "error_analysis": None
        }
    except Exception as e:
        print(f"Chat response error: {e}")
        return {
            "explanation": f"Error processing request: {str(e)}",
            "corrected_code": None,
            "links": [],
            "youtube_videos": [],
            "error_analysis": None
        }

# ------------------ VIDEO PROCESSING ------------------
async def process_video_task(task_id: str, video_url: str, goal: str):
    try:
        tasks[task_id] = {"status": TaskStatus.DOWNLOADING}
        video_path = os.path.join(DATA_DIR, f"{task_id}.mp4")
        actual_video_path = youtube_download.download_youtube_video(video_url, video_path)

        tasks[task_id] = {"status": TaskStatus.TRANSCRIBING}
        model = whisper.load_model("base")
        result = model.transcribe(actual_video_path, verbose=False)
        segments = result.get("segments", [])
        if not segments:
            tasks[task_id] = {"status": TaskStatus.FAILED, "error": "No segments found"}
            return

        script_lines = [f"[{seg['start']:.2f} - {seg['end']:.2f}] {seg['text'].strip()}" for seg in segments]
        full_script = "\n".join(script_lines)

        tasks[task_id] = {"status": TaskStatus.FILTERING}
        prompt = f"User goal: {goal}\nTranscript:\n{full_script}\nReturn only relevant segments."
        filtered_output = await get_gpt4o_response(prompt)
        if not filtered_output:
            tasks[task_id] = {"status": TaskStatus.FAILED, "error": "Filtering failed"}
            return

        parsed_segments = parse_segments_from_text(filtered_output)
        if not parsed_segments:
            tasks[task_id] = {"status": TaskStatus.FAILED, "error": "No valid segments"}
            return

        tasks[task_id] = {"status": TaskStatus.COMPILING}
        output_path = os.path.join(OUTPUT_DIR, f"{task_id}.mp4")
        video_compile.makeVideo(parsed_segments, actual_video_path, output_path)

        tasks[task_id] = {"status": TaskStatus.COMPLETED, "output_path": output_path}

    except Exception as e:
        tasks[task_id] = {"status": TaskStatus.FAILED, "error": str(e)}
        print(f"Processing error: {e}")

# ------------------ STARTUP ------------------
@app.on_event("startup")
async def startup_event():
    database.init_db()

# ------------------ AUTH ------------------
@app.post("/api/auth/register")
async def register(user_data: UserRegister):
    try:
        return auth.register_user(username=user_data.username, password=user_data.password, email=user_data.email)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/auth/login")
async def login(user_data: UserLogin):
    try:
        return auth.authenticate_user(username=user_data.username, password=user_data.password)
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))

@app.get("/api/auth/me")
async def get_current_user_info(current_user: dict = Depends(auth.get_current_user)):
    return current_user

# ------------------ VIDEO ROUTES ------------------
@app.post("/api/process")
async def process_video(request: ProcessRequest, background_tasks: BackgroundTasks, current_user: dict = Depends(auth.get_current_user)):
    task_id = str(uuid.uuid4())
    tasks[task_id] = {"status": TaskStatus.PENDING}
    video_url = f"https://www.youtube.com/watch?v={request.video_id}"
    background_tasks.add_task(process_video_task, task_id, video_url, request.goal)
    return {"task_id": task_id, "status": "pending"}

@app.get("/api/status/{task_id}")
async def get_status(task_id: str, current_user: dict = Depends(auth.get_current_user)):
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    return tasks[task_id]

@app.get("/api/video/{task_id}")
async def get_video(task_id: str, current_user: dict = Depends(auth.get_current_user)):
    task = tasks.get(task_id)
    if not task or task['status'] != TaskStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Video not ready")
    video_path = task['output_path']
    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="Video file not found")
    return FileResponse(video_path, media_type="video/mp4")

# ------------------ CHAT ROUTE ------------------
@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, current_user: dict = Depends(auth.get_current_user)):
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    result = await get_chat_response(request.message, request.code)
    return ChatResponse(**result)

# ------------------ FRONTEND INTEGRATION ------------------
if os.path.exists(DIST_DIR):
    # Mount entire frontend folder; serves index.html at root and assets correctly
    app.mount("/", StaticFiles(directory=DIST_DIR, html=True), name="frontend")
else:
    print("Warning: Frontend dist_build folder not found!")

# Fallback favicon
@app.get("/favicon.ico")
async def favicon():
    favicon_path = os.path.join(BASE_DIR, "favicon.ico")
    if os.path.exists(favicon_path):
        return FileResponse(favicon_path, media_type="image/x-icon")
    return RedirectResponse("https://raw.githubusercontent.com/favicon.ico")  # fallback

# ------------------ RUN ------------------
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))



