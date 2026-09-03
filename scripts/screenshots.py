"""Automated dashboard screenshots for MRV Amazon Lite.

Usage:
    .venv/bin/python scripts/screenshots.py [--out DIR] [--port 8501]

Requires: playwright + playwright-chromium installed. The script starts its own
Streamlit server in a subprocess, waits for it, drives the sidebar through the
three demo areas, and saves a full-page PNG for each use case.

Based on the 3 use cases documented in CHECKLIST.md:
    1. Juruti — UMF V Mamuru-Arapiuns  (VCU ~12,7k + TFFF elegível + PlaNAU N/A)
    2. Área urbana (demo PlaNAU)        (prioridade alta + déficit de árvores)
    3. Área degradada (demo TFFF)       (TFFF não elegível)
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

USE_CASES = [
    {
        "label": "Juruti — UMF V Mamuru-Arapiuns",
        "filter": "Juruti",
        "file": "01_juruti_mamuru.png",
        "expect": "VCU líquido",
    },
    {
        "label": "Área urbana (demo PlaNAU)",
        "filter": "urbana",
        "file": "02_area_urbana_planau.png",
        "expect": "Prioridade:",
    },
    {
        "label": "Área degradada (demo TFFF)",
        "filter": "degradada",
        "file": "03_area_degradada_tfff.png",
        "expect": "Não elegível",
    },
]


def select_area(page, filter_text: str, label: str) -> None:
    """Select an option in the Streamlit sidebar 'Área de análise' combobox."""
    combobox = page.locator('[data-testid="stSelectbox"]').first.locator(
        'input[role="combobox"]'
    )
    combobox.click()
    page.wait_for_timeout(400)
    combobox.fill(filter_text)
    page.wait_for_timeout(600)
    options = page.locator('[role="option"]')
    for i in range(options.count()):
        if options.nth(i).inner_text().strip() == label:
            options.nth(i).click()
            page.wait_for_timeout(2000)
            return
    raise RuntimeError(
        f"Opção não encontrada para '{label}' após filtrar '{filter_text}'"
    )


def wait_for_server(url: str, timeout: float = 60.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(url, timeout=2)
            return
        except OSError:
            time.sleep(0.5)
    raise TimeoutError(f"Streamlit server não respondeu em {url}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=str(REPO_ROOT / "screenshots"))
    parser.add_argument("--port", type=int, default=8501)
    parser.add_argument("--server", default="http://localhost")
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    url = f"{args.server}:{args.port}"
    server = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            "web/app.py",
            "--server.headless=true",
            "--server.address=127.0.0.1",
            f"--server.port={args.port}",
            "--browser.gatherUsageStats=false",
        ],
        cwd=REPO_ROOT,
    )

    try:
        wait_for_server(url)
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.goto(url, wait_until="networkidle")
            page.wait_for_timeout(3000)

            for case in USE_CASES:
                select_area(page, case["filter"], case["label"])
                page.wait_for_timeout(1500)
                body_text = page.locator("body").inner_text()
                if case["expect"] not in body_text:
                    raise RuntimeError(
                        f"Screenshot '{case['file']}' não contém marcador esperado "
                        f"'{case['expect']}'"
                    )
                target = out_dir / case["file"]
                page.screenshot(path=str(target), full_page=True)
                print(f"saved {target}")

            browser.close()
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()

    print(f"done → {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
