"""
Pattern Detection Module for Code Intelligence Layer
Identifies coding problem patterns from code snippets and error messages
"""

from typing import Dict, List, Optional, Tuple
from openai import OpenAI
from config import OPENAI_API_KEY

OPENAI_CLIENT = OpenAI(api_key=OPENAI_API_KEY)

# Pattern Library - Database of known coding patterns
PATTERN_LIBRARY = {
    "async_await_misuse": {
        "name": "Async/Await Misuse",
        "pattern_type": "PRIMARY",
        "task_type": "async_handling",
        "description": "Using synchronous code in async functions or not awaiting async calls",
        "keywords": ["async", "await", "coroutine", "asyncio", "asynchronous"],
        "common_errors": ["coroutine was never awaited", "RuntimeWarning", "event loop"],
        "learning_intent": "Understanding asynchronous programming and proper async/await usage"
    },
    "linear_search_algorithm": {
        "name": "Linear Search Algorithm",
        "pattern_type": "PRIMARY",
        "task_type": "searching",
        "description": "Using linear/sequential search O(n) - iterating through array element by element",
        "keywords": ["loop", "iterate", "search", "find", "array", "linear", "sequential"],
        "common_errors": ["slow search", "timeout", "performance on large arrays"],
        "learning_intent": "Understanding linear search complexity and when to use more efficient search algorithms"
    },
    "binary_search_algorithm": {
        "name": "Binary Search Algorithm",
        "pattern_type": "PRIMARY",
        "task_type": "searching",
        "description": "Binary search issues - requires sorted array, O(log n) complexity",
        "keywords": ["binary", "sorted", "divide", "mid", "log", "search"],
        "common_errors": ["array not sorted", "infinite loop in binary search"],
        "learning_intent": "Understanding binary search requirements and O(log n) complexity"
    },
    "sorting_algorithm_issue": {
        "name": "Sorting Algorithm Issue",
        "pattern_type": "PRIMARY",
        "task_type": "sorting",
        "description": "Inefficient sorting algorithms (bubble/selection O(n²) vs quicksort/mergesort O(n log n))",
        "keywords": ["sort", "bubble", "selection", "quicksort", "mergesort", "nested loop"],
        "common_errors": ["slow sorting", "timeout on large arrays"],
        "learning_intent": "Understanding sorting algorithm complexities and choosing the right one"
    },
    "api_lifecycle_misuse": {
        "name": "API Lifecycle Misuse",
        "description": "Incorrect use of API lifecycle methods (React, Flask, FastAPI, etc.)",
        "keywords": ["useEffect", "componentDidMount", "lifecycle", "hook", "startup", "shutdown"],
        "common_errors": ["infinite loop", "re-render", "memory leak", "not cleaned up"],
        "learning_intent": "Understanding framework lifecycle and proper resource management"
    },
    "state_management_error": {
        "name": "State Management Error",
        "description": "Improper state handling causing race conditions or stale data",
        "keywords": ["state", "setState", "useState", "redux", "context", "closure"],
        "common_errors": ["stale state", "race condition", "state not updating"],
        "learning_intent": "Understanding state management patterns and immutability"
    },
    "error_handling_blind_spot": {
        "name": "Error Handling Blind Spot",
        "description": "Missing or improper error handling leading to silent failures",
        "keywords": ["try", "catch", "exception", "error", "unhandled"],
        "common_errors": ["unhandled exception", "silent failure", "crashes without error"],
        "learning_intent": "Implementing comprehensive error handling and logging"
    },
    "database_query_inefficiency": {
        "name": "Database Query Inefficiency",
        "description": "N+1 queries, missing indexes, or inefficient query patterns",
        "keywords": ["query", "database", "sql", "orm", "select", "join"],
        "common_errors": ["slow query", "too many queries", "n+1 problem"],
        "learning_intent": "Optimizing database queries and understanding ORMs"
    },
    "memory_management_issue": {
        "name": "Memory Management Issue",
        "description": "Memory leaks, excessive memory usage, or poor garbage collection",
        "keywords": ["memory", "leak", "garbage", "heap", "reference"],
        "common_errors": ["out of memory", "memory leak", "heap overflow"],
        "learning_intent": "Understanding memory management and preventing leaks"
    },
    "security_vulnerability": {
        "name": "Security Vulnerability",
        "description": "SQL injection, XSS, CSRF, or other security issues",
        "keywords": ["injection", "xss", "csrf", "security", "authentication", "password"],
        "common_errors": ["sql injection", "cross-site scripting", "unauthorized"],
        "learning_intent": "Implementing secure coding practices and input validation"
    },
    "deployment_environment_mismatch": {
        "name": "Deployment/Environment Mismatch",
        "description": "Works locally but fails in production due to environment differences",
        "keywords": ["production", "deployment", "environment", "config", "env variable"],
        "common_errors": ["works locally", "production error", "environment variable not set"],
        "learning_intent": "Managing environment configurations and deployment best practices"
    },
    "type_coercion_error": {
        "name": "Type Coercion Error",
        "pattern_type": "SECONDARY",
        "task_type": "syntax",
        "description": "Unexpected type conversions or type-related bugs (SECONDARY - not primary pattern)",
        "keywords": ["type", "typeof", "NaN", "undefined", "null", "coercion", "===", "=="],
        "common_errors": ["NaN", "undefined is not a function", "cannot read property"],
        "learning_intent": "Understanding type systems and type safety"
    },
    "concurrency_race_condition": {
        "name": "Concurrency/Race Condition",
        "description": "Issues with concurrent access to shared resources",
        "keywords": ["thread", "concurrent", "lock", "mutex", "race", "parallel"],
        "common_errors": ["race condition", "deadlock", "concurrent modification"],
        "learning_intent": "Understanding concurrency patterns and synchronization"
    },
    "dependency_version_conflict": {
        "name": "Dependency Version Conflict",
        "pattern_type": "PRIMARY",
        "task_type": "deployment",
        "description": "Package version mismatches or dependency hell",
        "keywords": ["dependency", "version", "package", "npm", "pip", "install"],
        "common_errors": ["dependency conflict", "version mismatch", "module not found"],
        "learning_intent": "Managing dependencies and understanding semantic versioning"
    },
    # SECONDARY PATTERN - Syntax/Logic Errors
    "syntax_logic_error": {
        "name": "Syntax/Logic Error",
        "pattern_type": "SECONDARY",
        "task_type": "syntax",
        "description": "Basic syntax mistakes (=== vs ==, missing semicolons, etc.)",
        "keywords": ["syntax", "==", "===", "semicolon", "typo", "undefined"],
        "common_errors": ["syntax error", "unexpected token", "missing"],
        "learning_intent": "Understanding language syntax and common pitfalls"
    }
}


