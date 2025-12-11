
"""
AI-Powered Feedback Generator for Autograders
Drop this file into your autograder folder and add one line to utils.py
"""

import json
import os
import re
from typing import Dict, List, Any
import requests

# ============== CONFIGURATION ==============
API_KEY_HERE = ""  # Add your OpenAI API key here
MODEL = "gpt-4o"  # or "gpt-4o-mini" for faster/cheaper
MAX_CODE_LENGTH = 8000  # Characters to include from student code
# ===========================================


def enhance_results_with_ai_feedback(results: dict, autograder_dir: str) -> dict:
    """
    Enhance autograder results with AI-generated feedback.
    
    Args:
        results: The autograder results dictionary
        autograder_dir: Path to the autograder directory
        
    Returns:
        Enhanced results dictionary with AI feedback added
    """
    
    # If no API key configured, return original results
    if not API_KEY_HERE:
        print("AI Feedback: No API key configured. Skipping AI feedback generation.")
        return results
    
    try:
        # Get student code
        student_code = get_student_code(autograder_dir)
        
        # Generate feedback via GPT-4
        feedback = generate_feedback(results, student_code)
        
        # Add feedback to results
        if feedback:
            results = add_feedback_to_results(results, feedback)
            
    except Exception as e:
        # If anything fails, just return original results
        print(f"AI Feedback Error: {e}")
        
    return results


def get_student_code(autograder_dir: str) -> str:
    """Extract student code from submission."""
    
    student_code = ""
    
    # Try to read the converted Python file first (if it exists)
    submission_py = os.path.join(autograder_dir, 'source', 'submission.py')
    if os.path.exists(submission_py):
        try:
            with open(submission_py, 'r', encoding='utf-8') as f:
                student_code = f.read()
                # Clean up the code dividers
                student_code = re.sub(r'#{50,}', '\n', student_code)
                return student_code[:MAX_CODE_LENGTH]
        except:
            pass
    
    # Otherwise try to read notebook files
    submission_dir = os.path.join(autograder_dir, 'submission')
    if os.path.exists(submission_dir):
        for file in os.listdir(submission_dir):
            if file.endswith('.ipynb'):
                try:
                    notebook_path = os.path.join(submission_dir, file)
                    with open(notebook_path, 'r', encoding='utf-8') as f:
                        notebook = json.load(f)
                        
                    # Extract code cells marked as AUTOGRADED
                    code_cells = []
                    for cell in notebook.get('cells', []):
                        if cell.get('cell_type') == 'code':
                            source = cell.get('source', [])
                            if source and len(source) > 0:
                                # Check if it's autograded
                                first_line = source[0] if isinstance(source, list) else source.split('\n')[0]
                                if '# AUTOGRADED' in first_line or len(code_cells) == 0:
                                    cell_text = ''.join(source) if isinstance(source, list) else source
                                    code_cells.append(cell_text)
                    
                    student_code = '\n\n'.join(code_cells)
                    break
                except:
                    continue
    
    # Truncate if too long
    if len(student_code) > MAX_CODE_LENGTH:
        student_code = student_code[:MAX_CODE_LENGTH] + "\n\n[Code truncated for brevity...]"
    
    return student_code


def generate_feedback(results: dict, student_code: str) -> Dict[str, Any]:
    """Generate AI feedback using GPT-4."""
    
    # Prepare the test results summary
    test_summaries = []
    for test in results.get('tests', []):
        test_info = {
            'name': test.get('name', 'Unknown Test'),
            'score': test.get('score', 0),
            'max_score': test.get('max_score', 0),
            'output': test.get('output', '')[:500]  # Limit output length
        }
        test_summaries.append(test_info)
    
    # Create the prompt
    prompt = create_feedback_prompt(test_summaries, student_code)
    
    # Make API call
    try:
        headers = {
            'Authorization': f'Bearer {API_KEY_HERE}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'model': MODEL,
            'messages': [
                {
                    'role': 'system',
                    'content': """You are a direct, knowledgeable programming instructor providing feedback on student code submissions. 
                    Give specific, actionable feedback in 2-3 sentences per graded section.
                    Focus on what the student did wrong and how to fix it, or what they did well if they succeeded.
                    Be direct and technical - avoid unnecessary encouragement."""
                },
                {
                    'role': 'user',
                    'content': prompt
                }
            ],
            'temperature': 0.3,
            'max_tokens': 1500
        }
        
        response = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers=headers,
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            feedback_text = result['choices'][0]['message']['content']
            return parse_feedback_response(feedback_text)
        else:
            print(f"AI Feedback API Error: {response.status_code} - {response.text}")
            return {}
            
    except Exception as e:
        print(f"AI Feedback Generation Error: {e}")
        return {}


