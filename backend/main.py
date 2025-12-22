from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
import os
import uuid
import asyncio
from enum import Enum

# Import existing modules
import whisper
from openai import OpenAI
import re
import video_compile
import youtube_download
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Import authentication modules
import database
import auth

# FastAPI app
app = FastAPI()

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    database.init_db()

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files for serving videos
os.makedirs("output", exist_ok=True)
app.mount("/output", StaticFiles(directory="output"), name="output")

# Configuration - Import from config module
from config import OPENAI_API_KEY, YOUTUBE_API_KEY

OPENAI_CLIENT = OpenAI(api_key=OPENAI_API_KEY)

# Task status tracking
tasks = {}

class TaskStatus(str, Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    TRANSCRIBING = "transcribing"
    FILTERING = "filtering"
    COMPILING = "compiling"
    COMPLETED = "completed"
    FAILED = "failed"

# Pydantic models
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
    message: str  # User's code/error/question
    code: Optional[str] = None  # Optional code snippet

class ChatResponse(BaseModel):
    explanation: str
    corrected_code: Optional[str] = None
    links: List[str] = []
    youtube_videos: List[dict] = []
    error_analysis: Optional[str] = None

# Helper functions
async def get_gpt4o_response(prompt: str) -> str:
    """Call OpenAI GPT-4o for filtering."""
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
    """Parse timestamps from GPT output."""
    pattern = r"\[(\d+\.?\d*)\s*-\s*(\d+\.?\d*)\]"
    matches = re.findall(pattern, text)
    return [(float(start), float(end)) for start, end in matches]

async def search_youtube_videos(query: str, max_results: int = 3) -> List[dict]:
    """Search YouTube videos and return formatted results."""
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
    """Get chat response from OpenAI with code analysis, links, and YouTube videos."""
    try:
        # Build the prompt
        prompt_parts = [
            "You are an expert coding assistant that helps developers resolve errors and understand code.",
            "Your task is to:",
            "1. Analyze any provided code for errors",
            "2. Explain what's wrong (if errors exist)",
            "3. Provide corrected code in markdown code blocks (```language ... ```)",
            "4. Suggest relevant documentation links in markdown format: [Title](URL)",
            "5. At the end, provide YouTube search terms for tutorials (format: YOUTUBE_SEARCH: term1, term2, term3)",
            "",
            "User's question/message:",
            message
        ]
        
        if code:
            prompt_parts.extend([
                "",
                "Code to analyze:",
                "```",
                code,
                "```"
            ])
        
        prompt = "\n".join(prompt_parts)
        
        # Call OpenAI
        response = OPENAI_CLIENT.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4000
        )
        
        response_text = response.choices[0].message.content.strip()
        
        # Parse response
        explanation = response_text
        corrected_code = None
        links = []
        youtube_search_terms = []
        
        # Extract code blocks
        code_block_pattern = r"```(?:\w+)?\n?(.*?)```"
        code_matches = re.findall(code_block_pattern, response_text, re.DOTALL)
        if code_matches:
            corrected_code = code_matches[-1].strip()  # Get the last code block (usually the corrected one)
            # Remove code blocks from explanation
            explanation = re.sub(code_block_pattern, "", explanation, flags=re.DOTALL).strip()
        
        # Extract markdown links
        link_pattern = r"\[([^\]]+)\]\(([^\)]+)\)"
        link_matches = re.findall(link_pattern, response_text)
        for title, url in link_matches:
            if url.startswith("http"):
                links.append(url)
        
        # Extract YouTube search terms
        youtube_pattern = r"YOUTUBE_SEARCH:\s*([^\n]+)"
        youtube_match = re.search(youtube_pattern, response_text, re.IGNORECASE)
        if youtube_match:
            terms = youtube_match.group(1).strip()
            youtube_search_terms = [term.strip() for term in terms.split(",") if term.strip()]
        
        # Search YouTube videos
        youtube_videos = []
        if youtube_search_terms:
            # Use the first search term or combine them
            search_query = youtube_search_terms[0] if youtube_search_terms else message
            youtube_videos = await search_youtube_videos(search_query, max_results=3)
        
        # Extract error analysis (if code was provided)
        error_analysis = None
        if code:
            # Look for error explanation patterns
            error_patterns = [
                r"(?:error|issue|problem|bug).*?:(.*?)(?:\n\n|\n[A-Z])",
                r"(?:The issue|The problem|The error).*?\.(.*?)(?:\n\n|\n[A-Z])"
            ]
            for pattern in error_patterns:
                match = re.search(pattern, response_text, re.IGNORECASE | re.DOTALL)
                if match:
                    error_analysis = match.group(1).strip()
                    break
        
        return {
            "explanation": explanation,
            "corrected_code": corrected_code,
            "links": links,
            "youtube_videos": youtube_videos,
            "error_analysis": error_analysis
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

async def process_video_task(task_id: str, video_url: str, goal: str):
    """Background task for processing video."""
    try:
        # Download
        tasks[task_id] = {"status": TaskStatus.DOWNLOADING}
        video_path = f"data/{task_id}.mp4"
        actual_video_path = youtube_download.download_youtube_video(video_url, video_path)

        # Transcribe
        tasks[task_id] = {"status": TaskStatus.TRANSCRIBING}
        model = whisper.load_model("base")
        result = model.transcribe(actual_video_path, verbose=False)
        segments = result.get("segments", [])
        
        if not segments:
            tasks[task_id] = {"status": TaskStatus.FAILED, "error": "No segments found"}
            return

        # Prepare script
        script_lines = []
        for seg in segments:
            timestamp = f"[{seg['start']:.2f} - {seg['end']:.2f}]"
            text = seg['text'].strip()
            script_lines.append(f"{timestamp} {text}")
        full_script = "\n".join(script_lines)

        # Filter
        tasks[task_id] = {"status": TaskStatus.FILTERING}
        prompt = (
            f"You are an intelligent assistant helping extract useful information from a video transcript.\n\n"
            f"User's goal: \"{goal}\"\n\n"
            f"Below is the transcript of the video with timestamps:\n\n"
            f"{full_script}\n\n"
            f"Please return ONLY the relevant segments (with timestamps) that directly help accomplish the goal. "
            f"Filter out introductions, fluff, or anything irrelevant.\n"
            f"If the video doesn't contain any relevant information, say so clearly."
        )
        filtered_output = await get_gpt4o_response(prompt)
        
        if not filtered_output:
            tasks[task_id] = {"status": TaskStatus.FAILED, "error": "Filtering failed"}
            return

        # Parse segments
        parsed_segments = parse_segments_from_text(filtered_output)
        if not parsed_segments:
            tasks[task_id] = {"status": TaskStatus.FAILED, "error": "No valid segments"}
            return

        # Compile video
        tasks[task_id] = {"status": TaskStatus.COMPILING}
        output_path = f"output/{task_id}.mp4"
        video_compile.makeVideo(parsed_segments, actual_video_path, output_path)

        tasks[task_id] = {
            "status": TaskStatus.COMPLETED,
            "output_path": output_path
        }

    except Exception as e:
        tasks[task_id] = {"status": TaskStatus.FAILED, "error": str(e)}
        print(f"Processing error: {e}")

# Authentication Endpoints
@app.post("/api/auth/register")
async def register(user_data: UserRegister):
    """Register a new user."""
    try:
        # Debug logging
        print(f"Register attempt - Username: {user_data.username}, Password type: {type(user_data.password)}, Password length: {len(user_data.password) if isinstance(user_data.password, str) else 'N/A'}")
        result = auth.register_user(
            username=user_data.username,
            password=user_data.password,
            email=user_data.email
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"Unexpected error during registration: {e}")
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")

@app.post("/api/auth/login")
async def login(user_data: UserLogin):
    """Login and get JWT token."""
    try:
        result = auth.authenticate_user(
            username=user_data.username,
            password=user_data.password
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

@app.get("/api/auth/me")
async def get_current_user_info(current_user: dict = Depends(auth.get_current_user)):
    """Get current authenticated user information."""
    return {
        "id": current_user["id"],
        "username": current_user["username"],
        "email": current_user["email"]
    }

# API Endpoints (Protected)
@app.get("/api/search")
async def search_videos(q: str, max_results: int = 10, current_user: dict = Depends(auth.get_current_user)):
    """Search YouTube videos."""
    if not YOUTUBE_API_KEY:
        raise HTTPException(status_code=500, detail="YouTube API key not configured")
    
    try:
        youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
        request = youtube.search().list(
            q=q,
            part='snippet',
            type='video',
            maxResults=max_results
        )
        response = request.execute()
        
        results = []
        for item in response['items']:
            results.append({
                "video_id": item['id']['videoId'],
                "title": item['snippet']['title'],
                "thumbnail": item['snippet']['thumbnails']['high']['url'],
                "channel": item['snippet']['channelTitle'],
                "description": item['snippet']['description']
            })
        
        return {"results": results}
    except HttpError as e:
        raise HTTPException(status_code=500, detail=f"YouTube API error: {str(e)}")

@app.post("/api/process")
async def process_video(request: ProcessRequest, background_tasks: BackgroundTasks, current_user: dict = Depends(auth.get_current_user)):
    """Start video processing."""
    task_id = str(uuid.uuid4())
    tasks[task_id] = {"status": TaskStatus.PENDING}
    
    # Get video URL from YouTube ID
    video_url = f"https://www.youtube.com/watch?v={request.video_id}"
    
    # Start background task
    background_tasks.add_task(process_video_task, task_id, video_url, request.goal)
    
    return {"task_id": task_id, "status": "pending"}

@app.get("/api/status/{task_id}")
async def get_status(task_id: str, current_user: dict = Depends(auth.get_current_user)):
    """Get processing status."""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return tasks[task_id]

@app.get("/api/video/{task_id}")
async def get_video(task_id: str, current_user: dict = Depends(auth.get_current_user)):
    """Get processed video."""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = tasks[task_id]
    if task['status'] != TaskStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Video not ready")
    
    video_path = f"output/{task_id}.mp4"
    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="Video file not found")
    
    return FileResponse(video_path, media_type="video/mp4")

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, current_user: dict = Depends(auth.get_current_user)):
    """Chat endpoint for code analysis and error resolution."""
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    try:
        result = await get_chat_response(request.message, request.code)
        return ChatResponse(**result)
    except Exception as e:
        print(f"Chat endpoint error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process chat request: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
