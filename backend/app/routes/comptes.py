"""Création de compte et session « compte » (connexion / déconnexion par mot de passe)."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.audit import journaliser
from app.config import Settings
from app.db import maintenant
from app.dependances import Authentifie, adresse_ip, authentifie_compte, obtenir_bdd, obtenir_settings
from app.erreurs import ErreurAPI
from app.modeles import JetonRevoque, Utilisateur
from app.schemas import Connexion, CreationCompte, utilisateur_vers_dict
from app.securite import creer_jeton, hacher_mot_de_passe, verifier_mot_de_passe

router = APIRouter(tags=["comptes"])


@router.post("/comptes", status_code=201)
def creer_compte(corps: CreationCompte, bdd: Session = Depends(obtenir_bdd)) -> dict:
    """Inscription : nom, email (unique, en minuscules) et mot de passe robuste."""
    deja_utilise = ErreurAPI(
        409, "EMAIL_DEJA_UTILISE",
        "Cette adresse email est déjà utilisée. Connectez-vous ou choisissez-en une autre.",
        {"email": "Adresse déjà utilisée."})
    if bdd.scalar(select(Utilisateur.id).where(Utilisateur.email == corps.email)):
        raise deja_utilise
    utilisateur = Utilisateur(nom=corps.nom, email=corps.email,
                              mot_de_passe_hash=hacher_mot_de_passe(corps.mot_de_passe))
    bdd.add(utilisateur)
    try:
        bdd.flush()
    except IntegrityError:  # inscription concurrente avec la même adresse
        bdd.rollback()
        raise deja_utilise from None
    journaliser(bdd, "COMPTE_CREE", utilisateur.id)
    bdd.commit()
    return utilisateur_vers_dict(utilisateur)


@router.post("/session")
def se_connecter(corps: Connexion, request: Request, bdd: Session = Depends(obtenir_bdd),
                 settings: Settings = Depends(obtenir_settings)) -> dict:
    """Connexion par email + mot de passe : renvoie un jeton `compte` (60 min)."""
    utilisateur = bdd.scalar(select(Utilisateur).where(Utilisateur.email == corps.email))
    if not verifier_mot_de_passe(utilisateur.mot_de_passe_hash if utilisateur else None,
                                 corps.mot_de_passe):
        if utilisateur:
            journaliser(bdd, "CONNEXION_ECHOUEE", utilisateur.id, ip=adresse_ip(request))
            bdd.commit()
        raise ErreurAPI(401, "IDENTIFIANTS_INVALIDES", "Adresse email ou mot de passe incorrect.")
    jeton = creer_jeton(settings.secret_jwt, "compte", utilisateur.id)
    journaliser(bdd, "CONNEXION", utilisateur.id, ip=adresse_ip(request))
    bdd.commit()
    return {
        "jeton_compte": jeton.jeton,
        "expire_dans": jeton.expire_dans,
        "utilisateur": utilisateur_vers_dict(utilisateur),
    }


@router.delete("/session", status_code=204)
def se_deconnecter(auth: Authentifie = Depends(authentifie_compte),
                   bdd: Session = Depends(obtenir_bdd)) -> Response:
    """Déconnexion : le jeton `compte` présenté est révoqué jusqu'à son expiration."""
    instant = maintenant()
    bdd.execute(delete(JetonRevoque).where(JetonRevoque.expire_le < instant))  # purge
    expire_le = datetime.fromtimestamp(int(auth.jeton["exp"]), tz=timezone.utc)
    bdd.merge(JetonRevoque(jti=auth.jeton["jti"], expire_le=expire_le))
    journaliser(bdd, "DECONNEXION", auth.utilisateur.id)
    bdd.commit()
    return Response(status_code=204)

