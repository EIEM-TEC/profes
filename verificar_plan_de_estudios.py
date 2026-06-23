from __future__ import annotations

import argparse
from dataclasses import dataclass
import difflib
import sys
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "clasificacion_saberes" / "data"


@dataclass(frozen=True)
class CheckSpec:
    name: str
    local_path: Path
    source_url: str


DEFAULT_CHECKS = (
    CheckSpec(
        name="plan_de_estudios",
        local_path=DATA_DIR / "plan_de_estudios.csv",
        source_url=(
            "https://raw.githubusercontent.com/EIEM-TEC/CLIE/main/"
            "cursos/plan_de_estudios.csv"
        ),
    ),
    CheckSpec(
        name="cursos_rasgos",
        local_path=DATA_DIR / "cursos_rasgos.csv",
        source_url=(
            "https://raw.githubusercontent.com/EIEM-TEC/CLIE/main/"
            "cursos/cursos_rasgos.csv"
        ),
    ),
    CheckSpec(
        name="areas",
        local_path=DATA_DIR / "areas.csv",
        source_url="https://raw.githubusercontent.com/EIEM-TEC/CLIE/main/areas.csv",
    ),
    CheckSpec(
        name="saberes",
        local_path=DATA_DIR / "saberes.csv",
        source_url=(
            "https://raw.githubusercontent.com/EIEM-TEC/CLIE/main/"
            "rasgos_ejes/saberes.csv"
        ),
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Verifica que los CSV locales de CLIE coincidan con las "
            "versiones oficiales de EIEM-TEC/CLIE."
        )
    )
    parser.add_argument(
        "--local",
        default=None,
        help="Ruta local de un CSV especifico a validar. Usar junto con --url.",
    )
    parser.add_argument(
        "--url",
        default=None,
        help="URL cruda oficial para --local.",
    )
    parser.add_argument(
        "--only",
        action="append",
        choices=[check.name for check in DEFAULT_CHECKS],
        help="Valida solo este archivo. Se puede repetir.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="Tiempo maximo de espera para descargar el CSV oficial.",
    )
    parser.add_argument(
        "--max-diff-lines",
        type=int,
        default=200,
        help="Cantidad maxima de lineas de diff que se imprimen si hay diferencias.",
    )
    args = parser.parse_args()
    if (args.local is None) != (args.url is None):
        parser.error("--local y --url se deben usar juntos.")
    return args


def resolve_local_path(path_text: str) -> Path:
    path = Path(path_text)
    if not path.is_absolute():
        path = ROOT / path
    return path


def download_bytes(url: str, timeout: float) -> bytes:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "profes-plan-de-estudios-check/1.0"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def decode_text(data: bytes, label: str) -> str:
    for encoding in ("utf-8-sig", "utf-8"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            pass
    try:
        return data.decode("latin-1")
    except UnicodeDecodeError as exc:
        raise ValueError(f"No se pudo decodificar {label}: {exc}") from exc


def normalize_csv_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if not text:
        return text
    return text.rstrip("\n") + "\n"


def short_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def print_diff(
    local_text: str,
    remote_text: str,
    local_label: str,
    remote_label: str,
    max_lines: int,
) -> None:
    diff_lines = list(
        difflib.unified_diff(
            local_text.splitlines(keepends=True),
            remote_text.splitlines(keepends=True),
            fromfile=local_label,
            tofile=remote_label,
        )
    )
    if not diff_lines:
        return

    shown_lines = diff_lines[:max_lines]
    sys.stdout.writelines(shown_lines)
    if len(diff_lines) > len(shown_lines):
        hidden = len(diff_lines) - len(shown_lines)
        print(f"\n... diff recortado: {hidden} lineas adicionales.")


def check_csv(spec: CheckSpec, timeout: float, max_diff_lines: int) -> int:
    local_path = resolve_local_path(str(spec.local_path))
    try:
        local_bytes = local_path.read_bytes()
    except FileNotFoundError:
        print(
            f"ERROR: no existe el archivo local para {spec.name}: {short_path(local_path)}",
            file=sys.stderr,
        )
        return 2
    except OSError as exc:
        print(f"ERROR: no se pudo leer {short_path(local_path)}: {exc}", file=sys.stderr)
        return 2

    try:
        remote_bytes = download_bytes(spec.source_url, timeout)
    except urllib.error.URLError as exc:
        print(f"ERROR: no se pudo descargar {spec.source_url}: {exc}", file=sys.stderr)
        return 2
    except TimeoutError:
        print(f"ERROR: tiempo agotado al descargar {spec.source_url}", file=sys.stderr)
        return 2

    try:
        local_text = normalize_csv_text(decode_text(local_bytes, short_path(local_path)))
        remote_text = normalize_csv_text(decode_text(remote_bytes, spec.source_url))
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    local_label = short_path(local_path)
    if local_text == remote_text:
        print(f"OK: {spec.name} ({local_label}) coincide con la fuente oficial.")
        return 0

    print(f"ERROR: {spec.name} ({local_label}) no coincide con la fuente oficial.")
    print(f"Fuente oficial: {spec.source_url}\n")
    print_diff(local_text, remote_text, local_label, spec.source_url, max_diff_lines)
    return 1


def selected_checks(args: argparse.Namespace) -> list[CheckSpec]:
    if args.local and args.url:
        return [
            CheckSpec(
                name=Path(args.local).stem or "custom",
                local_path=resolve_local_path(args.local),
                source_url=args.url,
            )
        ]

    selected_names = set(args.only or [check.name for check in DEFAULT_CHECKS])
    return [check for check in DEFAULT_CHECKS if check.name in selected_names]


def main() -> int:
    args = parse_args()
    exit_code = 0
    for spec in selected_checks(args):
        result = check_csv(spec, args.timeout, args.max_diff_lines)
        if result == 2:
            exit_code = 2
        elif result == 1 and exit_code == 0:
            exit_code = 1
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
