# Project Explanation

## Overview

This application assists educators in detecting potential academic dishonesty by analyzing text extracted from student answer scripts (images or scans). It provides an end-to-end workflow: account management, session creation, per-student uploads, automated analysis, results visualization, and PDF report generation.

## Key Features

- User authentication and session management
- OCR-based text extraction from images (ocr.space API)
- Multiple detection strategies:
  - Identical wrong answers
  - Rare answer patterns
  - Stylometric analysis (writing style metrics)
  - TF‑IDF cosine text similarity with suspicious line extraction
- Risk scoring and recommendations
- PDF report export (ReportLab)

## Architecture

- Web Framework: Flask
- ORM: SQLAlchemy
- Auth: Flask-Login
- Database: SQLite (default); configurable via `DATABASE_URL`
- OCR: External ocr.space API
- Analysis: scikit-learn (TF‑IDF and cosine similarity), PIL for image handling
- Reporting: ReportLab

### Main Components

- `app.py`  
  - Initializes Flask app, config, database, and login manager  
  - Defines routes for login/signup, dashboard/history, upload, processing, analysis, results, PDF reports, settings, and session deletion  
  - Boots the development server (host `0.0.0.0`, port `5000`)  

- `models.py`  
  - `User`: basic user profile with hashed password fields stored in DB  
  - `AnalysisSession`: created per analysis run; associated with a user  
  - `Student`: per-student metadata and stored path to uploaded file  
  - `AnalysisResult`: pairwise similarity results with metadata and recommendations  

- `academic_detector.py`  
  - Handles image size checks and optional compression before OCR  
  - Uses ocr.space API to extract text; robust error handling and retries  
  - Cleans and normalizes text, extracts answers using multiple regex patterns  
  - Computes stylometric features (sentence length, vocabulary richness, punctuation density, etc.)  
  - Builds TF‑IDF vectors to compute cross-script cosine similarity and extracts suspicious line pairs  
  - Aggregates multiple signals into per-script risk scores and overall assessment  

## Data Model (Summary)

- User (1) — (N) AnalysisSession  
- AnalysisSession (1) — (N) Student  
- AnalysisSession (1) — (N) AnalysisResult  
- AnalysisResult references detected pairs by `script1_id` and `script2_id` (student IDs) with `similarity_score`, `detection_method`, `suspicious_lines` (JSON), and `recommendation`.

## Detection Pipeline

1. Upload images for students in a session
2. OCR each image (with optional compression to satisfy API limits)
3. Normalize text and extract candidate answers
4. Compute:  
   - Identical wrong answers between scripts  
   - Rare answer patterns (answers occurring in <10% of scripts)  
   - Stylometric anomalies per script  
   - TF‑IDF text similarity between all pairs and extract suspicious line pairs
5. Aggregate signals into risk scores and classify risk levels (VERY LOW → VERY HIGH)
6. Present results with recommendations; allow PDF export

## Configuration and Runtime

- `SECRET_KEY` – session security
- `DATABASE_URL` – database location; defaults to SQLite in `instance/app.db`
- `OCR_API_KEY` – ocr.space API key; when absent or failing, the app supports demo results
- `UPLOAD_FOLDER` – upload path (default `uploads`)
- `FLASK_DEBUG` – enable debug locally

The app ensures `uploads/` and `instance/` directories exist on startup.

## Security and Privacy

- Secrets and keys are passed via environment variables
- Use strong `SECRET_KEY` and avoid committing secrets
- Consider HTTPS and a production WSGI server for deployment

## Limitations and Future Improvements

- OCR depends on an external API; network and rate limits apply
- Text similarity and stylometric heuristics may produce false positives/negatives
- Future enhancements could include:
  - Native PDF/image preprocessing and local OCR engine (e.g., Tesseract)
  - Configurable thresholds per detection method
  - Postgres support and migrations
  - Background task queue for long-running analyses

## File References

- Application entry and routes: `app.py`
- Models and schema: `models.py`
- Detection logic and OCR: `academic_detector.py`
- Templates: `Templates/`
- Static assets: `static/`
- Dockerization: `Dockerfile`, `docker-compose.yml`, `.dockerignore`
*** End Patch
