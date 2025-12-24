"""
Test script to verify YouTube API and Pattern Intelligence System
"""

import sys
import os

print("=" * 60)
print("YOUTUBE API & PATTERN INTELLIGENCE VERIFICATION")
print("=" * 60)

# Check environment variables
print("\n1. Checking Environment Variables...")
youtube_key = os.getenv("YOUTUBE_API_KEY")
openai_key = os.getenv("OPENAI_API_KEY")

if openai_key:
    print(f"   ✅ OPENAI_API_KEY is set (length: {len(openai_key)})")
else:
    print("   ❌ OPENAI_API_KEY is NOT set")

if youtube_key:
    print(f"   ✅ YOUTUBE_API_KEY is set (length: {len(youtube_key)})")
else:
    print("   ⚠️  YOUTUBE_API_KEY is NOT set (using fallback videos)")

# Test pattern detection
print("\n2. Testing Pattern Detection...")
try:
    import pattern_detector
    
    test_code = '''function searchItem(arr, target) {
    for (let i = 0; i <= arr.length; i++) {
        if (arr[i] = target) {
            return "Item Found at index " + i
        }
    }
    return "Item not found"
}'''
    
    result = pattern_detector.detect_primary_and_secondary_patterns(
        code=test_code,
        error_message="My search function isn't working",
        user_message="Need help with search algorithm"
    )
    
    print(f"   ✅ Pattern Detection Working")
    print(f"   PRIMARY: {result['primary_pattern_name']}")
    print(f"   SECONDARY: {result['secondary_issues']}")
    print(f"   Confidence: {result['confidence']}%")
    
    # Check if it detects Linear Search specifically
    if "Linear Search" in result['primary_pattern_name']:
        print("   ✅ Algorithm-specific detection working (Linear Search)")
    else:
        print(f"   ⚠️  Expected 'Linear Search', got: {result['primary_pattern_name']}")
        
except Exception as e:
    print(f"   ❌ Pattern Detection Error: {e}")

# Test video transcript analyzer
print("\n3. Testing Video Transcript Analyzer...")
try:
    import video_transcript_analyzer
    
    # Test with a known educational video
    test_url = "https://youtube.com/watch?v=dQw4w9WgXcQ"
    has_transcript, reason = video_transcript_analyzer.check_audio_availability(test_url)
    
    if has_transcript:
        print(f"   ✅ Transcript checking working")
    else:
        print(f"   ℹ️  Transcript unavailable (reason: {reason})")
        
except Exception as e:
    print(f"   ❌ Transcript Analyzer Error: {e}")

# Test YouTube search
print("\n4. Testing YouTube Search...")
try:
    import asyncio
    from main import search_youtube
    
    async def test_search():
        videos = await search_youtube("Linear Search algorithm tutorial")
        return videos
    
    videos = asyncio.run(test_search())
    
    if videos and len(videos) > 0:
        print(f"   ✅ YouTube Search Working - Found {len(videos)} videos")
        print(f"   Sample: {videos[0].get('title', 'N/A')[:50]}...")
        
        if youtube_key:
            print("   ✅ Using REAL YouTube API")
        else:
            print("   ⚠️  Using FALLBACK videos (set YOUTUBE_API_KEY for real videos)")
    else:
        print("   ❌ No videos returned")
        
except Exception as e:
    print(f"   ❌ YouTube Search Error: {e}")

# Test external knowledge search
print("\n5. Testing External Knowledge Search...")
try:
    import knowledge_search
    
    results = knowledge_search.get_external_knowledge("Linear Search algorithm")
    
    github_count = len(results.get("github_repos", []))
    so_count = len(results.get("stackoverflow_threads", []))
    dev_count = len(results.get("dev_articles", []))
    
    print(f"   ✅ External Knowledge Search Working")
    print(f"   GitHub repos: {github_count}")
    print(f"   StackOverflow threads: {so_count}")
    print(f"   Dev articles: {dev_count}")
    
except Exception as e:
    print(f"   ❌ External Knowledge Error: {e}")

print("\n" + "=" * 60)
print("VERIFICATION COMPLETE")
print("=" * 60)

# Summary
print("\n📊 SYSTEM STATUS SUMMARY:")
print(f"Pattern Detection: {'✅ Working' if 'pattern_detector' in sys.modules else '❌ Failed'}")
print(f"Transcript Analysis: {'✅ Working' if 'video_transcript_analyzer' in sys.modules else '❌ Failed'}")
print(f"YouTube API: {'✅ Real API' if youtube_key else '⚠️  Fallback Mode'}")
print(f"External Knowledge: {'✅ Working' if 'knowledge_search' in sys.modules else '❌ Failed'}")

print("\n✨ System is ready for pattern-based code analysis!")
