"""Run explicitly with --consent; the GUI never downloads weights."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.ai.model_manager import CATALOG, download_model


def main():
    parser = argparse.ArgumentParser(description="Télécharger et vérifier des modèles GGUF pour Redactor")
    parser.add_argument("models", nargs="*", choices=[m.id for m in CATALOG], default=[m.id for m in CATALOG])
    parser.add_argument("--consent", action="store_true", help="Accord explicite pour télécharger les fichiers")
    args = parser.parse_args()
    if not args.consent:
        parser.error("Ajoutez --consent après avoir consulté les tailles et licences dans docs/MODELS.md.")
    root = Path(__file__).resolve().parents[1]
    for info in CATALOG:
        if info.id in args.models:
            print(f"{info.id} : {info.size / 1e6:.1f} Mo · {info.license}", flush=True)
            print(download_model(info, root / "models", consent=True), flush=True)


if __name__ == "__main__":
    main()
