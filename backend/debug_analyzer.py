"""
Debug Analyzer Module
Generates structured debugging insights with root cause analysis
"""

from typing import Optional, Dict
from openai import OpenAI
from config import OPENAI_API_KEY

OPENAI_CLIENT = OpenAI(api_key=OPENAI_API_KEY)


def generate_debug_insight(
    pattern_name: str,
    code: Optional[str],
    error_message: str,
    user_message: str
) -> Dict[str, str]:
    """
    Generate comprehensive debugging insight with root cause analysis.
    
    Args:
        pattern_name: Detected pattern name
        code: Code snippet (if available)
        error_message: Error message
        user_message: User's description
    
    Returns:
        Dict with root_cause, faulty_assumption, correct_flow
    """
    context = f"""
Pattern Detected: {pattern_name}
User Message: {user_message}
Error: {error_message}
Code: {code if code else 'Not provided'}
"""

    prompt = f"""You are a Debugging Intelligence System for a Final Year Project.

Your task is to provide STRUCTURED debugging insight for the existing debugging UI.

**Context:**
{context}

**Output Format (respond in exactly this structure):**

ROOT_CAUSE:
[Identify the fundamental cause of the failure in 1-2 sentences]

FAULTY_ASSUMPTION:
[What incorrect assumption did the developer make?]

CORRECT_FLOW:
[Step-by-step correct execution flow, numbered 1-4 steps]

**Your Structured Response:**"""

    try:
        response = OPENAI_CLIENT.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.4
        )
        
        result = response.choices[0].message.content.strip()
        
        # Parse structured response
        parts = {}
        current_key = None
        current_text = []
        
        for line in result.split('\n'):
            if line.startswith('ROOT_CAUSE:'):
                if current_key:
                    parts[current_key] = '\n'.join(current_text).strip()
                current_key = 'root_cause'
                current_text = []
            elif line.startswith('FAULTY_ASSUMPTION:'):
                if current_key:
                    parts[current_key] = '\n'.join(current_text).strip()
                current_key = 'faulty_assumption'
                current_text = []
            elif line.startswith('CORRECT_FLOW:'):
                if current_key:
                    parts[current_key] = '\n'.join(current_text).strip()
                current_key = 'correct_flow'
                current_text = []
            else:
                current_text.append(line)
        
        # Add last section
        if current_key:
            parts[current_key] = '\n'.join(current_text).strip()
        
        return {
            "root_cause": parts.get("root_cause", "Unable to determine root cause"),
            "faulty_assumption": parts.get("faulty_assumption", "Assumption analysis unavailable"),
            "correct_flow": parts.get("correct_flow", "Correct flow unavailable")
        }
        
    except Exception as e:
        print(f"Debug insight generation error: {e}")
        return {
            "root_cause": f"Pattern detected: {pattern_name}. Detailed analysis unavailable.",
            "faulty_assumption": "Analysis unavailable due to processing error",
            "correct_flow": "Unable to generate correct flow"
        }


def format_debug_insight_for_ui(insight: Dict[str, str]) -> str:
    """
    Format debugging insight for UI display.
    
    Args:
        insight: Dict with root_cause, faulty_assumption, correct_flow
    
    Returns:
        Formatted string ready for UI
    """
    formatted = f"""**🔍 Root Cause:**
{insight['root_cause']}

**❌ Faulty Assumption:**
{insight['faulty_assumption']}

**✅ Correct Execution Flow:**
{insight['correct_flow']}"""
    
    return formatted
