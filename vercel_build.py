from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent
FRONTEND = ROOT / "frontend"
PUBLIC = ROOT / "public"

def main():
    if PUBLIC.exists():
        shutil.rmtree(PUBLIC)
    shutil.copytree(
        FRONTEND,
        PUBLIC,
        ignore=shutil.ignore_patterns("vercel.json"),
    )

if __name__ == "__main__":
    main()