def create_feedback_prompt(test_summaries: List[Dict], student_code: str) -> str:
    """Create the prompt for GPT-4."""
    
    prompt = f"""Analyze this student's code submission and provide feedback based on the autograder results.

STUDENT CODE:
```python
{student_code}
```

AUTOGRADER RESULTS:
"""
    
    for test in test_summaries:
        prompt += f"\n{test['name']}: {test['score']}/{test['max_score']} points"
        if test['output']:
            prompt += f"\nAutograder output: {test['output']}\n"
    
    prompt += """

Provide feedback in the following JSON format:
{
    "overall": "2-3 sentences of direct overall assessment focusing on key strengths or weaknesses",
    "tests": {
        "test_name_1": "2-3 sentences of specific feedback for this test",
        "test_name_2": "2-3 sentences of specific feedback for this test"
    }
}

For each test, analyze what the student did wrong (or right) and provide specific guidance.
If they failed, explain the likely issue and how to fix it.
If they succeeded, briefly note what they did well.
Focus on the code implementation, not just restating the scores."""
    
    return prompt


def parse_feedback_response(feedback_text: str) -> Dict[str, Any]:
    """Parse the GPT-4 response into structured feedback."""
    
    try:
        # Try to extract JSON from the response
        json_match = re.search(r'\{.*\}', feedback_text, re.DOTALL)
        if json_match:
            feedback_json = json.loads(json_match.group())
            return feedback_json
    except:
        pass
    
    # Fallback: parse as plain text
    feedback = {}
    
    # Try to extract overall feedback
    overall_match = re.search(r'overall[:\s]+(.+?)(?:tests:|$)', feedback_text, re.IGNORECASE | re.DOTALL)
    if overall_match:
        feedback['overall'] = overall_match.group(1).strip()
    
    # Try to extract test-specific feedback
    feedback['tests'] = {}
    test_pattern = r'([^:]+):\s*([^:]+?)(?=\n[^:]+:|$)'
    matches = re.finditer(test_pattern, feedback_text, re.MULTILINE)
    for match in matches:
        test_name = match.group(1).strip()
        test_feedback = match.group(2).strip()
        if test_name.lower() != 'overall':
            feedback['tests'][test_name] = test_feedback
    
    return feedback if feedback else {'overall': 'Unable to generate detailed feedback.', 'tests': {}}


def add_feedback_to_results(results: dict, feedback: Dict[str, Any]) -> dict:
    """Add AI feedback to the results dictionary by appending to output fields."""
    
    # Add overall feedback to main output
    if 'overall' in feedback:
        current_output = results.get('output', '')
        results['output'] = current_output + '\n\n=== AI FEEDBACK ===\n' + feedback['overall']
    
    # Add test-specific feedback to each test's output
    test_feedback = feedback.get('tests', {})
    for test in results.get('tests', []):
        test_name = test.get('name', '')
        feedback_to_add = None
        
        # Try to find matching feedback (case-insensitive)
        for feedback_key, feedback_value in test_feedback.items():
            if test_name.lower() in feedback_key.lower() or feedback_key.lower() in test_name.lower():
                feedback_to_add = feedback_value
                break
        
        # If no specific feedback found, generate generic based on score
        if not feedback_to_add:
            score = test.get('score', 0)
            max_score = test.get('max_score', 0)
            if max_score > 0:
                percentage = (score / max_score) * 100
                if percentage >= 90:
                    feedback_to_add = "Good implementation for this section."
                elif percentage >= 50:
                    feedback_to_add = "Partial credit earned. Review the test requirements and error messages."
                else:
                    feedback_to_add = "Significant issues detected. Check the error output and revise your approach."
        
        # Append feedback to test's output field
        if feedback_to_add:
            current_output = test.get('output', '')
            test['output'] = current_output + '\n\n📝 AI Feedback:\n' + feedback_to_add
    
    return results


# For testing purposes
if __name__ == "__main__":
    # Example test
    sample_results = {
        "tests": [
            {"name": "test_1", "score": 10, "max_score": 10, "output": "All tests passed"},
            {"name": "test_2", "score": 5, "max_score": 10, "output": "Failed assertion"},
        ],
        "output": "Completed"
    }
    
    # Test the enhancement (would need actual autograder_dir)
    enhanced = enhance_results_with_ai_feedback(sample_results, "/path/to/autograder")
    print(json.dumps(enhanced, indent=2))
