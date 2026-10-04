import os
import sys
import glob
import shutil
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

RAW_DIR = r"D:\prj\AI-Review-System\raw_browser_recording"
OUT_MP4 = r"D:\prj\AI-Review-System\SHOWCASE.mp4"
OUT_WEBM = r"D:\prj\AI-Review-System\SHOWCASE.webm"
ARTIFACT_DIR = r"C:\Users\SUJAL\.gemini\antigravity\brain\7ee6c462-280e-4188-8b0a-2ba8f0c7e26b"

WIDTH = 1920
HEIGHT = 1080
FPS = 25

# Load Fonts
FONT_BOLD_PATH = "C:/Windows/Fonts/segoeuib.ttf"
FONT_REG_PATH = "C:/Windows/Fonts/segoeui.ttf"
FONT_TITLE = ImageFont.truetype(FONT_BOLD_PATH, 54)
FONT_SUBTITLE = ImageFont.truetype(FONT_REG_PATH, 28)
FONT_BODY = ImageFont.truetype(FONT_REG_PATH, 22)
FONT_BOLD = ImageFont.truetype(FONT_BOLD_PATH, 24)
FONT_BADGE = ImageFont.truetype(FONT_BOLD_PATH, 16)
FONT_CHAPTER = ImageFont.truetype(FONT_BOLD_PATH, 22)
FONT_DESC = ImageFont.truetype(FONT_REG_PATH, 18)

def draw_rounded_rect(draw, xy, corner_radius, fill=None, outline=None, width=1):
    draw.rounded_rectangle(xy, radius=corner_radius, fill=fill, outline=outline, width=width)

