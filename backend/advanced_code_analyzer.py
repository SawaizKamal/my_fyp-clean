"""
Advanced Deterministic Code Analysis and Learning Assistant

Implements comprehensive code analysis with:
- Code type/category detection
- Error detection (syntax, runtime, logical, anti-patterns)
- Solution generation
- Pattern-based video recommendations
- Transcript extraction with key solution segments
- Edge case handling
"""

from typing import Dict, List, Optional, Tuple
from openai import OpenAI
from config import OPENAI_API_KEY
import re

OPENAI_CLIENT = OpenAI(api_key=OPENAI_API_KEY)

# Code Type Categories
CODE_TYPES = {
    "algorithm": {
        "name": "Algorithm",
        "subtypes": ["searching", "sorting", "dp", "greedy", "recursion", "graph", "tree", "string"]
    },
    "design_pattern": {
        "name": "Design Pattern",
        "subtypes": ["factory", "singleton", "observer", "strategy", "adapter", "decorator", "facade"]
    },
    "system_server": {
        "name": "System / Server-side Logic",
        "subtypes": ["api", "database", "authentication", "networking", "concurrency"]
    },
    "application_logic": {
        "name": "Generic Application Logic",
        "subtypes": ["business_logic", "data_processing", "ui_logic", "validation"]
    },
    "edge_case": {
        "name": "Edge Case / Unclassified",
        "subtypes": ["mixed_pattern", "insufficient_evidence", "unclear_intent"]
    }
}

# Specific Algorithm/Pattern Names
SPECIFIC_PATTERNS = {
    # Algorithms
    "bubble_sort": {"type": "algorithm", "category": "sorting"},
    "quick_sort": {"type": "algorithm", "category": "sorting"},
    "merge_sort": {"type": "algorithm", "category": "sorting"},
    "insertion_sort": {"type": "algorithm", "category": "sorting"},
    "linear_search": {"type": "algorithm", "category": "searching"},
    "binary_search": {"type": "algorithm", "category": "searching"},
    "dfs": {"type": "algorithm", "category": "graph"},
    "bfs": {"type": "algorithm", "category": "graph"},
    "dijkstra": {"type": "algorithm", "category": "graph"},
    
    # Design Patterns
    "singleton": {"type": "design_pattern", "category": "creational"},
    "factory": {"type": "design_pattern", "category": "creational"},
    "observer": {"type": "design_pattern", "category": "behavioral"},
    "strategy": {"type": "design_pattern", "category": "behavioral"},
    "adapter": {"type": "design_pattern", "category": "structural"},
    
    # System/Server
    "api_error": {"type": "system_server", "category": "api"},
    "database_error": {"type": "system_server", "category": "database"},
    "auth_error": {"type": "system_server", "category": "authentication"},
    "server_down": {"type": "system_server", "category": "networking"},
}


def analyze_code(code: str, error_message: str = "", user_message: str = "") -> Dict:
    """
    Main analysis function - performs comprehensive code analysis.
    
    Args:
        code: Code snippet to analyze
        error_message: Error message if any
        user_message: User's description of the problem
    
    Returns:
        Dict following the strict JSON format specified
    """
    # Step 1: Code Understanding
    code_analysis = understand_code_type(code, error_message, user_message)
    
    # Step 2: Error Detection
    errors = detect_errors(code, error_message)
    
    # Step 3: Solution Generation
    solution = generate_solution(code_analysis, code, error_message)
    
    # Step 4: Video Recommendations (pattern-based)
    videos = get_video_recommendations(code_analysis)
    
    return {
        "code_type": code_analysis["code_type"],
        "specific_pattern_or_algorithm": code_analysis["specific_pattern"],
        "confidence": code_analysis["confidence"],
        "errors_detected": errors,
        "solution": solution,
        "videos": videos
    }


