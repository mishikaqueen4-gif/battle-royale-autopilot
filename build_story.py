
import os
import re
import asyncio
import subprocess
import requests
import edge_tts
from PIL import Image, ImageDraw, ImageFont

API_KEY = os.environ["GEMINI_API_KEY"]
MODEL = "gemini-3.8-flash"
VOICE = "hi-IN-SwaraNeural"


def make_story():
    url = (
        "https://generativelanguage.googleapis.com/v1beta/"
        + MODEL + ":generateContent?key=" + API_KEY
    )

    prompt = """
Write an exciting original fictional battle royale
adventure story in simple Hindi.

Include suspense, action, emotional moments and
a satisfying ending.

Write around 600 Hindi words.
Return only the story narration.
Do not use copyrighted characters.
"""

    response = requests.post(
        url,
        json={
            "contents": [{
                "parts": [{"text": prompt}]
            }]
        },
        timeout=120
    )

    response.raise_for_status()
    data = response.json()

    return data["candidates"][0]["content"]["parts"][0]["text"]


def get_font(size):
    paths = [
        "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    ]

    for path in paths:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)

    return ImageFont.load_default()


def make_scene(text, number):
    image = Image.new(
        "RGB", (1280, 720), (15, 20, 38)
    )

    draw = ImageDraw.Draw(image)

    draw.rectangle(
        (0, 0, 1280, 18),
        fill=(235, 65, 65)
    )

    draw.text(
        (55, 55),
        f"BATTLE ROYALE | SCENE {number}",
        font=get_font(32),
        fill=(255, 190, 80)
    )

    font = get_font(38)
    words = text.split()
    lines = []
    line = ""

    for word in words:
        test = (line + " " + word).strip()

        if draw.textbbox((0, 0), test, font=font)[2] < 1160:
            line = test
        else:
            lines.append(line)
            line = word

    if line:
        lines.append(line)

    y = 220

    for line in lines[:6]:
        draw.text(
            (60, y), line,
            font=font, fill="white"
        )
        y += 65

    image.save(f"scene_{number}.png")


async def make_voice(text):
    speech = edge_tts.Communicate(text, VOICE)
    await speech.save("voice.mp3")


def make_video():
    duration = float(
        subprocess.check_output([
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            "voice.mp3"
        ]).decode().strip()
    )

    scene_duration = duration / 8

    with open("scenes.txt", "w") as file:
        for i in range(1, 9):
            file.write(f"file 'scene_{i}.png'\n")
            file.write(f"duration {scene_duration:.3f}\n")

        file.write("file 'scene_8.png'\n")

    subprocess.run([
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", "scenes.txt",
        "-i", "voice.mp3",
        "-vf", "scale=1280:720,format=yuv420p",
        "-c:v", "libx264",
        "-r", "24",
        "-c:a", "aac",
        "-shortest",
        "battle_royale_video.mp4"
    ], check=True)


def main():
    print("Generating Hindi story...")

    story = make_story()

    with open("story.txt", "w", encoding="utf-8") as file:
        file.write(story)

    paragraphs = [
        p.strip()
        for p in re.split(r"\n+", story)
        if p.strip()
    ]

    if len(paragraphs) < 8:
        words = story.split()
        chunk = max(1, len(words) // 8)
        paragraphs = [
            " ".join(words[i:i + chunk])
            for i in range(0, len(words), chunk)
        ]

    print("Creating scenes...")

    for i in range(8):
        start = i * len(paragraphs) // 8
        end = (i + 1) * len(paragraphs) // 8
        scene = " ".join(paragraphs[start:end])

        make_scene(scene or story[:300], i + 1)

    print("Creating Hindi female voice...")
    asyncio.run(make_voice(story))

    print("Rendering video...")
    make_video()

    print("VIDEO READY!")


if __name__ == "__main__":
    main()