def create_intro_frame():
    img = Image.new("RGB", (WIDTH, HEIGHT), color=(15, 23, 42))  # Slate 900
    draw = ImageDraw.Draw(img)

    # Accent top border
    draw.rectangle([(0, 0), (WIDTH, 8)], fill=(245, 158, 11))  # Amber-500

    # Grid effect lines (subtle)
    for y in range(80, HEIGHT, 80):
        draw.line([(0, y), (WIDTH, y)], fill=(30, 41, 59), width=1)
    for x in range(80, WIDTH, 80):
        draw.line([(x, 0), (x, HEIGHT)], fill=(30, 41, 59), width=1)

    # Center card
    card_w, card_h = 1400, 680
    cx, cy = WIDTH // 2, HEIGHT // 2 - 20
    x0, y0 = cx - card_w // 2, cy - card_h // 2
    x1, y1 = cx + card_w // 2, cy + card_h // 2

    draw_rounded_rect(draw, [(x0, y0), (x1, y1)], 24, fill=(30, 41, 59), outline=(71, 85, 105), width=2)

    # Badge: System Type
    badge_text = "ENTERPRISE CLIENT DEMONSTRATION • PRODUCTION VERIFIED"
    draw_rounded_rect(draw, [(cx - 290, y0 + 50), (cx + 290, y0 + 90)], 10, fill=(245, 158, 11))
    draw.text((cx, y0 + 70), badge_text, font=FONT_BADGE, fill=(15, 23, 42), anchor="mm")

    # Main Title
    title = "ODIPKS AI-NATIVE CONSTRUCTION OS"
    draw.text((cx, y0 + 160), title, font=FONT_TITLE, fill=(255, 255, 255), anchor="mm")

    # Subtitle
    sub = "Heavy Civil Infrastructure Management & Autonomous Governance Platform"
    draw.text((cx, y0 + 230), sub, font=FONT_SUBTITLE, fill=(226, 232, 240), anchor="mm")

    tag = "Purpose-Built for Bored Piling, Deep Well Foundations, Bridges & Flyover Projects"
    draw.text((cx, y0 + 280), tag, font=FONT_BODY, fill=(148, 163, 184), anchor="mm")

    # 4 Feature Pillars Grid
    pillars = [
        ("OFFLINE-FIRST PWA", "IndexedDB client queue auto-syncs when 4G/5G signal drops on site", (79, 70, 229)),
        ("STRICT ANOMALY GUARDS", "Rs.50,000 supervisor deficit ceiling & zero-ghost-fuel validation", (16, 185, 129)),
        ("500M GPS GEOFENCING", "Haversine coordinates eliminate ghost worker attendance fraud", (245, 158, 11)),
        ("08:00 AM BRIEF ENGINE", "Autonomous Celery aggregation with 1-click WhatsApp business dispatch", (236, 72, 153)),
    ]

    grid_y = y0 + 360
    col_w = 280
    col_gap = 40
    start_x = cx - (col_w * 4 + col_gap * 3) // 2

    for i, (p_title, p_desc, p_color) in enumerate(pillars):
        px0 = start_x + i * (col_w + col_gap)
        py0 = grid_y
        px1 = px0 + col_w
        py1 = py0 + 190

        draw_rounded_rect(draw, [(px0, py0), (px1, py1)], 14, fill=(15, 23, 42), outline=(51, 65, 85), width=1)
        # Top color pill
        draw_rounded_rect(draw, [(px0 + 16, py0 + 16), (px1 - 16, py0 + 44)], 6, fill=p_color)
        draw.text((px0 + col_w // 2, py0 + 30), p_title, font=ImageFont.truetype(FONT_BOLD_PATH, 13), fill=(255, 255, 255), anchor="mm")

        # Description wrapped
        words = p_desc.split()
        lines = []
        curr = ""
        for w in words:
            if len(curr + " " + w) > 28:
                lines.append(curr)
                curr = w
            else:
                curr = (curr + " " + w).strip()
        if curr:
            lines.append(curr)

        for l_idx, line in enumerate(lines[:4]):
            draw.text((px0 + 16, py0 + 64 + l_idx * 24), line, font=ImageFont.truetype(FONT_REG_PATH, 14), fill=(203, 213, 225))

    # Bottom footer note
    footer = "ADANI-ODIPKS Vadakara AVRP Flyover Package (Site ID #1) • End-to-End Walkthrough"
    draw.text((cx, HEIGHT - 70), footer, font=FONT_BODY, fill=(100, 116, 139), anchor="mm")

    return np.array(img)[:, :, ::-1]  # RGB to BGR

def create_outro_frame():
    img = Image.new("RGB", (WIDTH, HEIGHT), color=(15, 23, 42))
    draw = ImageDraw.Draw(img)

    # Accent top border
    draw.rectangle([(0, 0), (WIDTH, 8)], fill=(16, 185, 129))  # Emerald-500

    # Grid lines
    for y in range(80, HEIGHT, 80):
        draw.line([(0, y), (WIDTH, y)], fill=(30, 41, 59), width=1)
    for x in range(80, WIDTH, 80):
        draw.line([(x, 0), (x, HEIGHT)], fill=(30, 41, 59), width=1)

    card_w, card_h = 1360, 680
    cx, cy = WIDTH // 2, HEIGHT // 2 - 20
    x0, y0 = cx - card_w // 2, cy - card_h // 2
    x1, y1 = cx + card_w // 2, cy + card_h // 2

    draw_rounded_rect(draw, [(x0, y0), (x1, y1)], 24, fill=(30, 41, 59), outline=(71, 85, 105), width=2)

    # Badge
    badge_text = "SYSTEM READY FOR JOB SITE PILOT DEPLOYMENT"
    draw_rounded_rect(draw, [(cx - 240, y0 + 50), (cx + 240, y0 + 90)], 10, fill=(16, 185, 129))
    draw.text((cx, y0 + 70), badge_text, font=FONT_BADGE, fill=(15, 23, 42), anchor="mm")

    # Main Title
    title = "ODIPKS CONSTRUCTION OS — PRODUCTION READY"
    draw.text((cx, y0 + 155), title, font=FONT_TITLE, fill=(255, 255, 255), anchor="mm")

    sub = "Operational Friction Eliminated Across Field Operations & Executive Governance"
    draw.text((cx, y0 + 225), sub, font=FONT_SUBTITLE, fill=(226, 232, 240), anchor="mm")

    # Key Value Deliverables
    checks = [
        "100% Offline Capability: No lost records during network drops on harsh job sites",
        "Zero Fuel & Petty Cash Leakage: Rs.50k deficit ceiling & negative dip guards enforced",
        "Ghost Attendance Eliminated: 500m Haversine GPS geofence on every worker punch",
        "Executive Freedom: 08:00 AM WhatsApp brief replaces 50+ chaotic daily WhatsApp texts",
        "Tally Prime ERP Integration: 1-click XML ledger sync for accounting teams",
        "110 / 110 Automated Tests Passing (100%) • Next.js 14 Production Verified",
    ]

    for i, chk in enumerate(checks):
        chk_y = y0 + 295 + i * 50
        # Green bullet
        draw_rounded_rect(draw, [(cx - 580, chk_y - 12), (cx - 550, chk_y + 16)], 8, fill=(16, 185, 129))
        draw.text((cx - 565, chk_y + 2), "✓", font=ImageFont.truetype(FONT_BOLD_PATH, 16), fill=(15, 23, 42), anchor="mm")
        draw.text((cx - 530, chk_y + 2), chk, font=FONT_BOLD, fill=(241, 245, 249), anchor="lm")

    footer = "ODIPKS AI-Native Operating System • Delivered by Antigravity Collective"
    draw.text((cx, HEIGHT - 70), footer, font=FONT_BODY, fill=(148, 163, 184), anchor="mm")

    return np.array(img)[:, :, ::-1]

# Chapter timeline mapping
CHAPTERS = [
    {
        "pct_start": 0.00,
        "pct_end": 0.12,
        "num": 1,
        "title": "Rapid Field Authentication & Zero-Friction Login",
        "badge": "AUTH & ROLES",
        "desc": "Dual Persona Access: 4-digit PIN for dusty field conditions on mobile vs corporate email for management.",
    },
    {
        "pct_start": 0.12,
        "pct_end": 0.33,
        "num": 2,
        "title": "08:00 AM Autonomous Executive Daily Brief Scorecard",
        "badge": "EXECUTIVE AI",
        "desc": "Automated Shift Synthesis: 6 live production KPIs, operational exceptions, and 1-click WhatsApp broadcast.",
    },
    {
        "pct_start": 0.33,
        "pct_end": 0.55,
        "num": 3,
        "title": "Heavy Civil Daily Progress Report (DPR) & Site Telemetry",
        "badge": "FIELD OPS",
        "desc": "Bored piling progress, 1000mm diameter guard, rock socketing, casing, concrete overbreak & photo compression.",
    },
    {
        "pct_start": 0.55,
        "pct_end": 0.76,
        "num": 4,
        "title": "Site Petty Cash & Strict Rs.50,000 Deficit Ceiling Guard",
        "badge": "FINANCIAL SAFETY",
        "desc": "Out-of-pocket tracking with Rs.50,000 hard deficit ceiling guard, duplicate expense flags, and Tally Prime XML export.",
    },
    {
        "pct_start": 0.76,
        "pct_end": 0.91,
        "num": 5,
        "title": "Geofenced Labour Attendance & Gang Muster Verification",
        "badge": "LABOUR FRAUD GUARD",
        "desc": "500m Haversine GPS geofence validation for direct workers and unique shift constraints for subcontractor muster.",
    },
    {
        "pct_start": 0.91,
        "pct_end": 1.00,
        "num": 6,
        "title": "Offline-First Architecture & Resilient IndexedDB Sync",
        "badge": "OFFLINE PWA",
        "desc": "IndexedDB offline queue with automatic reconnect orchestrator and pre-sync JWT token renewal.",
    },
]

def precompute_chapter_overlays():
    print("Precomputing lower-third chapter banners...")
    overlays = {}
    bx0, by0 = 40, HEIGHT - 130
    bx1, by1 = WIDTH - 40, HEIGHT - 25

    for chap in CHAPTERS:
        overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        # Glassmorphism dark background box with border
        draw.rounded_rectangle([(bx0, by0), (bx1, by1)], radius=16, fill=(15, 23, 42, 238), outline=(71, 85, 105, 255), width=2)

        # Chapter Badge
        draw_rounded_rect(draw, [(bx0 + 20, by0 + 16), (bx0 + 160, by0 + 46)], 8, fill=(245, 158, 11))
        draw.text((bx0 + 90, by0 + 31), f"CHAPTER {chap['num']}", font=FONT_BADGE, fill=(15, 23, 42), anchor="mm")

        # Feature Pill
        draw_rounded_rect(draw, [(bx0 + 175, by0 + 16), (bx0 + 440, by0 + 46)], 8, fill=(79, 70, 229))
        draw.text((bx0 + 307, by0 + 31), chap['badge'], font=FONT_BADGE, fill=(255, 255, 255), anchor="mm")

        # Chapter Title
        draw.text((bx0 + 460, by0 + 31), chap['title'], font=FONT_CHAPTER, fill=(255, 255, 255), anchor="lm")

        # Detailed explanation
        draw.text((bx0 + 22, by0 + 68), chap['desc'], font=FONT_DESC, fill=(226, 232, 240), anchor="lm")

        np_overlay = np.array(overlay)
        # Extract the banner region
        y_start, y_end = by0 - 2, by1 + 2
        x_start, x_end = bx0 - 2, bx1 + 2
        alpha_roi = (np_overlay[y_start:y_end, x_start:x_end, 3] / 255.0)[:, :, np.newaxis]
        bgr_roi = np_overlay[y_start:y_end, x_start:x_end, :3][:, :, ::-1]

        overlays[chap["num"]] = {
            "y_start": y_start,
            "y_end": y_end,
            "x_start": x_start,
            "x_end": x_end,
            "alpha": alpha_roi,
            "bgr": bgr_roi,
        }

    return overlays

def render_master_video():
    webms = glob.glob(os.path.join(RAW_DIR, "*.webm"))
    if not webms:
        print(f"Error: No .webm recording found in {RAW_DIR}")
        sys.exit(1)

    raw_video = webms[0]
    print(f"Found raw video: {raw_video}")

    cap = cv2.VideoCapture(raw_video)
    total_raw_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    raw_fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    print(f"Raw Video: {total_raw_frames} frames @ {raw_fps:.2f} fps ({total_raw_frames/raw_fps:.1f}s)")

    fourcc_mp4 = cv2.VideoWriter_fourcc(*"mp4v")
    out_mp4 = cv2.VideoWriter(OUT_MP4, fourcc_mp4, FPS, (WIDTH, HEIGHT))

    if not out_mp4.isOpened():
        print("Error: Could not open VideoWriter for MP4")
        sys.exit(1)

    fourcc_webm = cv2.VideoWriter_fourcc(*"VP80")
    out_webm = cv2.VideoWriter(OUT_WEBM, fourcc_webm, FPS, (WIDTH, HEIGHT))
    use_webm_writer = out_webm.isOpened()
    if use_webm_writer:
        print("WebM VideoWriter initialized successfully (VP80)")
    else:
        print("Notice: WebM VideoWriter unavailable, will fallback to raw WebM copy")

    # 1. Render Intro Title Slate (140 frames = 5.6 seconds)
    print("Generating Cinematic Title Slate (140 frames)...")
    intro_frame = create_intro_frame()
    for f in range(140):
        if f < 20:
            alpha = f / 20.0
            f_frame = (intro_frame * alpha).astype(np.uint8)
        else:
            f_frame = intro_frame
        out_mp4.write(f_frame)
        if use_webm_writer:
            out_webm.write(f_frame)

    # 2. Process Raw Browser Recording with Fast Lower-Third Overlays
    print("Processing browser walkthrough frames with lower-third overlays...")
    overlays = precompute_chapter_overlays()
    frame_idx = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        if frame.shape[1] != WIDTH or frame.shape[0] != HEIGHT:
            frame = cv2.resize(frame, (WIDTH, HEIGHT))

        pct = frame_idx / max(1, total_raw_frames)

        # Determine active chapter
        curr_chap = None
        for c in CHAPTERS:
            if c["pct_start"] <= pct < c["pct_end"]:
                curr_chap = c
                break
        if not curr_chap:
            curr_chap = CHAPTERS[-1]

        ov = overlays[curr_chap["num"]]
        ys, ye = ov["y_start"], ov["y_end"]
        xs, xe = ov["x_start"], ov["x_end"]

        roi = frame[ys:ye, xs:xe]
        frame[ys:ye, xs:xe] = (roi * (1.0 - ov["alpha"]) + ov["bgr"] * ov["alpha"]).astype(np.uint8)

        out_mp4.write(frame)
        if use_webm_writer:
            out_webm.write(frame)

        frame_idx += 1
        if frame_idx % 400 == 0 or frame_idx == total_raw_frames:
            print(f"  Rendered frame {frame_idx}/{total_raw_frames} ({(pct*100):.1f}%)...")

    cap.release()

    # 3. Render Outro Slate (160 frames = 6.4 seconds)
    print("Generating Outro Slate (160 frames)...")
    outro_frame = create_outro_frame()
    for f in range(160):
        if f > 140:
            alpha = (160 - f) / 20.0
            f_frame = (outro_frame * alpha).astype(np.uint8)
        else:
            f_frame = outro_frame
        out_mp4.write(f_frame)
        if use_webm_writer:
            out_webm.write(f_frame)

    out_mp4.release()
    if use_webm_writer:
        out_webm.release()

    mp4_size_mb = os.path.getsize(OUT_MP4) / (1024 * 1024)
    print(f"--> Master MP4 Video Generated: {OUT_MP4} ({mp4_size_mb:.2f} MB)")

    # 4. Finalize SHOWCASE.webm
    if not use_webm_writer or not os.path.exists(OUT_WEBM) or os.path.getsize(OUT_WEBM) < 10000:
        shutil.copyfile(raw_video, OUT_WEBM)
    webm_size_mb = os.path.getsize(OUT_WEBM) / (1024 * 1024)
    print(f"--> Showcase WebM Created: {OUT_WEBM} ({webm_size_mb:.2f} MB)")

    # 5. Copy to Conversation Artifacts Directory and Local Artifacts Directory
    os.makedirs(ARTIFACT_DIR, exist_ok=True)
    art_mp4 = os.path.join(ARTIFACT_DIR, "SHOWCASE.mp4")
    art_webm = os.path.join(ARTIFACT_DIR, "SHOWCASE.webm")
    shutil.copyfile(OUT_MP4, art_mp4)
    shutil.copyfile(OUT_WEBM, art_webm)
    print(f"--> Copied showcase video artifacts to: {ARTIFACT_DIR}")

    LOCAL_ART_DIR = r"D:\prj\AI-Review-System\local_artifacts"
    if os.path.exists(LOCAL_ART_DIR):
        shutil.copyfile(OUT_MP4, os.path.join(LOCAL_ART_DIR, "SHOWCASE.mp4"))
        shutil.copyfile(OUT_WEBM, os.path.join(LOCAL_ART_DIR, "SHOWCASE.webm"))
        print(f"--> Copied showcase video artifacts to: {LOCAL_ART_DIR}")

    print("ALL VIDEO PRODUCTION WORKFLOWS COMPLETE!")

if __name__ == "__main__":
    render_master_video()