def understand_code_type(code: str, error_message: str, user_message: str) -> Dict:
    """
    Analyze code to determine type, category, and specific pattern.
    
    Returns:
        Dict with code_type, specific_pattern, confidence
    """
    context = f"""
User Description: {user_message}
Error Message: {error_message}
Code:
{code}
"""
    
    prompt = f"""You are an advanced deterministic code analysis system.

Analyze the given code and determine:

1. Code Type / Category (ONE primary):
   - Algorithm (e.g. Searching, Sorting, DP, Greedy, Recursion, Graph, Tree, String)
   - Design Pattern (e.g. Factory, Singleton, Observer, Strategy, Adapter)
   - System / Server-side Logic (e.g. API, Database, Authentication, Networking)
   - Generic Application Logic
   - Edge Case / Unclassified

2. If applicable, identify the SPECIFIC pattern or algorithm name.
   Base this on structural and behavioral evidence.
   DO NOT guess or assume popularity.
   If evidence is insufficient, mark as "Uncertain".

**Code to Analyze:**
{context}

**Instructions:**
1. Analyze the code structure and behavior
2. Identify the PRIMARY code type
3. Identify the SPECIFIC pattern/algorithm if clear evidence exists
4. Provide confidence level: "high" (clear evidence), "medium" (some evidence), "low" (weak/uncertain)

**Output Format:**
CODE_TYPE: [algorithm|design_pattern|system_server|application_logic|edge_case]
SPECIFIC_PATTERN: [specific name or "Uncertain"]
CONFIDENCE: [high|medium|low]

**Your Analysis:**"""

    try:
        response = OPENAI_CLIENT.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.2  # Low temperature for deterministic analysis
        )
        
        result = response.choices[0].message.content.strip()
        
        # Parse response
        code_type = "edge_case"
        specific_pattern = "Uncertain"
        confidence = "low"
        
        for line in result.split('\n'):
            if line.startswith('CODE_TYPE:'):
                code_type = line.split(':', 1)[1].strip().lower()
            elif line.startswith('SPECIFIC_PATTERN:'):
                specific_pattern = line.split(':', 1)[1].strip()
            elif line.startswith('CONFIDENCE:'):
                confidence = line.split(':', 1)[1].strip().lower()
        
        # Validate code_type
        valid_types = ["algorithm", "design_pattern", "system_server", "application_logic", "edge_case"]
        if code_type not in valid_types:
            code_type = "edge_case"
        
        # Validate confidence
        if confidence not in ["high", "medium", "low"]:
            confidence = "low"
        
        return {
            "code_type": code_type,
            "specific_pattern": specific_pattern,
            "confidence": confidence
        }
        
    except Exception as e:
        print(f"Code type analysis error: {e}")
        return {
            "code_type": "edge_case",
            "specific_pattern": "Uncertain",
            "confidence": "low"
        }


def detect_errors(code: str, error_message: str) -> List[Dict]:
    """
    Detect syntax, runtime, logical errors, and anti-patterns.
    
    Returns:
        List of error dicts with type and description
    """
    errors = []
    
    # Use GPT to analyze errors
    prompt = f"""Analyze this code for errors:

**Code:**
```python
{code}
```

**Error Message (if any):**
{error_message}

**Task:**
Detect and report:
- Syntax errors
- Runtime errors
- Logical errors
- Anti-patterns / bad practices
- Edge cases that can break this code

**Output Format:**
For each error found, output:
ERROR_TYPE: [syntax|runtime|logical|anti_pattern|edge_case]
DESCRIPTION: [brief description]

If no errors found, output: NO_ERRORS

**Your Analysis:**"""

    try:
        response = OPENAI_CLIENT.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.3
        )
        
        result = response.choices[0].message.content.strip()
        
        if "NO_ERRORS" in result:
            return []
        
        # Parse errors
        current_type = None
        current_desc = []
        
        for line in result.split('\n'):
            if line.startswith('ERROR_TYPE:'):
                if current_type and current_desc:
                    errors.append({
                        "type": current_type,
                        "description": " ".join(current_desc).strip()
                    })
                current_type = line.split(':', 1)[1].strip().lower()
                current_desc = []
            elif line.startswith('DESCRIPTION:'):
                current_desc.append(line.split(':', 1)[1].strip())
            elif current_type and line.strip():
                current_desc.append(line.strip())
        
        # Add last error
        if current_type and current_desc:
            errors.append({
                "type": current_type,
                "description": " ".join(current_desc).strip()
            })
        
        return errors
        
    except Exception as e:
        print(f"Error detection error: {e}")
        return []


