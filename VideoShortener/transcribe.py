import whisper
import asyncio
from typing import List
from openai import OpenAI
import video_compile
import re


# Use your API key (ensure you use environment variables in production)
client = OpenAI(api_key="sk-proj-JfOgEyCOIHFaeFRFIHXFX7LEG7mbUCnQ0jvH0ikU"
                               "-MWQkOp9GNLBkXbFivsGmcyF1TDiw1x8FpT3BlbkFJ4E5QhN7JLbzFFwcCmY4bsqFHhdb7FHh"
                               "-TbXqKR9ilUVEMzUF9JMji-zgVpruGJ8xYmb5JTqvEA")

# Your async GPT-4o filter function
async def get_gpt4o_mini_response(prompt: str) -> str:
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=3500
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print("An error occurred:", e)
        return None

def parse_segments_from_text(text):
    # Regex to find timestamps like [23.84 - 27.12]
    pattern = r"\[(\d+\.?\d*)\s*-\s*(\d+\.?\d*)\]"
    matches = re.findall(pattern, text)
    # Convert string matches to float tuples
    segments = [(float(start), float(end)) for start, end in matches]
    return segments
    
# Prompt + Transcribe + Filter Relevant Parts
async def extract_relevant_video_content(video_path: str):
    # Step 1: Get goal from user
    goal = input("Enter your query (goal): ").strip()

    # Step 2: Transcribe the video
    print("Transcribing video...")
    model = whisper.load_model("base")
    result = model.transcribe(video_path, verbose=True)

    segments = result.get("segments", [])
    if not segments:
        print("No segments found in video.")
        return

    # Step 3: Prepare raw script for GPT-4o filtering
    script_lines = []
    for seg in segments:
        timestamp = f"[{seg['start']:.2f} - {seg['end']:.2f}]"
        text = seg['text'].strip()
        script_lines.append(f"{timestamp} {text}")
    full_script = "\n".join(script_lines)

    # Step 4: Send to GPT for filtering
    prompt = (
        f"You are an intelligent assistant helping extract useful information from a video transcript.\n\n"
        f"User's goal: \"{goal}\"\n\n"
        f"Below is the transcript of the video with timestamps:\n\n"
        f"{full_script}\n\n"
        f"Please return ONLY the relevant segments (with timestamps) that directly help accomplish the goal. "
        f"Filter out introductions, fluff, or anything irrelevant.\n"
        f"If the video doesn't contain any relevant information, say so clearly."
    )

    print("\nFiltering segments using GPT-4o...")
    filtered_output = await get_gpt4o_mini_response(prompt)

    # Step 5: Display result
    if filtered_output:
        print("\n🧠 Relevant Video Segments:\n")
        print(filtered_output)
        
        segments = parse_segments_from_text(filtered_output)
        
        if segments:
            video_compile.makeVideo(segments)
        else:
            print("No valid timestamps found in filtered output.")
    else:
        print("No relevant information found or an error occurred.")


# Run the script
if __name__ == "__main__":
    video_path = "data/video.mp4"  # Change this if needed
    asyncio.run(extract_relevant_video_content(video_path))
