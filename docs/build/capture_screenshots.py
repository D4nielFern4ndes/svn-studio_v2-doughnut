"""Capture les copies d'écran de l'application utilisées dans le guide PDF.

Usage (depuis la racine du dépôt) :
    python docs/build/capture_screenshots.py

Lance l'application Streamlit en local, charge l'exemple pédagogique et
enregistre une image par étape dans docs/build/img/. Nécessite Playwright
avec Chromium (python -m pip install playwright && python -m playwright install chromium).
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "img"
PORT = 8599
URL = f"http://localhost:{PORT}"


def wait_server(timeout: float = 60) -> None:
    end = time.time() + timeout
    while time.time() < end:
        try:
            urllib.request.urlopen(URL + "/_stcore/health", timeout=2)
            return
        except Exception:
            time.sleep(0.5)
    raise RuntimeError("Streamlit n'a pas démarré")


def settle(page, extra: float = 1.2) -> None:
    page.wait_for_load_state("networkidle")
    try:
        page.wait_for_selector('[data-testid="stStatusWidget"]', state="detached", timeout=15000)
    except Exception:
        pass
    time.sleep(extra)


def goto(page, label: str) -> None:
    """Navigue par le menu latéral pour garder la session Streamlit."""
    page.locator('[data-testid="stSidebarNav"] a', has_text=label).first.click()
    settle(page)


def trim(path: Path, margin: int = 30) -> None:
    """Retire le blanc en bas de l'image."""
    from PIL import Image, ImageOps
    im = Image.open(path).convert("RGB")
    box = ImageOps.invert(im).point(lambda v: 255 if v > 12 else 0).getbbox()
    if box:
        im.crop((0, 0, im.width, min(im.height, box[3] + margin))).save(path)


def shot(page, name: str) -> None:
    # Masquer les notifications passagères et la barre d'outils Streamlit.
    page.evaluate("""() => document.querySelectorAll(
        '[data-testid="stToast"], [data-testid="stToolbar"]').forEach(e => e.remove())""")
    # Menu latéral masqué le temps de la capture : l'image montre seulement le contenu.
    page.add_style_tag(content='[data-testid="stSidebar"]{display:none !important}')
    time.sleep(1.2)
    page.evaluate("window.scrollTo(0, 0)")
    path = OUT / f"{name}.png"
    page.locator('[data-testid="stMain"]').screenshot(path=str(path))
    trim(path)
    page.evaluate("""() => document.querySelectorAll('style').forEach(
        st => { if (st.textContent.includes('stSidebar"]{display:none')) st.remove(); })""")
    time.sleep(0.8)
    print("  ", name)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    server = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "app.py", "--server.headless=true",
         f"--server.port={PORT}", "--browser.gatherUsageStats=false", "--theme.base=light"],
        cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        wait_server()
        with sync_playwright() as pw:
            exe = os.environ.get("CHROMIUM_PATH")  # navigateur déjà installé, facultatif
            browser = pw.chromium.launch(executable_path=exe) if exe else pw.chromium.launch()
            page = browser.new_page(viewport={"width": 1200, "height": 1100}, device_scale_factor=1.5)
            page.goto(URL)
            settle(page, 2)
            page.get_by_role("button", name="Charger l'exemple").click()
            settle(page)
            # La session Streamlit est liée à l'onglet : on navigue ensuite par le menu.
            goto(page, "Accueil")
            shot(page, "accueil")
            goto(page, "Parties prenantes")
            shot(page, "parties_prenantes")
            goto(page, "Flux de valeur")
            shot(page, "flux")
            goto(page, "Carte du réseau")
            page.get_by_text("Un cycle", exact=True).click()
            settle(page, 2.5)
            shot(page, "reseau")
            goto(page, "Cycles de valeur")
            # Sélectionner le 2e cycle (case à cocher de la grille, dessinée sur un canvas).
            grid = page.locator('[data-testid="stDataFrame"]').first
            box = grid.bounding_box()
            page.mouse.click(box["x"] + 14, box["y"] + 35 * 2.5)
            settle(page, 2)
            shot(page, "cycles")
            goto(page, "Priorisation")
            shot(page, "priorisation")
            goto(page, "Importer / exporter")
            page.get_by_role("tab", name="Exporter").click()
            settle(page)
            shot(page, "exporter")
            # Comparaison : A = T0_base.json (ouvert à l'étape 1), B = T1_doughnut_global.json.
            ex = ROOT / "data" / "examples" / "doughnut"
            page.get_by_role("tab", name="Importer").click()
            settle(page)
            page.locator('[data-testid="stFileUploaderDropzoneInput"]').set_input_files(str(ex / "T0_base.json"))
            settle(page, 2)
            page.get_by_role("button", name="Ouvrir ce projet").click()
            settle(page)
            goto(page, "Comparer deux scénarios")
            page.locator('[data-testid="stFileUploaderDropzoneInput"]').set_input_files(
                str(ex / "T1_doughnut_global.json"))
            settle(page, 3)
            shot(page, "comparaison")
            browser.close()
    finally:
        server.terminate()
        server.wait(timeout=10)


if __name__ == "__main__":
    main()
