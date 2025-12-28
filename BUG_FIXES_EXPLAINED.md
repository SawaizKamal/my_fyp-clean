# Bug Fixes Explained - FYP Video Transcription System

## ISSUE 1: Timestamp Click Bug - Video Restarts Instead of Seeking

### Issue Summary
When clicking on a transcript timestamp, the video restarts from the beginning instead of seeking to the clicked timestamp position.

### Root Cause
The problem is in the `useMemo` hook that computes the video `src` attribute (lines 405-422 in `VideoPlayerPage.jsx`). The `useMemo` calls `localStorage.getItem('token')` inside the function but the token is NOT included in the dependency array `[transcript?.video_url, videoId]`. 

When React re-renders (which happens when `setCurrentTime` is called in `jumpToTimestamp`), if React decides to recalculate the memo (even though dependencies haven't changed), it creates a **new string reference** for the `src` attribute. When the browser's video element sees a different `src` string reference (even with identical content), it treats it as a new source and reloads the video from the beginning.

Additionally, changing the `src` attribute triggers the `onLoadedMetadata` event, which can interfere with seeking operations.

### Correct Fix

**Frontend Fix (`frontend/src/pages/VideoPlayerPage.jsx`):**

1. **Stabilize the video src** by computing it once and storing it in state, or using a ref to prevent React from recreating it
2. **Use `video.currentTime` directly** without triggering re-renders that could recreate the src
3. **Remove token from query string** - use HTTP headers instead (handled by axios interceptor)

**Key changes:**
- Move video URL computation to `useState` so it's computed once when transcript loads
- Ensure the `src` attribute remains stable across renders
- Use `video.currentTime` assignment which is the standard HTML5 video API for seeking

```javascript
// In VideoPlayerPage.jsx, replace the useMemo src with a stable state value:

const [videoSrc, setVideoSrc] = useState('');

// Update videoSrc when transcript loads
useEffect(() => {
  if (!transcript) {
    setVideoSrc('');
    return;
  }
  
  let videoUrl = transcript.video_url || `/api/video/stream/${videoId}`;
  if (!videoUrl.startsWith('http') && !videoUrl.startsWith('/api')) {
    videoUrl = `/api${videoUrl}`;
  }
  
  // Store the base URL (without token - token will be in Authorization header)
  setVideoSrc(videoUrl);
  setVideoInitialized(false);
}, [transcript?.video_url, videoId]);

// In the video element, use the stable src:
<video
  ref={videoRef}
  controls
  className="w-full"
  preload="metadata"
  src={videoSrc}
  onLoadedMetadata={(e) => {
    // Only initialize once when video first loads
    if (videoRef.current && !videoInitialized && !isSeekingRef.current) {
      if (videoRef.current.currentTime === 0 || videoRef.current.readyState < 2) {
        videoRef.current.currentTime = 0;
      }
      setVideoInitialized(true);
      if (!videoRef.current.paused) {
        videoRef.current.pause();
      }
    }
  }}
  // ... rest of handlers
/>
```

**Update `jumpToTimestamp` function:**

```javascript
const jumpToTimestamp = (startTime) => {
  console.log('Jumping to timestamp:', startTime);
  
  if (transcript?.video_unavailable && transcript.youtube_embed_url) {
    // YouTube handling (unchanged)
    // ... existing YouTube code ...
  } else if (videoRef.current) {
    const video = videoRef.current;
    
    // Check if video is ready to seek
    if (video.readyState < 2) {
      // Video metadata not loaded yet, wait for it
      video.addEventListener('loadedmetadata', () => {
        video.currentTime = startTime;
      }, { once: true });
      return;
    }
    
    // Set seeking flag to prevent interference
    isSeekingRef.current = true;
    
    // Direct seek - this is the standard HTML5 API
    video.currentTime = startTime;
    
    // Update state immediately for UI feedback
    setCurrentTime(startTime);
    
    // Clear seeking flag after seek completes
    video.addEventListener('seeked', () => {
      isSeekingRef.current = false;
      setCurrentTime(video.currentTime);
    }, { once: true });
  }
};
```

### Why This Fix Works
- **Stable src**: By using `useState` instead of `useMemo`, the video URL is computed once when the transcript loads and stored in state. React won't recreate this string on every render, so the browser sees a stable `src` attribute.
- **Direct currentTime assignment**: Setting `video.currentTime = startTime` is the standard HTML5 video API for seeking. This directly changes the playback position without reloading the video.
- **No token in URL**: Removing the token from the query string prevents URL changes. The axios interceptor already adds the token to the `Authorization` header for all API requests, including video streaming (the browser handles this automatically for `<video>` elements when using the same origin or proper CORS).

---

## ISSUE 2: 401 Unauthorized Error After Clicking Timestamp

### Issue Summary
After clicking a transcript timestamp, the system starts giving 401 Unauthorized errors on subsequent API calls or video requests.

### Root Cause
The video element's `src` includes the token as a query parameter (`?token=...`). When the user clicks a timestamp:

1. The `jumpToTimestamp` function doesn't change the video src, so this shouldn't directly cause 401s
2. However, if the video src is being recreated (Issue #1), the browser makes a new HTTP request for the video
3. The backend `/api/video/upload/{video_id}` and `/api/video/stream/{video_id}` endpoints require authentication
4. Video elements in browsers **cannot send custom headers** like `Authorization: Bearer <token>`
5. The backend tries to read the token from the query parameter, but if the token is missing, expired, or the query parameter isn't properly passed, it returns 401

Additionally, if clicking a timestamp somehow triggers a re-fetch of the transcript or other API calls, and the token has expired or been removed from localStorage, those calls will fail with 401.

### Correct Fix

**Backend Fix - Ensure video streaming endpoints properly handle token from query params:**

The backend already tries to read the token from query params (line 693 in `main.py`), but we should ensure it's robust.

**Frontend Fix - Remove token from video URL, use HTTP headers instead:**

The real fix is to **NOT include the token in the video URL**. Instead:

1. The video should be served from the same origin (or with proper CORS)
2. For same-origin requests, cookies/credentials can be used
3. For cross-origin, we need a different approach

However, since `<video>` elements cannot send Authorization headers, we have two options:

**Option A: Use a proxy endpoint that adds authentication**
**Option B: Use signed URLs or session-based auth for video streaming**

The current code already uses query parameters, so the issue is likely:
1. Token is missing from the URL when src is recreated
2. Token has expired
3. The video src is being recreated without the token

**The fix for Issue #1 (stabilizing the src) will also fix Issue #2**, because:
- The video src won't be recreated on timestamp clicks
- The token remains in the URL (if we keep using query params)
- No new HTTP requests are made, so no 401 errors

**However, a better long-term solution:**

Remove token from video URL and use a session-based approach or signed URLs:

```javascript
// In VideoPlayerPage.jsx, update videoSrc to NOT include token:
useEffect(() => {
  if (!transcript) {
    setVideoSrc('');
    return;
  }
  
  let videoUrl = transcript.video_url || `/api/video/stream/${videoId}`;
  if (!videoUrl.startsWith('http') && !videoUrl.startsWith('/api')) {
    videoUrl = `/api${videoUrl}`;
  }
  
  // DO NOT add token to URL - video elements can't send headers
  // Instead, backend should check session/cookies or use signed URLs
  setVideoSrc(videoUrl);
}, [transcript?.video_url, videoId]);
```

**Backend should handle authentication via:**
1. Session cookies (if same origin)
2. Signed URLs with expiration
3. Or continue using query params but ensure they're always included

### Why This Fix Works
- **No URL recreation**: By stabilizing the video src (from Issue #1 fix), the video URL (including token if using query params) remains constant
- **No new requests**: Since the src doesn't change, the browser doesn't make new HTTP requests for the video, so no 401 errors occur
- **Proper authentication flow**: Token remains in localStorage for API calls (handled by axios interceptor), and video streaming uses a stable URL with token in query params (or session-based auth)

---

## ISSUE 3: Wrong Solution Highlighting After Transcription

### Issue Summary
The system highlights incorrect transcript segments as "solutions" after transcription completes. Segments that don't contain solutions are marked, while actual solution segments are missed.

### Root Cause
In `backend/main.py`, the `transcribe_uploaded_video_task` function (lines 315-401) sends the **ENTIRE transcript** to GPT-4 for solution identification. The prompt includes:

```python
full_transcript = "\n".join(full_transcript_lines)  # ALL segments
solution_prompt = f"""...
TRANSCRIPT (each line format: [MM:SS] text):
{full_transcript}  # <-- FULL transcript sent to GPT
...
Identify segments (by their 0-based index) that DIRECTLY address the user's question
"""
```

**The Problem:**
1. GPT receives the **entire video transcript** (could be 1000+ segments)
2. GPT is asked to identify solution segments by **0-based index**
3. With a large transcript, GPT can:
   - Make indexing errors (off-by-one, wrong indices)
   - Get confused by the volume of content
   - Return indices that don't correspond to actual solutions
   - Miss context about which segments are truly relevant

**Why timestamp-based chunking is needed:**
- GPT works better with focused, contextual chunks
- Timestamp information helps GPT understand temporal relationships
- Smaller chunks reduce indexing errors
- More accurate solution identification when GPT sees relevant context

### Correct Fix

**Backend Fix (`backend/main.py`):**

Instead of sending the full transcript, send **timestamp-based chunks** with clear context:

```python
# In transcribe_uploaded_video_task function, replace the solution identification logic:

# Use GPT-4 to identify solution segments if user_query is provided
solution_segments = []
if user_query:
    logger.info(f"Identifying solution segments using GPT-4 for query: {user_query[:100]}")
    
    # CHUNK THE TRANSCRIPT BY TIMESTAMPS (e.g., 2-minute windows)
    chunk_size_seconds = 120  # 2 minutes per chunk
    chunks = []
    
    current_chunk_start = 0
    current_chunk_segments = []
    current_chunk_indices = []
    
    for idx, seg in enumerate(transcript_segments):
        seg_start = seg['start']
        
        # If this segment starts a new chunk window, save previous chunk
        if seg_start >= current_chunk_start + chunk_size_seconds and current_chunk_segments:
            chunks.append({
                'start_time': current_chunk_start,
                'end_time': seg_start,
                'segments': current_chunk_segments,
                'indices': current_chunk_indices
            })
            current_chunk_start = int(seg_start / chunk_size_seconds) * chunk_size_seconds
            current_chunk_segments = []
            current_chunk_indices = []
        
        current_chunk_segments.append(seg)
        current_chunk_indices.append(idx)
    
    # Add final chunk
    if current_chunk_segments:
        chunks.append({
            'start_time': current_chunk_start,
            'end_time': transcript_segments[-1]['end'] if transcript_segments else current_chunk_start + chunk_size_seconds,
            'segments': current_chunk_segments,
            'indices': current_chunk_indices
        })
    
    # Analyze each chunk separately
    for chunk in chunks:
        # Build chunk transcript with clear index labels
        chunk_transcript_lines = []
        for i, seg in enumerate(chunk['segments']):
            original_index = chunk['indices'][i]
            timestamp_str = seg['timestamp']
            chunk_transcript_lines.append(f"[Segment {original_index}] [{timestamp_str}] {seg['text']}")
        
        chunk_transcript = "\n".join(chunk_transcript_lines)
        
        solution_prompt = f"""You are an expert at identifying solution segments in educational video transcripts.

USER'S QUESTION/QUERY: "{user_query}"

TRANSCRIPT CHUNK (Time range: {chunk['start_time']:.1f}s - {chunk['end_time']:.1f}s):
Each line format: [Segment INDEX] [MM:SS] text

{chunk_transcript}

INSTRUCTIONS:
1. Analyze ONLY the segments in this chunk
2. Identify segments (by their Segment INDEX number) that DIRECTLY address the user's question
3. Focus on segments that explain HOW to solve the problem, show implementations, or provide actionable solutions
4. EXCLUDE introductions, filler, off-topic content, or vague mentions

OUTPUT FORMAT:
Return ONLY a JSON array of segment indices from this chunk that contain solutions, or an empty array [].
Example: [5, 8, 12] or []

CRITICAL: Return ONLY the JSON array, no explanations."""
        
        try:
            chunk_response = await get_gpt4o_response(solution_prompt, temperature=0.2)
            
            if chunk_response:
                # Parse JSON array from response
                import json
                import re
                
                # Try to extract JSON array
                json_match = re.search(r'\[[\d,\s]*\]', chunk_response)
                if json_match:
                    try:
                        chunk_solutions = json.loads(json_match.group())
                        if isinstance(chunk_solutions, list):
                            # Add to overall solution segments (they're already the correct indices)
                            solution_segments.extend([int(i) for i in chunk_solutions if isinstance(i, (int, str)) and str(i).isdigit()])
                    except json.JSONDecodeError:
                        pass
        except Exception as e:
            logger.error(f"Failed to analyze chunk: {e}", exc_info=True)
            continue
    
    # Remove duplicates and sort
    solution_segments = sorted(list(set([i for i in solution_segments if 0 <= i < len(transcript_segments)])))
    
    logger.info(f"Identified {len(solution_segments)} solution segments using chunked analysis: {solution_segments[:10]}{'...' if len(solution_segments) > 10 else ''}")
```

**Alternative Simpler Fix (if chunking is complex):**

Send the full transcript but with **better indexing and context**:

```python
# Build transcript with clear, prominent index labels
indexed_transcript_lines = []
for idx, seg in enumerate(transcript_segments):
    timestamp_str = seg['timestamp']
    # Make index VERY clear and prominent
    indexed_transcript_lines.append(f"SEGMENT_INDEX_{idx} | [{timestamp_str}] {seg['text']}")

indexed_transcript = "\n".join(indexed_transcript_lines)

solution_prompt = f"""You are an expert at identifying solution segments in educational video transcripts.

USER'S QUESTION/QUERY: "{user_query}"

TRANSCRIPT (each line format: SEGMENT_INDEX_X | [MM:SS] text):
{indexed_transcript}

INSTRUCTIONS:
1. Read through ALL segments carefully
2. Identify segments by their SEGMENT_INDEX number (the number after SEGMENT_INDEX_) that DIRECTLY address the user's question
3. Focus on segments that explain HOW to solve the problem, show code/implementations, or provide step-by-step solutions

OUTPUT FORMAT:
Return ONLY a JSON array of SEGMENT_INDEX numbers, nothing else.
Example: [2, 5, 12] or []

CRITICAL: Use the SEGMENT_INDEX numbers exactly as shown in the transcript above."""
```

### Why This Fix Works
- **Chunked analysis**: By breaking the transcript into smaller, timestamp-based chunks (e.g., 2-minute windows), GPT can:
  - Focus on relevant content without being overwhelmed
  - Make more accurate indexing decisions
  - Better understand temporal context (what happens before/after)
  - Return more precise segment indices
  
- **Clear indexing**: By prominently labeling each segment with its index (e.g., `SEGMENT_INDEX_5`), GPT is less likely to make indexing errors

- **Focused context**: Smaller chunks mean GPT sees only relevant portions, reducing the chance of selecting irrelevant segments

- **Better accuracy**: When GPT analyzes 2-minute chunks instead of a 30-minute full transcript, it can more accurately identify which segments truly contain solutions

---

## Summary

1. **Issue 1**: Stabilize video `src` using `useState` instead of `useMemo` to prevent video reload on timestamp clicks
2. **Issue 2**: Fixing Issue 1 also fixes Issue 2 (no new HTTP requests = no 401 errors)
3. **Issue 3**: Use timestamp-based chunking when sending transcripts to GPT for solution identification, with clear index labels

All fixes focus on **stability** (Issue 1 & 2) and **precision** (Issue 3) to ensure the system works correctly.



