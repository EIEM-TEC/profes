from __future__ import annotations

import argparse
import csv
import unicodedata
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent


def normalize_text(value: object) -> str:
    text = "" if value is None else str(value)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return " ".join(text.casefold().split())


def split_codes(value: object) -> list[str]:
    text = "" if value is None else str(value)
    return [part.strip() for part in text.split(";") if part.strip()]


def target_files(root_dir: Path) -> list[Path]:
    return sorted(
        path
        for path in root_dir.glob("*.csv")
        if path.name[:2].isdigit()
        and 0 <= int(path.name[:2]) <= 10
        and path.name[2:3] == "_"
    )


def read_csv_rows(path: Path) -> list[list[str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.reader(file))


def write_csv_rows(path: Path, rows: list[list[str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file, lineterminator="\n")
        writer.writerows(rows)


def build_name_lookup(root_dir: Path) -> dict[str, str]:
    datos_path = root_dir / "00_datos.csv"
    if not datos_path.exists():
        return {}

    rows = read_csv_rows(datos_path)
    if not rows:
        return {}

    header = [cell.strip().removeprefix("\ufeff") for cell in rows[0]]
    try:
        code_index = header.index("codigo")
        name_index = header.index("nombre")
    except ValueError:
        return {}

    lookup = {}
    for row in rows[1:]:
        if not any(cell.strip() for cell in row):
            continue
        code = row[code_index].strip() if code_index < len(row) else ""
        name = row[name_index].strip() if name_index < len(row) else ""
        if code and name:
            lookup[code] = name
    return lookup


def padded_row(row: list[str], width: int) -> list[str]:
    return row + [""] * max(0, width - len(row))


def sort_key(
    row: list[str],
    header: list[str],
    file_name: str,
    name_lookup: dict[str, str],
    original_index: int,
) -> tuple[object, ...]:
    width = len(header)
    row = padded_row(row, width)

    code_index = header.index("codigo") if "codigo" in header else None
    codes = split_codes(row[code_index]) if code_index is not None else []

    if file_name == "00_datos.csv" and "nombre" in header:
        name_index = header.index("nombre")
        primary = row[name_index].strip()
    else:
        names = [name_lookup[code] for code in codes if code in name_lookup]
        primary = min(names, key=normalize_text) if names else ""

    fallback = ";".join(codes) if codes else ",".join(row)
    normalized_row = tuple(normalize_text(cell) for cell in row)
    return (
        normalize_text(primary or fallback),
        normalize_text(fallback),
        normalized_row,
        original_index,
    )


def sort_csv(path: Path, name_lookup: dict[str, str], dry_run: bool) -> bool:
    rows = read_csv_rows(path)
    if len(rows) <= 2:
        return False

    header = [cell.strip().removeprefix("\ufeff") for cell in rows[0]]
    data = [row for row in rows[1:] if any(cell.strip() for cell in row)]
    if len(data) <= 1:
        return False

    indexed_data = list(enumerate(data))
    sorted_data = [
        row
        for _, row in sorted(
            indexed_data,
            key=lambda item: sort_key(
                row=item[1],
                header=header,
                file_name=path.name,
                name_lookup=name_lookup,
                original_index=item[0],
            ),
        )
    ]
    if sorted_data == data:
        return False

    if not dry_run:
        write_csv_rows(path, [rows[0], *sorted_data])
    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Ordena alfabeticamente los CSV 00_*.csv a 10_*.csv. "
            "Usa el nombre en 00_datos.csv como referencia para ordenar "
            "filas de archivos que solo tienen codigo."
        )
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Muestra que archivos cambiarian sin reescribirlos.",
    )
    args = parser.parse_args()

    name_lookup = build_name_lookup(ROOT_DIR)
    changed = []
    for path in target_files(ROOT_DIR):
        if sort_csv(path, name_lookup=name_lookup, dry_run=args.dry_run):
            changed.append(path.name)

    if args.dry_run:
        prefix = "Cambiarian" if changed else "No cambiarian"
    else:
        prefix = "Ordenados" if changed else "Ya estaban ordenados"
    print(f"{prefix}: {', '.join(changed) if changed else 'ninguno'}")


if __name__ == "__main__":
    main()
