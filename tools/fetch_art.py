# Download Canva page exports and save them as WebP artwork for the site.
# Usage: python3 fetch_art.py <name=url> ...   (saves art/<name>.webp)
import pathlib, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
out = ROOT / "art"
out.mkdir(exist_ok=True)
with tempfile.TemporaryDirectory() as tmp:
    for arg in sys.argv[1:]:
        name, url = arg.split("=", 1)
        png = pathlib.Path(tmp) / f"{name}.png"
        subprocess.run(["curl", "-sSf", "-m", "120", "-o", str(png), url], check=True)
        subprocess.run(["cwebp", "-quiet", "-q", "82", "-resize", "1200", "0", str(png), "-o", str(out / f"{name}.webp")], check=True)
        print(name, (out / f"{name}.webp").stat().st_size // 1024, "KB")
