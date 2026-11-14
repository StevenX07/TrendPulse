# TrendPulse — Monitor Semanal de Tendencias Musicales

Aplicación ligera inspirada en **Google Material Design 3** (`Montserrat` + paleta luminosa) para descubrir las canciones más escuchadas en los últimos **7 días**, las de **crecimiento más rápido** y los sonidos **virales en TikTok**, con **previsualización instantánea de audio** y soporte automático para **GitHub Actions + GitHub Pages**.

## Fuentes de datos

- **Gratuitas**:
  - Spotify Global Weekly & Daily (`kworb.net`) — Streams 7D, variación semanal, saltos de posición y enlace directo.
  - YouTube Global Weekly (`kworb.net`) + YouTube Music Charts (`ytmusicapi`) — Visualizaciones 7D y videos musicales.
  - Apple Music Worldwide + iTunes Top Songs RSS (`us`, `gb`, `mx`, `es`, `br`, `de`) — Puntos globales, género y previews 30s AAC permanentes.
  - Deezer Global Chart & Search API — Previews 30s MP3, portadas HD, BPM y duración.
  - Billboard Hot 100 Weekly + Kworb Radio / Shazam Cross-Rank.
- **Inteligencia Social & Viral vía Apify (Fuentes de pago)**:
  - `trendingtiktoksongs~tiktok-trending-sounds-history` — Crecimiento 7D multi-país (`US`, `MX`, `BR`, `DE`) y videos de ejemplo.
  - `s_actors~tiktok-trending-sounds-scraper` — Sonidos musicales trending en Explore (`US`, `GB`, `MX`, `ES`), muestra de videos y audio MP3.
  - `trendingtiktoksongs~instagram-audio-history` — Audios en crecimiento rápido en Instagram Reels (`1D` y `7D`) + Reels de ejemplo.
  - `automation-lab~shazam-charts-scraper` — Shazam Global Top 200 y Shazam Global Viral 50.
  - `automation-lab~spotify-scraper` — Spotify Viral 50 Global, reproducciones acumuladas (`playCount`), fecha de lanzamiento y audio preview de respaldo.

## Arquitectura de actualización

La aplicación web pública es **exclusivamente de solo lectura**. Las actualizaciones semanales se ejecutan únicamente desde **GitHub Actions** ([`.github/workflows/weekly-trends.yml`](.github/workflows/weekly-trends.yml)) **todos los miércoles a las 00:00 (UTC-5 / `0 5 * * 3`)** utilizando `APIFY_API_TOKEN` almacenado en *GitHub Repository Secrets*, publicando automáticamente el sitio estático en **GitHub Pages**.

## Uso local de desarrollo (solo lectura web)

```powershell
.\start.ps1
```
Abrir `http://localhost:5173`. Para recolectar por consola manualmente:
```powershell
.\.venv\Scripts\python.exe -m collector.collect_trends --mode free
```
