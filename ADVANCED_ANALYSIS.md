# Advanced Deterministic Code Analysis System

## Overview

This system implements a comprehensive code analysis assistant that follows strict deterministic analysis principles. It provides:

1. **Code Understanding** - Categorizes code by type and identifies specific patterns
2. **Error Detection** - Finds syntax, runtime, logical errors, and anti-patterns
3. **Solution Generation** - Provides corrected code with explanations
4. **Video Learning** - Recommends pattern-based YouTube videos with timestamps
5. **Transcript Extraction** - Extracts key solution segments from video transcripts
6. **Edge Case Handling** - Handles uncertain or mixed patterns appropriately

## API Endpoint

### POST `/api/chat/advanced`

**Request:**
```json
{
  "message": "Error description or question",
  "code": "code snippet here"
}
```

**Response Format (Strict JSON):**
```json
{
  "code_type": "algorithm | design_pattern | system_server | application_logic | edge_case",
  "specific_pattern_or_algorithm": "bubble_sort | singleton | api_error | Uncertain",
  "confidence": "high | medium | low",
  "errors_detected": [
    {
      "type": "syntax | runtime | logical | anti_pattern | edge_case",
      "description": "Error description"
    }
  ],
  "solution": {
    "fixed_code": "corrected code here",
    "explanation": "Why this solution works"
  },
  "videos": [
    {
      "title": "Video Title",
      "video_id": "youtube_video_id",
      "start_time": 120,
      "end_time": 300,
      "key_solution_segments": [
        {
          "start": 120.5,
          "end": 180.2,
          "transcript": "This is where the solution is explained..."
        }
      ]
    }
  ]
}
```

## Code Type Categories

### 1. Algorithm
- **Subtypes**: Searching, Sorting, DP, Greedy, Recursion, Graph, Tree, String
- **Examples**: `bubble_sort`, `quick_sort`, `linear_search`, `binary_search`, `dfs`, `bfs`

### 2. Design Pattern
- **Subtypes**: Factory, Singleton, Observer, Strategy, Adapter, Decorator, Facade
- **Examples**: `singleton`, `factory`, `observer`, `strategy`

### 3. System / Server-side Logic
- **Subtypes**: API, Database, Authentication, Networking, Concurrency
- **Examples**: `api_error`, `database_error`, `auth_error`, `server_down`

### 4. Generic Application Logic
- **Subtypes**: Business Logic, Data Processing, UI Logic, Validation

### 5. Edge Case / Unclassified
- Used when evidence is insufficient or pattern is mixed

## Features

### Deterministic Analysis
- **Evidence-based**: Only identifies patterns when clear structural/behavioral evidence exists
- **No guessing**: Marks as "Uncertain" when evidence is insufficient
- **Confidence levels**: High (clear evidence), Medium (some evidence), Low (weak/uncertain)

### Error Detection
- **Syntax errors**: Language syntax mistakes
- **Runtime errors**: Errors that occur during execution
- **Logical errors**: Incorrect program logic
- **Anti-patterns**: Bad coding practices
- **Edge cases**: Potential failure scenarios

### Video Recommendations
- **Pattern-based**: Videos match the detected pattern/algorithm
- **Not generic**: Avoids basic language tutorials
- **Timestamps**: Provides start_time and end_time for solution segments
- **Key segments**: Highlights exact portions where solution is explained

### Transcript Extraction
- **Smart skipping**: Only processes videos with available transcripts
- **Key segments**: Extracts portions where pattern/solution is discussed
- **Highlighting**: Marks important solution moments in transcripts

## Usage Examples

### Example 1: Algorithm Detection
```python
# Request
{
  "message": "My sorting code is slow",
  "code": "def sort(arr):\n    for i in range(len(arr)):\n        for j in range(i+1, len(arr)):\n            if arr[i] > arr[j]:\n                arr[i], arr[j] = arr[j], arr[i]"
}

# Response will identify:
# - code_type: "algorithm"
# - specific_pattern_or_algorithm: "bubble_sort"
# - Videos about bubble sort with timestamps
```

### Example 2: Design Pattern Detection
```python
# Request
{
  "message": "How to ensure only one instance?",
  "code": "class Database:\n    _instance = None\n    def __new__(cls):\n        if cls._instance is None:\n            cls._instance = super().__new__(cls)\n        return cls._instance"
}

# Response will identify:
# - code_type: "design_pattern"
# - specific_pattern_or_algorithm: "singleton"
# - Videos about singleton pattern
```

### Example 3: Edge Case
```python
# Request
{
  "message": "Code not working",
  "code": "x = 5\ny = 10\nprint(x + y)"
}

# Response will identify:
# - code_type: "edge_case"
# - specific_pattern_or_algorithm: "Uncertain"
# - General programming videos (if any)
```

## Integration

The advanced analysis can be used in two ways:

1. **Direct endpoint**: `POST /api/chat/advanced` - Returns strict JSON format
2. **Via regular chat**: Set `use_advanced_analysis: true` in ChatRequest - Returns ChatResponse format

## Requirements

- OpenAI API key (for GPT-4o analysis)
- YouTube API key (optional, for video search)
- youtube-transcript-api (for transcript extraction)

## Notes

- Videos are only recommended when pattern is clearly identified
- Edge cases return empty video list or general videos
- Transcript extraction requires videos to have available transcripts
- Key solution segments are extracted based on pattern keywords

