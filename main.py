import io
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, Response
from PIL import Image

app = FastAPI(title="Favicon Generator")

HTML_CONTENT = """
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Favicon Generator - KodiniTools</title>
    <style>
        * { box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #0f172a;
            color: #f8fafc;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            margin: 0;
            padding: 1rem;
        }
        .card {
            background: #1e293b;
            padding: 2.5rem;
            border-radius: 12px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.5);
            max-width: 480px;
            width: 100%;
            text-align: center;
            border: 1px solid #334155;
        }
        h1 { margin-top: 0; font-size: 1.6rem; color: #38bdf8; }
        p { color: #94a3b8; font-size: 0.95rem; margin-bottom: 1.5rem; }
        .dropzone {
            display: block;
            border: 2px dashed #475569;
            border-radius: 8px;
            padding: 2.5rem 1rem;
            cursor: pointer;
            transition: all 0.2s ease;
            background: #0f172a;
        }
        .dropzone:hover { border-color: #38bdf8; background: #182234; }
        input[type="file"] { display: none; }
        button {
            margin-top: 1.5rem;
            width: 100%;
            background: #0284c7;
            color: white;
            border: none;
            padding: 0.85rem;
            border-radius: 6px;
            font-weight: 600;
            cursor: pointer;
            font-size: 1rem;
            transition: background 0.2s;
        }
        button:hover { background: #0369a1; }
        #status { margin-top: 1rem; font-size: 0.95rem; min-height: 1.2rem; }
    </style>
</head>
<body>
    <div class="card">
        <h1>Favicon Konverter</h1>
        <p>Erstelle aus einem Bild (PNG, JPG, WebP) ein optimiertes <code>favicon.ico</code> (16x16, 32x32, 48x48, 64x64).</p>
        
        <form id="uploadForm">
            <label class="dropzone" id="dropzone">
                <span id="label-text">Datei auswählen oder hierher ziehen</span>
                <input type="file" id="fileInput" name="file" accept="image/*" required>
            </label>
            <button type="submit" id="btn">favicon.ico generieren</button>
        </form>
        <div id="status"></div>
    </div>

    <script>
        const fileInput = document.getElementById('fileInput');
        const labelText = document.getElementById('label-text');
        const form = document.getElementById('uploadForm');
        const status = document.getElementById('status');

        fileInput.addEventListener('change', () => {
            if (fileInput.files.length > 0) {
                labelText.textContent = fileInput.files[0].name;
            }
        });

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            if (!fileInput.files.length) return;

            status.textContent = "Wird verarbeitet...";
            status.style.color = "#38bdf8";

            const formData = new FormData();
            formData.append('file', fileInput.files[0]);

            try {
                // Relativer Aufruf passend zum Subpath
                const res = await fetch('convert', { method: 'POST', body: formData });
                if (!res.ok) throw new Error('Konvertierung fehlgeschlagen');
                
                const blob = await res.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'favicon.ico';
                document.body.appendChild(a);
                a.click();
                a.remove();
                
                status.textContent = "Fertig! Download gestartet.";
                status.style.color = "#4ade80";
            } catch (err) {
                status.textContent = err.message;
                status.style.color = "#f87171";
            }
        });
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
def index():
    return HTML_CONTENT

@app.post("/convert")
async def convert(file: UploadFile = File(...)):
    try:
        data = await file.read()
        img = Image.open(io.BytesIO(data))
        
        if img.mode not in ("RGBA", "RGB"):
            img = img.convert("RGBA")
            
        out_buf = io.BytesIO()
        sizes = [(16, 16), (32, 32), (48, 48), (64, 64)]
        img.save(out_buf, format="ICO", sizes=sizes)
        out_buf.seek(0)
        
        return Response(
            content=out_buf.getvalue(),
            media_type="image/x-icon",
            headers={"Content-Disposition": "attachment; filename=favicon.ico"}
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Fehler: {str(e)}")
