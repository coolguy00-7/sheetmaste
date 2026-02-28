import os
import base64
from io import BytesIO

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from pypdf import PdfReader

load_dotenv()

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.post("/api/analyze-practice")
def analyze_practice():
    files = request.files.getlist("files")
    if not files:
        return jsonify({"error": "Upload at least one text file."}), 400

    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        return jsonify({"error": "Missing OPENROUTER_API_KEY in environment."}), 400

    max_files = 20
    max_chars_per_file = 12000
    max_total_chars = 90000
    max_image_bytes_per_file = 8 * 1024 * 1024
    max_total_image_bytes = 24 * 1024 * 1024
    allowed_extensions = {".txt", ".md", ".csv", ".rtf", ".pdf", ".png", ".jpg", ".jpeg"}

    if len(files) > max_files:
        return jsonify({"error": f"Too many files. Max allowed is {max_files}."}), 400

    parsed_files = []
    image_files = []
    total_chars = 0
    total_image_bytes = 0

    for uploaded_file in files:
        filename = (uploaded_file.filename or "").strip()
        if not filename:
            continue

        _, ext = os.path.splitext(filename.lower())
        if ext and ext not in allowed_extensions:
            return jsonify(
                {
                    "error": (
                        f"Unsupported file extension for '{filename}'. "
                        "Allowed: .txt, .md, .csv, .rtf, .pdf, .png, .jpg, .jpeg"
                    )
                }
            ), 400

        raw = uploaded_file.read()
        if not raw:
            continue

        if ext in {".png", ".jpg", ".jpeg"}:
            image_size = len(raw)
            if image_size > max_image_bytes_per_file:
                return jsonify(
                    {"error": f"'{filename}' exceeds {max_image_bytes_per_file // (1024 * 1024)}MB image limit."}
                ), 400
            total_image_bytes += image_size
            if total_image_bytes > max_total_image_bytes:
                return jsonify(
                    {"error": f"Total image upload size exceeds {max_total_image_bytes // (1024 * 1024)}MB."}
                ), 400

            mime = "image/png" if ext == ".png" else "image/jpeg"
            data_uri = f"data:{mime};base64,{base64.b64encode(raw).decode('utf-8')}"
            image_files.append({"filename": filename, "data_uri": data_uri})
            continue

        if ext == ".pdf":
            try:
                reader = PdfReader(BytesIO(raw))
                text = "\n".join((page.extract_text() or "") for page in reader.pages).strip()
            except Exception:
                return jsonify({"error": f"Could not read text from PDF '{filename}'."}), 400
        else:
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                try:
                    text = raw.decode("latin-1")
                except UnicodeDecodeError:
                    return jsonify({"error": f"Could not decode '{filename}' as text."}), 400

        text = (text or "").strip()
        if not text:
            continue

        if len(text) > max_chars_per_file:
            text = text[:max_chars_per_file]

        total_chars += len(text)
        if total_chars > max_total_chars:
            return jsonify(
                {
                    "error": (
                        "Uploaded text content is too large. "
                        f"Keep total text characters under {max_total_chars}."
                    )
                }
            ), 400

        parsed_files.append({"filename": filename, "text": text})

    if not parsed_files and not image_files:
        return jsonify({"error": "No readable text content found in uploaded files."}), 400

    model = os.getenv("OPENROUTER_MODEL", "mistralai/mistral-small-3.1-24b-instruct:free")
    url = "https://openrouter.ai/api/v1/chat/completions"

    file_blocks = "\n\n".join(
        [
            f"FILE: {item['filename']}\n---\n{item['text']}"
            for item in parsed_files
        ]
    )
    image_names = ", ".join([item["filename"] for item in image_files]) or "None"
    analysis_prompt = f"""
You are analyzing multiple student practice materials.

Goal:
Tell me exactly what is being covered across these files and images.

Output format:
1) Covered topics:
- A bullet list of concrete topics that appear in the material.
2) Skills practiced:
- A bullet list of skills/question types being practiced.
3) Frequency map:
- For each topic, estimate how often it appears (high/medium/low) with brief evidence from file names.
4) Missing or weak areas:
- Mention important adjacent topics that are absent or lightly covered.
5) 5-point summary:
- Give exactly five concise bullets a teacher can scan quickly.

Use clear headings and keep it concise but specific.

Image files:
{image_names}

File contents:
{file_blocks or "None"}
""".strip()

    user_content = [{"type": "text", "text": analysis_prompt}]
    for image in image_files:
        user_content.append({"type": "text", "text": f"Image file: {image['filename']}"})
        user_content.append({"type": "image_url", "image_url": {"url": image["data_uri"]}})

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You produce precise, structured educational analysis."},
            {"role": "user", "content": user_content},
        ],
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        body = response.json()
    except requests.HTTPError as exc:
        status_code = exc.response.status_code if exc.response is not None else None
        details = ""
        if exc.response is not None:
            try:
                details = exc.response.json()
            except ValueError:
                details = (exc.response.text or "")[:500]

        if status_code == 404:
            return (
                jsonify(
                    {
                        "error": "OpenRouter model not found or unavailable.",
                        "model": model,
                        "details": details,
                    }
                ),
                502,
            )

        return (
            jsonify(
                {
                    "error": f"OpenRouter request failed with status {status_code}.",
                    "details": details,
                }
            ),
            502,
        )
    except requests.RequestException as exc:
        return jsonify({"error": f"OpenRouter request failed: {exc}"}), 502

    text = ((body.get("choices") or [{}])[0].get("message") or {}).get("content", "")

    if not text:
        return jsonify({"error": "OpenRouter returned no text response.", "raw": body}), 502

    return jsonify(
        {
            "response": text,
            "files_analyzed": [item["filename"] for item in parsed_files] + [item["filename"] for item in image_files],
            "total_files": len(parsed_files) + len(image_files),
        }
    )


if __name__ == "__main__":
    app.run(debug=True)
