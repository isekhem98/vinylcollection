# DuckDuckVinyl

DuckDuckVinyl is a lightweight Flask-based vinyl collection manager with Discogs lookup, price refresh, gallery view, and direct YouTube/Spotify search.

## Quick start

1. Create and activate a virtual environment

   ```bash
   python -m venv .venv
   .venv\Scripts\Activate.ps1  # PowerShell on Windows
   source .venv/bin/activate     # macOS / Linux
   ```

2. Install dependencies

   ```bash
   pip install -r requirements.txt
   ```

3. Run the app

   ```bash
   python run.py
   ```

4. Open your browser at `http://127.0.0.1:5000`

## Docker

Build the image:

```bash
docker build -t duckduckvinyl .
```

Run the container:

```bash
docker run --rm -p 5000:5000 duckduckvinyl
```

## GitHub Actions

A workflow is included at `.github/workflows/python-app.yml` to install dependencies and compile Python source files on push and pull request.

## Deployment

This repo includes a `Dockerfile` and `Procfile` for container-based hosting or Heroku-style deployment.
