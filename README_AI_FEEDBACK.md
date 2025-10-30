# AI Feedback for Autograders

## Quick Setup (2 steps)

### 1. Add your OpenAI API key
Open `ai_feedback.py` and add your API key at the top:
```python
API_KEY_HERE = "your-openai-api-key-here"
```

### 2. Modify `utils.py`
In your autograder's `utils.py`, find the `save_results` function and add these two lines:

```python
def save_results(results: dict, autograder_dir: str):
    # Add these two lines BEFORE saving the JSON:
    from ai_feedback import enhance_results_with_ai_feedback
    results = enhance_results_with_ai_feedback(results, autograder_dir)
    
    # This is the existing code that saves the JSON:
    with open(f'{autograder_dir}/results/results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=4)
```

## That's it!

- Drop `ai_feedback.py` into your autograder folder (same directory as `utils.py`)
- The AI will analyze student code and add feedback to each graded section
- If the API fails, the autograder continues working normally
- Feedback appears directly in Gradescope's output display

## Optional Configuration

In `ai_feedback.py` you can adjust:
- `MODEL`: Switch between "gpt-4o" (better) and "gpt-4o-mini" (cheaper/faster)
- `MAX_CODE_LENGTH`: How much student code to analyze (default: 8000 chars)
