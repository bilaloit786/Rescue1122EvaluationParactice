import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(BACKEND_DIR))

from scripts.seed_document_question_bank import generate_question_bank, write_json_files  # noqa: E402


def main() -> None:
    rows = generate_question_bank()
    write_json_files(rows)
    print("Generation complete.")


if __name__ == "__main__":
    main()
