"""Reproducible local benchmark. Human quality scores intentionally remain blank."""
import argparse
from dataclasses import asdict
import csv
import json
from pathlib import Path
import platform
import threading
import time
import psutil
from .engine import LlamaEngine
from .model_manager import sha256
from .prompts import Request

CASES = (
    ("orthographe", Request("correct", "Bonjours Madame Dupont, je vous envoi les document demain."), ["Dupont"]),
    ("grammaire", Request("correct", "Les réunion que nous avons organisé sont terminé."), []),
    ("mail_professionnel", Request("compose", "Demander poliment à Madame Martin de confirmer sa présence à la réunion du 24 octobre à 10 h.", "Professionnel"), ["Martin", "24", "10"]),
    ("reponse_mail", Request("reply", "Bonjour Camille, pouvez-vous me transmettre le compte rendu de la réunion ? Merci, Léa.", "Professionnel", "Répondre que le compte rendu sera transmis demain."), ["Léa", "demain"]),
    ("reformulation_naturelle", Request("rewrite", "Je me permets de porter à votre connaissance mon indisponibilité pour demain.", "Naturel"), ["demain"]),
    ("reformulation_administrative", Request("rewrite", "Je souhaite savoir où en est mon dossier envoyé le 12 septembre.", "Administratif"), ["12", "septembre"]),
    ("resume", Request("summarize", "L’association Les Hirondelles organise un atelier gratuit le 24 octobre à Lyon. Il commence à 14 h et se termine à 16 h. L’inscription est obligatoire avant le 20 octobre.", "Concis"), ["Hirondelles", "Lyon", "24", "14", "16", "20"]),
    ("respect_consignes", Request("compose", "Écris exactement deux phrases courtes pour remercier une collègue de son aide. N’utilise aucun prénom.", "Amical"), []),
    ("noms_propres", Request("correct", "Éloïse Le Goff et Jean-Baptiste D’Arcy travaille à Saint-Étienne pour XyloNova."), ["Éloïse Le Goff", "Jean-Baptiste D’Arcy", "Saint-Étienne", "XyloNova"]),
    ("absence_invention", Request("reply", "Bonjour, quel est le prix et la date de livraison du produit ?", "Professionnel", "Ces informations ne sont pas fournies. Utiliser [à compléter], sans inventer de montant ni de date."), ["[à compléter]"]),
)
RUBRIC = {
    "method": "Deux relecteurs francophones évaluent indépendamment les sorties anonymisées, puis résolvent leurs désaccords. Une seule série n’est pas une étude comparative fiable.",
    "scale": {"0": "Échec majeur", "1": "Erreurs importantes", "2": "Acceptable avec corrections", "3": "Prêt après relecture"},
    "criteria": ["orthographe_grammaire", "respect_consigne", "fidelite_faits_noms_nombres", "francais_style_utilisable"],
    "critical_failure": "Un fait inventé, un nom déformé ou une consigne essentielle ignorée doit être signalé séparément.",
}


def run(model, output, threads=0, tokens=256, repeat=1):
    output.mkdir(parents=True, exist_ok=True)
    process = psutil.Process()
    peak, stopping = [process.memory_info().rss], threading.Event()
    def sample():
        while not stopping.wait(.01):
            peak[0] = max(peak[0], process.memory_info().rss)
    monitor = threading.Thread(target=sample, daemon=True)
    monitor.start()
    engine, rows = LlamaEngine(), []
    try:
        load = engine.load(model, threads=threads)
        load_peak = peak[0]
        for repetition in range(repeat):
            for case, request, preserved in CASES:
                peak[0] = process.memory_info().rss
                started = time.perf_counter()
                result = "".join(engine.stream(request, max_tokens=tokens))
                metrics = asdict(engine.metrics)
                row = {"case": case, "repeat": repetition + 1, "model": model.name,
                    "model_size_bytes": model.stat().st_size, "load_seconds": load.load_seconds,
                    **metrics, "peak_rss_bytes": peak[0], "load_peak_rss_bytes": load_peak,
                    "action": request.action, "source": request.text, "instruction": request.instruction,
                    "style": request.style, "output": result,
                    "literal_preservation_flags": {name: name in result for name in preserved},
                    "human_scores": {name: None for name in RUBRIC["criteria"]},
                    "human_critical_failure": None, "human_notes": ""}
                rows.append(row)
                print(f"{model.name}: {case} · {metrics['total_seconds']:.2f}s · {metrics['output_tokens']} tokens", flush=True)
    finally:
        stopping.set()
        monitor.join(1)
        engine.close()
    report = {"schema_version": 1, "model": str(model), "sha256": sha256(model),
        "environment": {"os": platform.platform(), "python": platform.python_version(), "cpu": platform.processor(),
                        "physical_cores": psutil.cpu_count(logical=False), "threads": threads, "tokens_limit": tokens},
        "method": {"timing": "perf_counter; first nonempty model delta; warm prompt cache after first case",
                   "tokens": "Output retokenized without BOS, includes hidden reasoning if present; rate=(tokens-1)/(total-first_delta). This can differ from internal decode counts.",
                   "memory": "Process RSS sampled every 10 ms, not commit size; mmap includes OS file cache effects.",
                   "quality": "Literal flags are diagnostics, not quality scores. Human grid is unscored until reviewed."},
        "rubric": RUBRIC, "results": rows}
    path = output / (model.stem + ".json")
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    columns = ["model", "case", "repeat", "model_size_bytes", "load_seconds", "first_token_seconds", "tokens_per_second",
               "total_seconds", "output_tokens", "peak_rss_bytes", "finish_reason", "output", *RUBRIC["criteria"], "human_notes"]
    with path.with_suffix(".csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({**row, **row["human_scores"]})
    return report


def main():
    parser = argparse.ArgumentParser(description="Benchmark local Redactor avec grille humaine reproductible")
    parser.add_argument("models", type=Path, nargs="+")
    parser.add_argument("--output", type=Path, default=Path("docs/validation/benchmarks"))
    parser.add_argument("--threads", type=int, default=0)
    parser.add_argument("--tokens", type=int, default=256)
    parser.add_argument("--repeat", type=int, default=1)
    args = parser.parse_args()
    for model in args.models:
        run(model, args.output, args.threads, args.tokens, args.repeat)


if __name__ == "__main__":
    main()
