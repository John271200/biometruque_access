"""Télécharge les modèles InsightFace « buffalo_l » dans backend/models/buffalo_l/.

Utilisation (depuis le dossier backend) :

    python scripts/telecharger_modeles.py

Le script est idempotent : si les trois modèles utilisés par BioAccess sont déjà présents,
il ne retélécharge rien. Il n'utilise que la bibliothèque standard Python.

ATTENTION — licence : les modèles pré-entraînés InsightFace sont réservés à un usage de
recherche académique NON COMMERCIAL. Toute utilisation commerciale exige une licence
auprès d'InsightFace.
"""

from __future__ import annotations

import argparse
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path

URL_BUFFALO_L = "https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_l.zip"
MODELES_UTILES = ("det_10g.onnx", "1k3d68.onnx", "w600k_r50.onnx")
DOSSIER_DEFAUT = Path(__file__).resolve().parent.parent / "models" / "buffalo_l"
AVERTISSEMENT_LICENCE = (
    "Rappel : les modèles InsightFace buffalo_l sont réservés à un usage de recherche "
    "non commercial."
)


def modeles_presents(dossier: Path) -> bool:
    """Vrai si les trois modèles utiles existent (et ne sont pas vides)."""
    return all((dossier / nom).is_file() and (dossier / nom).stat().st_size > 0
               for nom in MODELES_UTILES)


def _afficher_progression(recu: int, total: int) -> None:
    if total > 0:
        pourcentage = recu * 100 / total
        sys.stdout.write(f"\r  Téléchargement : {recu / 1e6:6.1f} / {total / 1e6:.1f} Mo ({pourcentage:5.1f} %)")
    else:
        sys.stdout.write(f"\r  Téléchargement : {recu / 1e6:6.1f} Mo")
    sys.stdout.flush()


def telecharger(url: str, destination: Path) -> None:
    """Télécharge ``url`` dans ``destination`` en affichant la progression."""
    partiel = destination.with_suffix(destination.suffix + ".partiel")
    with urllib.request.urlopen(url, timeout=60) as reponse, open(partiel, "wb") as sortie:
        total = int(reponse.headers.get("Content-Length") or 0)
        recu = 0
        while True:
            bloc = reponse.read(1024 * 1024)
            if not bloc:
                break
            sortie.write(bloc)
            recu += len(bloc)
            _afficher_progression(recu, total)
    print()
    if total and recu != total:
        partiel.unlink(missing_ok=True)
        raise IOError(f"Téléchargement incomplet ({recu} octets reçus sur {total}).")
    partiel.replace(destination)


def extraire_modeles(archive: Path, dossier: Path) -> list[str]:
    """Extrait les fichiers .onnx de l'archive (à plat) dans ``dossier``."""
    extraits = []
    with zipfile.ZipFile(archive) as zf:
        for info in zf.infolist():
            nom = Path(info.filename).name
            if info.is_dir() or not nom.endswith(".onnx"):
                continue
            with zf.open(info) as source, open(dossier / nom, "wb") as cible:
                shutil.copyfileobj(source, cible)
            extraits.append(nom)
    return extraits


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Télécharge les modèles InsightFace buffalo_l.")
    parser.add_argument("--dossier", type=Path, default=DOSSIER_DEFAUT,
                        help="dossier de destination (défaut : backend/models/buffalo_l)")
    parser.add_argument("--forcer", action="store_true", help="retélécharger même si les modèles sont présents")
    args = parser.parse_args(argv)
    dossier: Path = args.dossier

    print(AVERTISSEMENT_LICENCE)
    if modeles_presents(dossier) and not args.forcer:
        print(f"Les modèles sont déjà présents dans « {dossier} » : rien à télécharger.")
        return 0

    dossier.mkdir(parents=True, exist_ok=True)
    archive = dossier / "buffalo_l.zip"
    print(f"Téléchargement de buffalo_l (≈ 280 Mo) depuis {URL_BUFFALO_L}")
    try:
        telecharger(URL_BUFFALO_L, archive)
        print("Extraction des modèles…")
        extraits = extraire_modeles(archive, dossier)
    except (OSError, zipfile.BadZipFile) as exc:
        print(f"\nÉchec : {exc}\nVérifiez votre connexion Internet puis relancez le script.",
              file=sys.stderr)
        return 1
    finally:
        archive.unlink(missing_ok=True)
        archive.with_name(archive.name + ".partiel").unlink(missing_ok=True)

    print(f"Modèles extraits : {', '.join(sorted(extraits))}")
    if not modeles_presents(dossier):
        manquants = [n for n in MODELES_UTILES if not (dossier / n).is_file()]
        print(f"Échec : modèle(s) absent(s) de l'archive : {', '.join(manquants)}", file=sys.stderr)
        return 1
    print(f"Terminé : les modèles sont prêts dans « {dossier} ».")
    return 0


if __name__ == "__main__":
    sys.exit(main())
