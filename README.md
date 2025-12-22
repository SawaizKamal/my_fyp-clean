# VideoShortener AI - Web Application

A full-stack web application that allows users to search YouTube videos, select content to extract using AI, and get a shortened video with only the relevant parts.

## Features

- 🎯 **AI-Powered Extraction**: Extract only relevant parts of videos using GPT-4o
- 📺 **YouTube Integration**: Search and process any YouTube video
- ⚡ **Fast Processing**: Get results in minutes
- 📱 **Responsive Design**: Beautiful, modern UI that works on all devices
- 🔍 **Smart Search**: Search YouTube videos directly from the app

## Tech Stack

### Frontend
- React 18
- Vite
- TailwindCSS
- React Router DOM
- Axios

### Backend
- FastAPI
- OpenAI Whisper (Transcription)
- GPT-4o (AI Filtering)
- MoviePy (Video Editing)
- yt-dlp (YouTube Download)
- YouTube Data API v3

## Setup Instructions

### Prerequisites

1. Python 3.10+ with venv
2. Node.js 18+
3. YouTube Data API key ([Get it here](https://console.cloud.google.com))
4. OpenAI API key

### Backend Setup

1. Navigate to the backend directory:
```bash
cd VideoShortener/backend
```

2. Activate the virtual environment:
```bash
# Windows
..\venv\Scripts\activate

# Linux/Mac
source ../venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables (optional):
Create a `.env` file in the backend directory:
```
OPENAI_API_KEY=your_openai_key_here
YOUTUBE_API_KEY=your_youtube_api_key_here
```

Or modify the API keys directly in `main.py`.

5. Start the backend server:
```bash
python main.py
```

The backend will run on `http://localhost:8000`

### Frontend Setup

1. Navigate to the frontend directory:
```bash
cd VideoShortener/frontend
```

2. Install dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm run dev
```

The frontend will run on `http://localhost:5173`

## Usage

1. Open your browser and go to `http://localhost:5173`
2. Click "Get Started" on the landing page
3. Search for a YouTube video using keywords
4. Click on a video from the search results
5. Enter what you want to extract (e.g., "Show me the tutorial steps")
6. Click "Process Video" and wait for processing
7. Download or view your shortened video

## API Endpoints

- `GET /api/search?q={query}` - Search YouTube videos
- `POST /api/process` - Start video processing
  - Body: `{ video_id: string, goal: string }`
- `GET /api/status/{task_id}` - Get processing status
- `GET /api/video/{task_id}` - Get processed video file

## File Structure

```
VideoShortener/
├── backend/
│   ├── main.py                 # FastAPI server
│   ├── config.py              # Configuration
│   ├── requirements.txt       # Python dependencies
│   ├── transcribe.py          # Transcription logic (for reference)
│   ├── video_compile.py       # Video compilation
│   ├── youtube_download.py    # YouTube download
│   ├── data/                  # Downloaded videos
│   └── output/                # Processed videos
├── frontend/
│   ├── src/
│   │   ├── pages/             # Page components
│   │   ├── components/        # Reusable components
│   │   ├── api/              # API configuration
│   │   ├── App.jsx           # Main app component
│   │   └── main.jsx          # Entry point
│   ├── package.json
│   └── vite.config.js
└── venv/                      # Python virtual environment
```

## Notes

- Processing times vary based on video length
- Ensure you have sufficient disk space for video downloads
- YouTube API has quota limits - check your usage
- OpenAI API usage will incur costs

## License

MIT License

