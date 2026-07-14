import subprocess
from pathlib import Path

# HWPX 원본 파싱
def parse_hwpx(hwpx_path: str) -> str:

    output_path = Path("output/output3.md")

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    result = subprocess.run(
        [
            "npx",
            "kordoc",
            hwpx_path,
            "-o",
            str(output_path)
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        shell=True   
    )

    if result.returncode != 0:
        raise RuntimeError(result.stderr)

    return output_path.read_text(
        encoding="utf-8"
    )