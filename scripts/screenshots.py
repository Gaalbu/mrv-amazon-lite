"""Automated dashboard screenshots for Diagnóstico Territorial Preliminar.

Usage:
    .venv/bin/python scripts/screenshots.py [--out DIR] [--port 8501]

Requires: playwright + playwright-chromium installed. The script starts its own
Streamlit server in a subprocess, waits for it, drives the sidebar through the
three demo areas, and saves a full-page PNG for each use case.

Use cases documented in CHECKLIST.md:
    1. Juruti — UMF V Mamuru-Arapiuns   (contexto territorial)
    2. Área urbana (pré-diagnóstico)    (contexto territorial)
    3. Área degradada (pré-diagnóstico) (limitações visíveis)
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
        "file": "01_juruti_contexto.png",
        "expect": "Área selecionada",
    },
    {
        "label": "Área urbana (pré-diagnóstico)",
        "filter": "urbana",
        "file": "02_area_urbana_contexto.png",
        "expect": "Diagnóstico territorial",
    },
    {
        "label": "Área degradada (pré-diagnóstico)",
        "filter": "degradada",
        "file": "03_area_degradada_contexto.png",
        "expect": "Limitações",
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


def wait_for_idle(page, timeout: float = 180.0, stable_seconds: float = 3.0) -> None:
    """Wait until Streamlit finishes (re)running the script.

    The status widget shows "Running" (and the header shows a "Stop" button)
    while the server-side script executes, including the PRODES/ICMBio network
    calls. The widget can detach briefly during DOM reshuffles, so return only
    after the running indicators stay absent for `stable_seconds` in a row.
    This guarantees settled content instead of a faded mid-transition page.
    """
    running = page.locator('[data-testid="stStatusWidget"]').get_by_text("Running")
    stop_button = page.get_by_role("button", name="Stop")
    deadline = time.time() + timeout
    stable_since: float | None = None
    while time.time() < deadline:
        busy = (running.count() > 0 and running.first.is_visible()) or (
            stop_button.count() > 0 and stop_button.first.is_visible()
        )
        if busy:
            stable_since = None
        elif stable_since is None:
            stable_since = time.time()
        elif time.time() - stable_since >= stable_seconds:
            return
        time.sleep(0.5)
    raise TimeoutError("dashboard não ficou idle a tempo")


def wait_for_marker(page, marker: str, timeout: float = 120.0) -> None:
    """Wait until a heading containing the marker is visible in the body."""
    matchers = [
        page.get_by_role("heading", name=marker, exact=True),
        page.get_by_role("heading", name=marker, exact=False),
    ]
    deadline = time.time() + timeout
    while time.time() < deadline:
        for locator in matchers:
            if locator.count() > 0 and locator.first.is_visible():
                return
        time.sleep(0.5)
    raise TimeoutError(f"marcador '{marker}' não apareceu no corpo da página")


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
            wait_for_idle(page)

            for case in USE_CASES:
                select_area(page, case["filter"], case["label"])
                wait_for_idle(page)
                wait_for_marker(page, case["expect"])
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
