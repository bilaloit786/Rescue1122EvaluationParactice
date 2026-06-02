import os
from pathlib import Path


def main() -> None:
    path = Path(".env")
    replacements = {
        "DATABASE_URL": os.environ["NEON_DATABASE_URL"],
        "ALLOWED_HOSTS": "rescue1122-api.onrender.com,localhost,127.0.0.1",
        "BCRYPT_ROUNDS": "12",
    }
    lines = path.read_text().splitlines()
    out = []
    seen = set()
    for line in lines:
        if "=" in line and not line.lstrip().startswith("#"):
            key = line.split("=", 1)[0]
            if key in replacements:
                out.append(f"{key}={replacements[key]}")
                seen.add(key)
                continue
        out.append(line)

    for key, value in replacements.items():
        if key not in seen:
            out.append(f"{key}={value}")

    path.write_text("\n".join(out) + "\n")


if __name__ == "__main__":
    main()
