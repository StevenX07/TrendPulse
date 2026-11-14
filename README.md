# 🎵 TrendPulse — Radar Semanal de Tendencias Musicales

**TrendPulse** es una aplicación web interactiva diseñada para descubrir, comparar y escuchar en un solo lugar las canciones que están dominando el mundo musical durante los últimos **7 días**. Reúne en una sola vista lo más reproducido, lo que está creciendo más rápido y los sonidos que se están volviendo virales en redes sociales, tanto desde computador como desde celular.

👉 **Explora la aplicación en vivo:** [https://stevenx07.github.io/TrendPulse/](https://stevenx07.github.io/TrendPulse/)

---

## ✨ ¿Qué hace la aplicación?

El consumo musical actual está repartido entre plataformas de streaming, listas radiales, búsquedas rápidas y videos cortos. En lugar de obligarte a revisar decenas de rankings por separado, **TrendPulse** concentra todo el panorama semanal en un tablero limpio, visual y fácil de recorrer:

- **Detecta qué está sonando ahora y qué viene subiendo:** distingue entre los éxitos ya consolidados, las canciones con aceleración explosiva en los últimos 7 días, los audios virales de video corto y los debuts recién llegados.
- **Unifica la información de múltiples plataformas:** cruza el desempeño de cada canción en **Spotify** (Top 200 semanal y diario, Top 50 Global y Viral 50), **YouTube** y **YouTube Music**, **TikTok**, **Instagram Reels**, **Shazam** (Top 200 y Viral 50), **Apple Music**, **Deezer**, **Billboard Hot 100** y **Radio en EE. UU.**
- **Permite escuchar sin salir del tablero:** integra un reproductor flotante para oír avances de 30 segundos al instante (con respaldo de video cuando aplica) mientras sigues explorando la lista.
- **Conserva historial semana a semana:** te permite viajar entre cortes semanales guardados para revisar cómo evolucionaron los lanzamientos de semanas anteriores.
- **Experiencia cómoda en celular y computador:** ofrece tarjetas compactas, carrusel deslizable de destacados en móvil, barra de categorías fija al hacer scroll, filtros rápidos y ficha detallada para cada canción.

---

## ⚙️ ¿Cómo funciona y cómo organiza la información?

Cada canción pasa por un proceso automático pensado para ofrecer orden y contexto real sin ruido visual:

1. **Recolección coordinada desde 14 fuentes:** cada corte semanal combina **9 tableros musicales abiertos** (streaming, radio, videos y rankings globales) con **5 fuentes especializadas de pago** enfocadas en detección temprana de viralidad social (TikTok e Instagram Reels), búsquedas globales en Shazam y datos ampliados de Spotify.
2. **Cruce y unificación inteligente:** si una misma canción aparece al mismo tiempo en Spotify, YouTube, TikTok, Shazam y Billboard, TrendPulse reconoce que se trata del mismo tema, evita duplicados y agrupa todas sus posiciones, cifras de crecimiento, carátula, género y enlace de escucha en una sola tarjeta.
3. **Cálculo del puntaje *Pulso 7D* (0 a 100):** la aplicación evalúa de manera equilibrada el volumen de reproducciones semanales, la velocidad de crecimiento respecto a la semana anterior, el impulso viral en redes de video corto y la presencia simultánea en varias plataformas.
4. **Respaldo ante fallos:** si en algún corte semanal una fuente externa presenta interrupciones temporales, la aplicación no se detiene ni se rompe; completa la actualización con todas las fuentes disponibles y deja indicado el estado real dentro de la pestaña **Fuentes**.

---

## 🧭 ¿Cómo se usa? (Recorrido por la pantalla)

Al abrir **TrendPulse**, encontrarás cinco zonas claras para navegar la música de la semana:

- **Resumen destacado (Tarjetas superiores):** muestra de un vistazo la canción **#1 más streameada**, el **crecimiento explosivo** de la semana, el sonido líder en **TikTok & Reels** y el balance total de canciones analizadas (incluyendo estrenos y pistas con preview). En celular puedes deslizar estas tarjetas horizontalmente.
- **Barra de categorías fija (siempre a mano al bajar):**
  - **Más Streameadas (7D):** las canciones líderes por impacto global y volumen acumulado de los últimos 7 días.
  - **Crecimiento Rápido:** temas que están dando los mayores saltos en reproducciones, posiciones o viralidad.
  - **TikTok & Reels:** canciones y sonidos que impulsan los videos cortos con mayor crecimiento reciente.
  - **Recién Llegadas:** estrenos y debuts nuevos que acaban de entrar al radar semanal.
  - **Radar por Plataforma:** te deja elegir una plataforma concreta (`Spotify 7D`, `Spotify Top 50`, `Spotify Viral 50`, `YouTube 7D`, `Instagram Reels`, `Shazam Global/Viral`, `Apple Music` o `Billboard Hot 100`) para ver su ranking específico.
  - **Fuentes:** explica con transparencia de dónde sale cada dato, qué mide cada tablero y el estado real en que se ejecutó en la semana seleccionada.
- **Buscador y filtros rápidos:** busca al instante por canción, artista o género, o activa **Con preview** y **3+ plataformas** para quedarte solo con éxitos multi-plataforma listos para escuchar.
- **Ficha completa de cada canción:** al tocar cualquier tarjeta se abre una ventana con su posición detallada plataforma por plataforma, variaciones porcentuales, audios/videos de muestra en TikTok o Reels y accesos directos para abrirla en Spotify o YouTube.
- **Reproductor flotante:** al pulsar el botón de reproducción en cualquier canción aparece una barra inferior con portada, barra de progreso y botones de canción anterior o siguiente dentro de tu filtro actual.

---

## 🕒 ¿Cada cuánto se actualiza?

- **Frecuencia semanal automática:** TrendPulse se actualiza **todos los miércoles a las 00:00 (hora Colombia / UTC-5)**.
- **Modo solo lectura para visitantes:** cuando entras a la página web ves la fotografía más reciente ya procesada, lo que garantiza carga rápida, estabilidad y consulta directa de semanas anteriores desde el selector de fecha en la parte superior.
