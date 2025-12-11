import io
import os
import re
import shutil
import tempfile
import zipfile
from pathlib import Path
from flask import Flask, render_template, request, send_file, flash, redirect, url_for
import uuid

BASE_DIR = Path(__file__).resolve().parent.parent
AI_FEEDBACK_PATH = BASE_DIR / "ai_feedback.py"
GENERATED_DIR = (BASE_DIR / "web_tool" / "generated")
GENERATED_DIR.mkdir(parents=True, exist_ok=True)


def ensure_import_and_call_in_utils(utils_text: str) -> str:
    """Insert AI feedback import and enhancer call INTO save_results, right before writing results.json.

    Expected insertion inside save_results:
        from ai_feedback import enhance_results_with_ai_feedback
        results = enhance_results_with_ai_feedback(results, autograder_dir)
    """

    text = utils_text

    # Locate save_results function (typed or untyped)
    func_match = re.search(r"def\s+save_results\s*\(.*?\)\s*:\s*", text)
    if not func_match:
        return text  # Can't modify safely

    # From function start, find the line that writes results.json
    start_idx = func_match.end()
    tail = text[start_idx:]
    # Match a 'with open(...results.json' line
    open_match = re.search(r"^([\t ]*)with\s+open\(.*results\s*\/\s*results\.json.*\):", tail, re.MULTILINE)
    if not open_match:
        # Try also matching json.dump line to infer indentation and insert just before it
        dump_match = re.search(r"^([\t ]*)json\.dump\(\s*results\s*,\s*f\b", tail, re.MULTILINE)
        target_indent = dump_match.group(1) if dump_match else "    "
        insertion_point = dump_match.start() + start_idx if dump_match else start_idx
    else:
        target_indent = open_match.group(1)
        insertion_point = open_match.start() + start_idx

    # Build injection block using the same indentation
    import_line = f"{target_indent}from ai_feedback import enhance_results_with_ai_feedback\n"
    call_line = f"{target_indent}results = enhance_results_with_ai_feedback(results, autograder_dir)\n"

    # Avoid duplicate insertion if already present in the next few lines
    preview = text[insertion_point:insertion_point + 500]
    if "enhance_results_with_ai_feedback(" in preview:
        return text
    if "from ai_feedback import enhance_results_with_ai_feedback" in preview:
        import_line = ""  # don't duplicate

    updated = text[:insertion_point] + import_line + call_line + text[insertion_point:]

    # If a top-level import was previously added erroneously, keep it (harmless). We don't attempt to remove.
    return updated


def make_zip_with_ai(upload_zip_bytes: bytes) -> bytes:
    """Process uploaded autograder zip and return modified zip bytes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        src_dir = tmpdir_path / "src"
        out_dir = tmpdir_path / "out"
        src_dir.mkdir()
        out_dir.mkdir()

        # Extract upload
        with zipfile.ZipFile(io.BytesIO(upload_zip_bytes)) as zf:
            zf.extractall(src_dir)

        # Locate utils.py
        utils_path = None
        for p in src_dir.rglob("utils.py"):
            utils_path = p
            break
        if not utils_path:
            raise RuntimeError("Could not find utils.py in the uploaded zip.")

        # Read and modify utils.py
        utils_text = utils_path.read_text(encoding="utf-8")
        modified_utils = ensure_import_and_call_in_utils(utils_text)
        utils_path.write_text(modified_utils, encoding="utf-8")

        # Copy ai_feedback.py into same directory as utils.py
        if not AI_FEEDBACK_PATH.exists():
            raise RuntimeError("ai_feedback.py not found in repository root.")
        shutil.copy2(AI_FEEDBACK_PATH, utils_path.parent / "ai_feedback.py")

        # Re-zip contents
        mem_buf = io.BytesIO()
        with zipfile.ZipFile(mem_buf, mode="w", compression=zipfile.ZIP_DEFLATED) as out_zip:
            for path in src_dir.rglob("*"):
                if path.is_file():
                    arcname = path.relative_to(src_dir).as_posix()
                    out_zip.write(path, arcname)
        mem_buf.seek(0)
        return mem_buf.read()


def create_app():
    app = Flask(__name__)
    app.secret_key = os.environ.get("SECRET_KEY", "dev-secret")

    @app.route("/", methods=["GET"]) 
    def index():
        ready_id = request.args.get("ready")
        return render_template("index.html", ready_id=ready_id)

    @app.route("/process", methods=["POST"]) 
    def process():
        file = request.files.get("bundle")
        if not file or not file.filename.lower().endswith(".zip"):
            flash("Please upload a .zip file of your autograder bundle.")
            return redirect(url_for("index"))
        try:
            zip_bytes = file.read()
            output_zip = make_zip_with_ai(zip_bytes)
            # Persist the generated zip to a temporary server folder
            file_id = str(uuid.uuid4())
            out_path = GENERATED_DIR / f"{file_id}.zip"
            with open(out_path, "wb") as f:
                f.write(output_zip)
            # Redirect to index with a ready flag to show a manual download button
            flash("Your bundle is ready. Click the button below to download.")
            return redirect(url_for("index", ready=file_id))
        except Exception as e:
            flash(f"Error: {e}")
            return redirect(url_for("index"))

    @app.route("/download/<file_id>", methods=["GET"]) 
    def download(file_id: str):
        # Serve the previously generated file by id
        safe_id = re.sub(r"[^a-zA-Z0-9\-]", "", file_id)
        path = GENERATED_DIR / f"{safe_id}.zip"
        if not path.exists():
            flash("Download not found or expired. Please regenerate.")
            return redirect(url_for("index"))
        return send_file(path, mimetype="application/zip", as_attachment=True, download_name="autograder_with_ai_feedback.zip")

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)