def generate_solution(code_analysis: Dict, code: str, error_message: str) -> Dict:
    """
    Generate corrected code and explanation.
    
    Returns:
        Dict with fixed_code and explanation
    """
    pattern = code_analysis.get("specific_pattern", "Uncertain")
    code_type = code_analysis.get("code_type", "edge_case")
    
    prompt = f"""You are a code analysis assistant. Generate a solution for this code.

**Code Type:** {code_type}
**Specific Pattern:** {pattern}
**Original Code:**
```python
{code}
```

**Error Message:**
{error_message}

**Task:**
Provide:
1. Corrected or improved version of the code (if needed)
2. Explanation of why this solution works
3. Best practices related to this type of code

**Output Format:**
FIXED_CODE:
[corrected code here]

EXPLANATION:
[explanation here]

**Your Solution:**"""

    try:
        response = OPENAI_CLIENT.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1500,
            temperature=0.4
        )
        
        result = response.choices[0].message.content.strip()
        
        # Parse response
        fixed_code = ""
        explanation = ""
        
        in_code = False
        in_explanation = False
        code_lines = []
        explanation_lines = []
        
        for line in result.split('\n'):
            if line.startswith('FIXED_CODE:'):
                in_code = True
                in_explanation = False
                code_lines = []
            elif line.startswith('EXPLANATION:'):
                in_code = False
                in_explanation = True
                explanation_lines = []
            elif in_code:
                code_lines.append(line)
            elif in_explanation:
                explanation_lines.append(line)
        
        fixed_code = "\n".join(code_lines).strip()
        explanation = "\n".join(explanation_lines).strip()
        
        # Remove code block markers if present
        fixed_code = re.sub(r'^```\w*\n', '', fixed_code)
        fixed_code = re.sub(r'\n```$', '', fixed_code)
        
        return {
            "fixed_code": fixed_code if fixed_code else None,
            "explanation": explanation if explanation else "Solution generation unavailable."
        }
        
    except Exception as e:
        print(f"Solution generation error: {e}")
        return {
            "fixed_code": None,
            "explanation": "Solution generation failed."
        }


def get_video_recommendations(code_analysis: Dict) -> List[Dict]:
    """
    Get pattern-based video recommendations.
    Note: This function returns structure only.
    Actual YouTube search and transcript extraction happens in main.py endpoint.
    
    Returns:
        List of video dicts with title, video_id, start_time, end_time, key_solution_segments
    """
    code_type = code_analysis.get("code_type", "edge_case")
    specific_pattern = code_analysis.get("specific_pattern", "Uncertain")
    confidence = code_analysis.get("confidence", "low")
    
    # If edge case or uncertain, recommend general videos
    if code_type == "edge_case" or specific_pattern == "Uncertain" or confidence == "low":
        return get_general_videos()
    
    # Return structure - will be populated by main endpoint
    return [
        {
            "title": f"{specific_pattern} Tutorial",
            "video_id": "",
            "start_time": 0,
            "end_time": 0,
            "key_solution_segments": []
        }
    ]


def get_general_videos() -> List[Dict]:
    """Return general overview videos for edge cases."""
    return [
        {
            "title": "General Programming Overview",
            "video_id": "",
            "start_time": 0,
            "end_time": 0,
            "key_solution_segments": []
        }
    ]


def extract_key_solution_segments(transcript: List[Dict], pattern_keywords: List[str]) -> List[Dict]:
    """
    Extract key solution segments from transcript with highlighting.
    
    Args:
        transcript: List of transcript segments
        pattern_keywords: Keywords to search for
    
    Returns:
        List of segments with start, end, transcript
    """
    if not transcript:
        return []
    
    keywords_lower = [kw.lower() for kw in pattern_keywords]
    solution_segments = []
    
    for segment in transcript:
        text_lower = segment.get('text', '').lower()
        
        # Check if segment contains keywords
        if any(kw in text_lower for kw in keywords_lower):
            solution_segments.append({
                "start": segment.get('start', 0),
                "end": segment.get('start', 0) + segment.get('duration', 5),
                "transcript": segment.get('text', '')
            })
    
    return solution_segments

