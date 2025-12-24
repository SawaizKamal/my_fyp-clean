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
        "description": "Using synchronous code in async functions or not awaiting async calls",
        "keywords": ["async", "await", "coroutine", "asyncio", "asynchronous"],
        "common_errors": ["coroutine was never awaited", "RuntimeWarning", "event loop"],
        "learning_intent": "Understanding asynchronous programming and proper async/await usage"
    },
    "algorithm_complexity": {
        "name": "Algorithm Complexity Issue",
        "description": "Using inefficient algorithms (O(n²) when O(n log n) exists)",
        "keywords": ["nested loop", "performance", "slow", "timeout", "efficiency"],
        "common_errors": ["timeout", "too slow", "performance issue"],
        "learning_intent": "Understanding algorithm complexity and optimization techniques"
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
        "description": "Unexpected type conversions or type-related bugs",
        "keywords": ["type", "typeof", "NaN", "undefined", "null", "coercion"],
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
        "description": "Package version mismatches or dependency hell",
        "keywords": ["dependency", "version", "package", "npm", "pip", "install"],
        "common_errors": ["dependency conflict", "version mismatch", "module not found"],
        "learning_intent": "Managing dependencies and understanding semantic versioning"
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
