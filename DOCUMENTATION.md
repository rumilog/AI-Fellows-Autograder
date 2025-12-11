## AI Feedback: User Guide and Technical Overview

### Table of contents
- Overview
- Features
- Prerequisites
- Installation
- Usage
- Example output
- Configuration
- How it works
- Limitations and scope
- Privacy and data handling
- Troubleshooting
- FAQ
- Disable/Uninstall
- Support and maintenance

### What this is
Add AI-powered, test-aware feedback to your Gradescope autograders with a lightweight drop-in. The AI uses the autograder’s own grades and outputs to focus feedback on what the student did wrong and how to fix it, then appends that guidance directly into the results students see on Gradescope. It runs alongside your autograder and does not change scores.

### Who this is for
- Instructors/TAs who already have a working Gradescope autograder and want richer, more actionable feedback without rewriting their grader.

### Features
- Works alongside existing autograders; does not modify scoring.
- Uses your tests’ grades and outputs to target only mistakes and provide tips.
- Adds both overall and per-test feedback directly into Gradescope output.
- Graceful failure: if the API call fails, grading proceeds as normal.

### Prerequisites
- An existing Gradescope autograder that writes `results/results.json` via `utils.py`.
- An OpenAI API key with network egress from the autograder environment.

## Installation
Place `ai_feedback.py` in the same directory as your autograder’s `utils.py`.

## Usage
Follow this once per autograder. This mirrors and expands on `README_AI_FEEDBACK.md`.

1) Add your OpenAI API key
- Open `ai_feedback.py` and set `API_KEY_HERE` to your key.

2) Wire it into your autograder
- In your autograder's `utils.py`, locate the `save_results(results: dict, autograder_dir: str)` function and add the two lines shown below before writing the `results.json` file:

```python
from ai_feedback import enhance_results_with_ai_feedback
results = enhance_results_with_ai_feedback(results, autograder_dir)
```

3) Ship the file
- Place `ai_feedback.py` in the same directory as `utils.py` within your autograder bundle.

4) Run as usual
- Upload your autograder to Gradescope and grade normally. If the API is unavailable or your key is missing, grading proceeds normally (AI feedback is simply skipped).

## Example output
- The autograder’s usual output appears, plus an additional section:
  - Overall feedback appended to the top-level `output` as a block headed by `=== AI FEEDBACK ===`.
  - Per-test feedback appended to each test’s `output` as a “📝 AI Feedback:” note.

Example (abbreviated):

```text
=== AI FEEDBACK ===
Your solution correctly implements X but fails edge case Y. Consider handling ...

Test: parse_input
...
📝 AI Feedback:
The parser works for well-formed input but breaks on empty tokens. Guard against ...
```

## Configuration
Edit the constants at the top of `ai_feedback.py`:
- MODEL: `"gpt-4o"` (higher quality) or `"gpt-4o-mini"` (faster/cheaper)
- MAX_CODE_LENGTH: cap on characters of student code included in the prompt (default 8000)

No other changes are required.

## How it works
This summarizes the flow implemented in `ai_feedback.py`.

- Entry point: `enhance_results_with_ai_feedback(results, autograder_dir)`
  - If no `API_KEY_HERE` is set, it logs a message and returns `results` unchanged.
  - Otherwise it collects student code and test summaries (including the autograder’s grades), calls the model, parses the response, and appends feedback back into `results`.

- Collecting student code: `get_student_code(autograder_dir)`
  - Checks `source/submission.py` first (if your pipeline converts notebooks to Python).
  - If not present, scans `submission/*.ipynb` and concatenates code cells (prioritizing cells marked `# AUTOGRADED`).
  - Truncates to `MAX_CODE_LENGTH` with a clear truncation note.

- Building the prompt: `create_feedback_prompt(test_summaries, student_code)`
  - Summarizes each test: name, score/max, and a trimmed `output` (up to ~500 chars).
  - Asks the model for a specific JSON shape:
    - `overall`: 2–3 sentence summary.
    - `tests`: map of test name → 2–3 sentence targeted feedback emphasizing mistakes and actionable tips.

- Calling the model: `generate_feedback(results, student_code)`
  - Sends a chat completion request with a concise system prompt geared toward technical, actionable, and direct feedback.
  - On success, extracts the assistant message text and hands it to the parser.

- Parsing and resilience: `parse_feedback_response(feedback_text)`
  - Tries to extract JSON from the response; if not valid JSON, falls back to heuristic parsing of plain text.
  - Guarantees a dictionary with at least `overall` and `tests` keys.

- Attaching feedback: `add_feedback_to_results(results, feedback)`
  - Appends `overall` feedback to the top-level `results['output']` under the `=== AI FEEDBACK ===` header.
  - For each test:
    - Attempts case-insensitive name matching to map model feedback to the test.
    - If missing, generates generic guidance based on score percentage thresholds.
    - Appends to the test’s `output` under “📝 AI Feedback:”.
  - Scores are never modified; the AI only adds explanatory feedback based on the autograder’s outcomes.

- Failure behavior
  - Any exception or API error logs a message and returns the original `results` untouched to ensure grading is never blocked.

## Limitations and scope
- Feedback reflects what your tests observe; if tests are sparse, feedback may be broad.
- Very large submissions are truncated to `MAX_CODE_LENGTH` to control cost/latency.
- The AI focuses on mistakes and tips; positive notes are brief when tests pass.

## Privacy and data handling
- Only the following data is sent to the AI API:
  - A truncated slice of the student’s code (up to `MAX_CODE_LENGTH`).
  - Test names, scores, max scores, and a truncated `output` per test.
- Consider redacting sensitive tokens or data in your own autograder if present in stdout/stderr.
- If your institution has policies around LLM usage, configure or proxy the API accordingly.

## Troubleshooting
- No AI feedback appears
  - Check `API_KEY_HERE` in `ai_feedback.py` is set and valid.
  - Verify the two integration lines run before `results.json` is written.
  - Ensure outbound network access from the autograder environment.

- Feedback seems generic for some tests
  - The model couldn’t confidently match a feedback entry to a test name; generic feedback is used. Consider making test names more descriptive or ensuring per-test outputs include distinct context.

- Large notebooks not fully considered
  - Increase `MAX_CODE_LENGTH` if needed, understanding longer prompts increase cost/latency.

## FAQ
- Do I need to change my tests? No. The tool consumes the existing `results` structure and augments it.
- Will grading be slower? A single API call per submission is made; typical latency is a few seconds, depending on model and prompt size.
- What happens if the API is down? Grading continues and skips AI feedback.
- Can I disable per-test feedback? You can edit `add_feedback_to_results` to only keep the `overall` note.

## Disable/Uninstall
- Temporarily disable: remove or comment out the two integration lines in `save_results`, or leave `API_KEY_HERE` empty.
- Uninstall: delete `ai_feedback.py` and remove the import and function call from `utils.py`.

## Support and maintenance
- For issues or enhancements, open an issue in your repository or contact the course tooling maintainer.
- Keep your API key secure and rotate it per your organization’s policy.

## Related setup
For a quick-start reference and the minimal integration snippet, see `README_AI_FEEDBACK.md`.


