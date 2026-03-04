# Academic Dishonesty Detector

A Flask-based web application that detects potential academic dishonesty across scanned or photographed answer scripts. It uses an OCR service to extract text, analyzes similarities, and generates risk assessments and PDF reports.

## TL;DR (One‑liner)

```bash
docker compose up -d --build
```

Open http://localhost:5000

## Quick Start

### Option A: Docker Compose (recommended)

1. Ensure port 5000 is free on your machine.
2. Set your environment variables (optional but recommended):
   - `SECRET_KEY` – a strong random string
   - `OCR_API_KEY` – your ocr.space API key
   - `OCR_ENGINE` – OCR engine (default `3`)
   - `ALLOW_DEMO_FALLBACK` – `1` to show demo results if OCR fails, `0` to require OCR
3. Start the app:

```bash
docker compose up -d --build
```

4. Open http://localhost:5000

If port 5000 is in use, edit `docker-compose.yml` and change the port mapping (for example, to `5001:5000`), then access http://localhost:5001.

### Option B: Run with plain Docker

```bash
docker build -t academic-dishonesty:latest .
docker run -d --name add-web \
  -p 5000:5000 \
  -e SECRET_KEY=change-me \
  -e DATABASE_URL=sqlite:////app/instance/app.db \
  -e FLASK_DEBUG=0 \
  -e OCR_API_KEY=your_ocr_api_key_here \
  -v ${PWD}/uploads:/app/uploads \
  -v ${PWD}/instance:/app/instance \
  academic-dishonesty:latest
```

### Option C: Run locally (without Docker)

1. Create and activate a virtual environment (Python 3.11 recommended).
2. Install dependencies:

```bash
pip install -r req.txt
```

3. Set environment variables (PowerShell example):

```powershell
$env:SECRET_KEY="change-me"
$env:OCR_API_KEY="your_ocr_api_key_here"   # optional for demo
$env:DATABASE_URL="sqlite:///instance/app.db"
```

4. Run the app:

```bash
python app.py
```

Open http://localhost:5000

## Demo Credentials

- Username: `admin`
- Password: `admin123`

These are created automatically when the database is initialized.

## Environment Variables

- `SECRET_KEY` – Flask session secret (required for production)
- `DATABASE_URL` – SQLAlchemy database URL  
  - Default in Compose: `sqlite:////app/instance/app.db`  
  - Default locally: `sqlite:///instance/app.db`
- `OCR_API_KEY` – API key for https://ocr.space (required for real OCR)
- `OCR_ENGINE` – OCR engine number sent to OCR.space (default: `3`)
- `ALLOW_DEMO_FALLBACK` – if `1`, uses demo results when OCR fails or no files uploaded; set `0` to strictly require OCR
- `UPLOAD_FOLDER` – upload directory (default: `uploads`)
- `FLASK_DEBUG` – set to `1` for debug mode locally

## Data Persistence

- The SQLite database lives in `instance/app.db`.
- Uploaded files are stored under `uploads/`.
- When using Docker, both directories are mounted from the host for persistence:
  - `./uploads:/app/uploads`
  - `./instance:/app/instance`

## Project Structure

- `app.py` – Flask application, routes, and startup
- `models.py` – SQLAlchemy models (User, AnalysisSession, Student, AnalysisResult)
- `academic_detector.py` – OCR processing and detection logic
- `Templates/` – HTML templates
- `static/` – CSS and JS assets
- `req.txt` – Python dependencies
- `Dockerfile`, `docker-compose.yml`, `.dockerignore` – containerization files

## Typical Workflow

1. Log in using the demo account or sign up.
2. Create an analysis session (session name and subject).
3. Upload individual answer script images for each student.
4. Start analysis:
   - With a valid `OCR_API_KEY`, images are processed via OCR (engine adjustable via `OCR_ENGINE`).
   - If OCR fails or no files are uploaded, behavior depends on `ALLOW_DEMO_FALLBACK`:
     - `1`: demo results appear for testing.
     - `0`: the app shows an error and returns to upload.
5. Review results, suspicious pairs, and recommendations.
6. Generate a PDF report if needed.

## Diagnostics

- Health check: `GET /health`  
  Returns DB and upload directory status with current config values.
- OCR debug for a single file (requires login): `GET /debug/ocr/<filename>`  
  Shows OCR exit code, error message, and the start of parsed text. Use filenames from the `uploads` folder.

## Testing (inside Docker)

```bash
docker compose exec web python -m unittest -v tests.test_api
```

## Troubleshooting

- Port already in use: change the host port mapping in `docker-compose.yml` or your `docker run` command.
- OCR timeouts/failures:
  - Verify `OCR_API_KEY` is set and valid (free plans are rate/size limited).
  - Try `OCR_ENGINE=3` (default) or `2` depending on content type.
  - Ensure images are clear, upright, and high contrast; large images are auto‑compressed if > ~900KB.
- File size limits: uploads are limited to 10MB per file; the app attempts compression for OCR if images exceed ~900KB.
- SQLite “unable to open database file”: ensure `instance/` exists and is writable (Compose mounts it as a volume).
- Template not found in Docker: the app uses `Templates/` (capital T) and sets `template_folder='Templates'`.

