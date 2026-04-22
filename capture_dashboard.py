#!/usr/bin/env python3
"""Capture Grafana fraud-live-ops dashboard screenshots and create a GIF."""

import time
import os
from pathlib import Path
from playwright.sync_api import sync_playwright
from PIL import Image

CHROMIUM = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
GRAFANA_URL = "http://localhost:3000"
DASHBOARD_PATH = "/d/fraud-live-ops/fraud-detection-e28094-live-operations"
USERNAME = "admin"
PASSWORD = "admin"
SCREENSHOT_DIR = Path("/home/user/rp-rw-fraud-monitor/screenshots")
GIF_OUTPUT = Path("/home/user/rp-rw-fraud-monitor/fraud_live_ops.gif")
DURATION_SECONDS = 180
INTERVAL_SECONDS = 10
VIEWPORT = {"width": 1600, "height": 900}


def capture_screenshots():
    SCREENSHOT_DIR.mkdir(exist_ok=True)
    screenshots = []
    start = time.time()
    shot_num = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=CHROMIUM,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage", "--headless"],
        )
        context = browser.new_context(viewport=VIEWPORT)
        page = context.new_page()

        # Log in via the login form
        print("Logging into Grafana...")
        page.goto(f"{GRAFANA_URL}/login", wait_until="networkidle", timeout=30000)
        page.locator('input[name="user"]').fill(USERNAME)
        page.locator('input[name="password"]').fill(PASSWORD)
        page.locator('button[type="submit"]').click()
        page.wait_for_load_state("networkidle")

        # Navigate to dashboard with kiosk mode and 10s refresh
        url = f"{GRAFANA_URL}{DASHBOARD_PATH}?orgId=1&refresh=10s&kiosk"
        print(f"Navigating to: {url}")
        page.goto(url, wait_until="networkidle", timeout=30000)
        # Wait for panels to load
        time.sleep(8)

        print(f"Starting capture: {DURATION_SECONDS}s, every {INTERVAL_SECONDS}s")
        while time.time() - start < DURATION_SECONDS:
            shot_num += 1
            elapsed = int(time.time() - start)
            path = SCREENSHOT_DIR / f"shot_{shot_num:03d}_{elapsed:03d}s.png"
            page.screenshot(path=str(path), full_page=False)
            screenshots.append(str(path))
            print(f"  [{elapsed}s] Screenshot {shot_num}: {path.name}")
            # Sleep until the next interval boundary
            next_shot_time = start + shot_num * INTERVAL_SECONDS
            sleep_time = next_shot_time - time.time()
            if sleep_time > 0:
                time.sleep(sleep_time)

        browser.close()

    print(f"\nCaptured {len(screenshots)} screenshots.")
    return screenshots


def make_gif(screenshots):
    print(f"\nCreating GIF from {len(screenshots)} frames...")
    frames = []
    for path in screenshots:
        img = Image.open(path)
        # Resize to 1280x720 for reasonable GIF size
        img = img.resize((1280, 720), Image.LANCZOS)
        frames.append(img.convert("P", palette=Image.ADAPTIVE, colors=256))

    if not frames:
        print("No frames to create GIF!")
        return

    frames[0].save(
        str(GIF_OUTPUT),
        save_all=True,
        append_images=frames[1:],
        optimize=True,
        duration=800,   # 800ms per frame
        loop=0,
    )
    size_mb = GIF_OUTPUT.stat().st_size / (1024 * 1024)
    print(f"GIF saved: {GIF_OUTPUT} ({size_mb:.1f} MB, {len(frames)} frames)")


if __name__ == "__main__":
    screenshots = capture_screenshots()
    make_gif(screenshots)
    print("\nDone! GIF ready at:", GIF_OUTPUT)