def detect_pattern(code: Optional[str], error_message: str, user_message: str) -> Tuple[str, float]:
    """
    Detect the coding problem pattern from code and error message.
    
    Args:
        code: Optional code snippet
        error_message: Error message or problem description
        user_message: User's description of the problem
    
    Returns:
        Tuple of (pattern_key, confidence_score)
    """
    # Build context for GPT-4o
    context_parts = []
    if user_message:
        context_parts.append(f"User Description: {user_message}")
    if error_message:
        context_parts.append(f"Error/Problem: {error_message}")
    if code:
        context_parts.append(f"Code:\n{code}")
    
    context = "\n\n".join(context_parts)
    
    # Pattern detection prompt
    pattern_names = "\n".join([f"- {key}: {info['name']}" for key, info in PATTERN_LIBRARY.items()])
    
    prompt = f"""You are a Code Pattern Intelligence System for a Final Year Project.

Your task is to identify the CATEGORY of coding problem, not just explain the code.

**Available Patterns:**
{pattern_names}

**Input:**
{context}

**Instructions:**
1. Analyze the PATTERN behind the problem, ignore surface syntax
2. Return ONLY the pattern key from the list above (e.g., "async_await_misuse")
3. On the next line, return a confidence score (0-100)
4. Format: pattern_key\\nconfidence_score

**Example Output:**
async_await_misuse
85

**Your Response:**"""

    try:
        response = OPENAI_CLIENT.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100,
            temperature=0.3  # Lower temperature for more consistent pattern detection
        )
        
        result = response.choices[0].message.content.strip().split('\n')
        pattern_key = result[0].strip()
        confidence = float(result[1].strip()) if len(result) > 1 else 70.0
        
        # Validate pattern key
        if pattern_key not in PATTERN_LIBRARY:
            # Fallback to keyword matching
            pattern_key = _fallback_pattern_detection(context.lower())
            confidence = max(confidence - 20, 50)
        
        return pattern_key, confidence
        
    except Exception as e:
        print(f"Pattern detection error: {e}")
        # Fallback to keyword-based detection
        pattern_key = _fallback_pattern_detection((context or "").lower())
        return pattern_key, 60.0




def detect_primary_and_secondary_patterns(
    code: Optional[str],
    error_message: str,
    user_message: str
) -> Dict[str, any]:
    """
    Detect PRIMARY pattern (algorithm/architecture) and SECONDARY issues (syntax).
    Enforces rule: Algorithmic intent ALWAYS identified before syntax bugs.
    
    Args:
        code: Optional code snippet
        error_message: Error message
        user_message: User's description
    
    Returns:
        Dict with primary_pattern, secondary_issues, confidence
    """
    # First detect all patterns
    primary_pattern_key, confidence = detect_pattern(code, error_message, user_message)
    
    # Check if detected pattern is PRIMARY or SECONDARY
    pattern_info = PATTERN_LIBRARY.get(primary_pattern_key, {})
    pattern_type = pattern_info.get("pattern_type", "PRIMARY")
    
    # If detected pattern is SECONDARY, try to find PRIMARY pattern
    if pattern_type == "SECONDARY":
        # Look for PRIMARY patterns in code/error
        context = f"{user_message} {error_message} {code or ''}".lower()
        
        # Search for PRIMARY patterns
        primary_candidates = []
        for key, info in PATTERN_LIBRARY.items():
            if info.get("pattern_type") == "PRIMARY":
                score = 0
                for keyword in info.get('keywords', []):
                    if keyword.lower() in context:
                        score += 1
                if score > 0:
                    primary_candidates.append((key, score))
        
        # If PRIMARY pattern found, use it and make original pattern SECONDARY
        if primary_candidates:
            primary_pattern_key = max(primary_candidates, key=lambda x: x[1])[0]
            secondary_pattern = get_pattern_name(detect_pattern(code, error_message, user_message)[0])
            return {
                "primary_pattern": primary_pattern_key,
                "primary_pattern_name": get_pattern_name(primary_pattern_key),
                "secondary_issues": [secondary_pattern],
                "confidence": confidence
            }
    
    # If PRIMARY pattern detected, check for SECONDARY issues
    secondary_issues = []
    context_lower = f"{code or ''} {error_message}".lower()
    
    # Check for common secondary issues
    if "===" in context_lower or "==" in context_lower or "=" in context_lower:
        if "comparison" in error_message.lower() or "assignment" in context_lower:
            secondary_issues.append("Assignment operator (=) used instead of comparison (==)")
    
    if "type" in error_message.lower() and pattern_type != "SECONDARY":
        secondary_issues.append("Type coercion issue")
    
    return {
        "primary_pattern": primary_pattern_key,
        "primary_pattern_name": get_pattern_name(primary_pattern_key),
        "secondary_issues": secondary_issues,
        "confidence": confidence
    }