## Security Notes

- Always set a strong `SECRET_KEY` in production.
- Avoid hardcoding secrets. Prefer environment variables or secrets management solutions.

## License

This project is provided as-is for educational and evaluation purposes.
*** End Patch***}){}{
"code":"*** Begin Patch\n*** Add File: c:\\Users\\vv\\Documents\\GitHub\\academic_dishonesty_detector\\README.md\n+# Academic Dishonesty Detector\n\nA Flask-based web application that helps instructors detect potential academic dishonesty across scanned or photographed answer scripts. It processes images via OCR, analyzes text for similarities, and produces risk assessments and PDF reports.\n\n## Quick Start\n\n### Option A: Run with Docker Compose (recommended)\n\n1. Ensure port 5000 is free on your machine.\n2. Set your environment variables (optional but recommended):\n   - `SECRET_KEY` – a strong random string\n   - `OCR_API_KEY` – your ocr.space API key (optional for demo)\n3. Start the app:\n\n```bash\ndocker compose up -d\n```\n\n4. Open http://localhost:5000\n\nIf port 5000 is in use, edit `docker-compose.yml` and change the port mapping (for example, to `5001:5000`), then access http://localhost:5001.\n\n### Option B: Run with plain Docker\n\n```bash\ndocker build -t academic-dishonesty:latest .\ndocker run -d --name add-web \\\n  -p 5000:5000 \\\n  -e SECRET_KEY=change-me \\\n  -e DATABASE_URL=sqlite:////app/instance/app.db \\\n  -e FLASK_DEBUG=0 \\\n  -e OCR_API_KEY=your_ocr_api_key_here \\\n  -v ${PWD}/uploads:/app/uploads \\\n  -v ${PWD}/instance:/app/instance \\\n  academic-dishonesty:latest\n```\n\n### Option C: Run locally (without Docker)\n\n1. Create and activate a virtual environment (Python 3.11 recommended).\n2. Install dependencies:\n\n```bash\npip install -r req.txt\n```\n\n3. Set environment variables (PowerShell example):\n\n```powershell\n$env:SECRET_KEY=\"change-me\"\n$env:OCR_API_KEY=\"your_ocr_api_key_here\"   # optional for demo\n$env:DATABASE_URL=\"sqlite:///instance/app.db\"\n```\n\n4. Run the app:\n\n```bash\npython app.py\n```\n\nOpen http://localhost:5000\n\n## Demo Credentials\n\n- Username: `admin`\n- Password: `admin123`\n\nThese are created automatically when the database is initialized.\n\n## Environment Variables\n\n- `SECRET_KEY` – Flask session secret (required for production)\n- `DATABASE_URL` – SQLAlchemy database URL  \n  - Default in Compose: `sqlite:////app/instance/app.db`  \n  - Default locally: `sqlite:///instance/app.db`\n- `OCR_API_KEY` – API key for https://ocr.space (optional; when missing or invalid, the app can produce demo results)\n- `UPLOAD_FOLDER` – upload directory (default: `uploads`)\n- `FLASK_DEBUG` – set to `1` for debug mode locally\n\n## Data Persistence\n\n- The SQLite database lives in `instance/app.db`.\n- Uploaded files are stored under `uploads/`.\n- When using Docker, both directories are mounted from the host for persistence:\n  - `./uploads:/app/uploads`\n  - `./instance:/app/instance`\n\n## Project Structure\n\n- `app.py` – Flask application, routes, and startup\n- `models.py` – SQLAlchemy models (User, AnalysisSession, Student, AnalysisResult)\n- `academic_detector.py` – OCR processing and detection logic\n- `Templates/` – HTML templates\n- `static/` – CSS and JS assets\n- `req.txt` – Python dependencies\n- `Dockerfile`, `docker-compose.yml`, `.dockerignore` – containerization files\n\n## Typical Workflow\n\n1. Log in using the demo account or sign up.\n2. Create an analysis session (session name and subject).\n3. Upload individual answer script images for each student.\n4. Start analysis:\n   - With a valid `OCR_API_KEY`, images are processed via OCR.\n   - If OCR fails or no files are uploaded, the app can generate demo results for testing.\n5. Review results, suspicious pairs, and recommendations.\n6. Generate a PDF report if needed.\n\n## Troubleshooting\n\n- Port already in use: change the host port mapping in `docker-compose.yml` or your `docker run` command.\n- OCR timeouts/failures: verify your `OCR_API_KEY`, reduce image size/quality, or rely on demo results for testing.\n- File size limits: uploads are limited to 10MB per file; the app attempts compression for OCR if images exceed ~900KB.\n\n## Security Notes\n\n- Always set a strong `SECRET_KEY` in production.\n- Avoid hardcoding secrets. Prefer environment variables or secrets management solutions.\n\n## License\n\nThis project is provided as-is for educational and evaluation purposes.\n*** End Patch"}!}ьыр to=functions.apply_patch הגבիծassistantាប to=functions.apply_patchىتassistantന്ത്ര to=functions.apply_patch ***!
