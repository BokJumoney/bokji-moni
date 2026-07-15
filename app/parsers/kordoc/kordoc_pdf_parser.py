import subprocess
from pathlib import Path


def parse_pdf(pdf_path: str) -> str:

    output_dir = Path("output")
    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    output_path = output_dir / "wolse.md"


    result = subprocess.run(
        [
            "npx",
            "kordoc",
            pdf_path,
            "-o",
            str(output_path)
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        shell=True
    )


    if result.returncode != 0:
        raise RuntimeError(
            result.stderr
        )


    return output_path.read_text(
        encoding="utf-8"
    )