def get_pattern_name(pattern_key: str) -> str:
    """Get pattern name from key"""
    return PATTERN_LIBRARY.get(pattern_key, {}).get("name", "Unknown Pattern")


def _fallback_pattern_detection(text: str) -> str:
    """Fallback keyword matching if GPT fails"""
    scores = {}
    for key, info in PATTERN_LIBRARY.items():
        score = 0
        for keyword in info['keywords']:
            score += text.count(keyword.lower()) * 2
        for error in info['common_errors']:
            if error.lower() in text:
                score += 5
        scores[key] = score
    
    # Return pattern with highest score, or generic error handling
    if max(scores.values()) > 0:
        return max(scores, key=scores.get)
    return "error_handling_blind_spot"


def generate_pattern_explanation(pattern_key: str, code: Optional[str], error: str) -> str:
    """
    Generate explanation of why this pattern fails.
    
    Args:
        pattern_key: Detected pattern key
        code: Optional code snippet
        error: Error message
    
    Returns:
        Detailed pattern explanation
    """
    pattern_info = PATTERN_LIBRARY.get(pattern_key, {})
    pattern_name = pattern_info.get("name", "Unknown Pattern")
    
    prompt = f"""You are a Code Pattern Intelligence System.

**Detected Pattern:** {pattern_name}
**Pattern Description:** {pattern_info.get('description', '')}

**Context:**
Error: {error}
{f"Code: {code}" if code else ""}

**Task:** Explain WHY this pattern fails (not what the code does).

Focus on:
1. The conceptual mistake in the pattern
2. Why developers make this mistake
3. What the correct mental model should be

Keep it concise (3-4 sentences).

**Your Explanation:**"""

    try:
        response = OPENAI_CLIENT.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.5
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Pattern explanation error: {e}")
        return f"{pattern_name}: {pattern_info.get('description', 'Pattern detected but explanation unavailable.')}"


def get_pattern_solution(pattern_key: str, code: Optional[str]) -> str:
    """
    Generate pattern-based solution with best practices.
    
    Args:
        pattern_key: Detected pattern key
        code: Optional code snippet to correct
    
    Returns:
        Corrected code or solution strategy
    """
    pattern_info = PATTERN_LIBRARY.get(pattern_key, {})
    
    prompt = f"""You are a Code Pattern Intelligence System.

**Pattern:** {pattern_info.get('name', '')}
**User's Code:**
{code if code else "No code provided"}

**Task:** Provide a PATTERN-BASED solution, not just a code fix.

Include:
1. Corrected code following best practices for this pattern
2. Brief comment explaining the key change

Return ONLY the corrected code with minimal comments.

**Corrected Code:**"""

    try:
        response = OPENAI_CLIENT.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=800,
            temperature=0.4
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Solution generation error: {e}")
        return None


def map_pattern_to_search_query(pattern_key: str) -> str:
    """
    Convert pattern to optimal search query for external knowledge search.
    
    Args:
        pattern_key: Detected pattern key
    
    Returns:
        Optimized search query
    """
    pattern_info = PATTERN_LIBRARY.get(pattern_key, {})
    name = pattern_info.get("name", "")
    keywords = pattern_info.get("keywords", [])
    
    # Combine name and top keywords for search
    query_parts = [name]
    if keywords:
        query_parts.extend(keywords[:3])
    
    return " ".join(query_parts)


def get_learning_intent(pattern_key: str) -> str:
    """Get the learning intent for this pattern"""
    return PATTERN_LIBRARY.get(pattern_key, {}).get(
        "learning_intent", 
        "Understanding best practices and avoiding common pitfalls"
    )


def get_pattern_keywords(pattern_key: str) -> List[str]:
    """Get keywords for a pattern (for video transcript search)"""
    return PATTERN_LIBRARY.get(pattern_key, {}).get("keywords", [])
