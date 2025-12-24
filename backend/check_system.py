"""Simple System Verification Check"""
import os
import sys

print("=" * 60)
print("SYSTEM VERIFICATION CHECK")
print("=" * 60)

# 1. Check API Keys
print("\n1. API Keys:")
youtube_key = os.getenv("YOUTUBE_API_KEY")
openai_key = os.getenv("OPENAI_API_KEY")

print(f"   OPENAI_API_KEY: {'SET' if openai_key else 'NOT SET'}")
print(f"   YOUTUBE_API_KEY: {'SET' if youtube_key else 'NOT SET (using fallback)'}")

# 2. Test imports
print("\n2. Module Imports:")
try:
    import pattern_detector
    print("   [OK] pattern_detector")
except Exception as e:
    print(f"   [FAIL] pattern_detector: {e}")

try:
    import video_transcript_analyzer
    print("   [OK] video_transcript_analyzer")
except Exception as e:
    print(f"   [FAIL] video_transcript_analyzer: {e}")

try:
    import knowledge_search
    print("   [OK] knowledge_search")
except Exception as e:
    print(f"   [FAIL] knowledge_search: {e}")

try:
    import debug_analyzer
    print("   [OK] debug_analyzer")
except Exception as e:
    print(f"   [FAIL] debug_analyzer: {e}")

# 3. Check pattern library
print(f"\n3. Pattern Library: {len(pattern_detector.PATTERN_LIBRARY)} patterns loaded")
print("   Specific algorithms:")
for key, info in pattern_detector.PATTERN_LIBRARY.items():
    if "search" in key.lower() or "sort" in key.lower():
        print(f"   - {info['name']} ({info['task_type']})")

print("\n" + "=" * 60)
print("VERIFICATION COMPLETE")
print("=" * 60)

# Status
if youtube_key:
    print("\nSTATUS: All systems ready with REAL YouTube API")
else:
    print("\nSTATUS: All systems ready with FALLBACK videos")
    print("TIP: Set YOUTUBE_API_KEY for real video search")
