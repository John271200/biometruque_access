"""BioHashing (gabarit révocable) et chiffrement AES-256-GCM."""

import numpy as np
import pytest

from app.biometrie import Chiffreur, ErreurIntegrite, biohash, generer_jeton, similarite_hamming


def _unitaire(rng, dim=512):
    v = rng.standard_normal(dim)
    return v / np.linalg.norm(v)


def _a_angle(v, angle_deg, rng):
    """Vecteur unitaire formant exactement l'angle demandé avec ``v``."""
    o = rng.standard_normal(v.shape[0])
    o -= (o @ v) * v
    o /= np.linalg.norm(o)
    a = np.radians(angle_deg)
    return np.cos(a) * v + np.sin(a) * o


# ------------------------------------------------------------------------ jeton / BioHash
def test_jeton_32_octets_aleatoires():
    j1, j2 = generer_jeton(), generer_jeton()
    assert isinstance(j1, bytes) and len(j1) == 32
    assert j1 != j2


def test_biohash_deterministe_et_32_octets():
    rng = np.random.default_rng(0)
    v, jeton = _unitaire(rng), generer_jeton()
    code = biohash(v, jeton, "visage")
    assert isinstance(code, bytes) and len(code) == 32
    assert biohash(v.copy(), jeton, "visage") == code
    assert biohash(v.astype(np.float32), jeton, "visage") == code


def test_biohash_meme_vecteur_similarite_1():
    rng = np.random.default_rng(1)
    v, jeton = _unitaire(rng), generer_jeton()
    assert similarite_hamming(biohash(v, jeton, "visage"), biohash(v, jeton, "visage")) == 1.0
    # Le signe d'une projection ne dépend pas de la norme.
    assert biohash(3.7 * v, jeton, "visage") == biohash(v, jeton, "visage")


def test_biohash_jeton_different_environ_0_5():
    """Révocation : un nouveau jeton donne un code sans rapport avec l'ancien."""
    rng = np.random.default_rng(2)
    v = _unitaire(rng)
    reference = biohash(v, generer_jeton(), "visage")
    sims = [similarite_hamming(reference, biohash(v, generer_jeton(), "visage")) for _ in range(30)]
    assert abs(np.mean(sims) - 0.5) < 0.03
    assert all(0.35 < s < 0.65 for s in sims)


def test_biohash_modalites_independantes():
    rng = np.random.default_rng(3)
    v, jeton = _unitaire(rng), generer_jeton()
    sims = [similarite_hamming(biohash(v, jeton, "visage"), biohash(v, jeton, "oreille"))]
    v2 = _unitaire(rng)
    sims.append(similarite_hamming(biohash(v2, jeton, "visage"), biohash(v2, jeton, "oreille")))
    assert all(0.35 < s < 0.65 for s in sims)


@pytest.mark.parametrize("angle", [30, 60, 90, 120])
def test_biohash_relation_angle_sur_pi(angle):
    """Hachage par hyperplans aléatoires : E[similarité] = 1 − θ/π."""
    rng = np.random.default_rng(angle)
    sims = []
    for _ in range(40):
        v = _unitaire(rng)
        w = _a_angle(v, angle, rng)
        jeton = generer_jeton()
        sims.append(similarite_hamming(biohash(v, jeton, "visage"), biohash(w, jeton, "visage")))
    assert np.mean(sims) == pytest.approx(1 - angle / 180, abs=0.02)


def test_biohash_dimension_oreille_et_visage_acceptees():
    rng = np.random.default_rng(4)
    jeton = generer_jeton()
    assert len(biohash(rng.standard_normal(256), jeton, "oreille")) == 32
    assert len(biohash(rng.standard_normal(924), jeton, "oreille")) == 32


def test_biohash_refuse_dimension_inferieure_au_nombre_de_bits():
    with pytest.raises(ValueError):
        biohash(np.ones(255), generer_jeton(), "oreille")
    with pytest.raises(ValueError):
        biohash(np.ones((16, 32)), generer_jeton(), "oreille")


def test_similarite_hamming_valeurs_connues():
    assert similarite_hamming(b"\x00" * 32, b"\xff" * 32) == 0.0
    assert similarite_hamming(b"\x00" * 32, b"\x00" * 31 + b"\x01") == pytest.approx(1 - 1 / 256)
    with pytest.raises(ValueError):
        similarite_hamming(b"\x00" * 32, b"\x00" * 16)


# ------------------------------------------------------------------------ AES-256-GCM
def test_chiffrement_aller_retour_et_nonce_aleatoire():
    c = Chiffreur(bytes(range(32)))
    donnees, aad = b"code biohash" * 3, b"42|visage"
    b1, b2 = c.chiffrer(donnees, aad), c.chiffrer(donnees, aad)
    assert b1 != b2  # nonce aléatoire
    assert len(b1) == 12 + len(donnees) + 16
    assert c.dechiffrer(b1, aad) == donnees
    assert c.dechiffrer(b2, aad) == donnees


@pytest.mark.parametrize("position", [0, 11, 12, -1])  # nonce, début du chiffré, tag
def test_alteration_detectee(position):
    c = Chiffreur(bytes(32))
    blob = bytearray(c.chiffrer(b"secret", b"1|oreille"))
    blob[position] ^= 0x01
    with pytest.raises(ErreurIntegrite):
        c.dechiffrer(bytes(blob), b"1|oreille")


def test_mauvaise_aad_ou_mauvaise_cle_refusee():
    c = Chiffreur(bytes(32))
    blob = c.chiffrer(b"secret", b"1|visage")
    with pytest.raises(ErreurIntegrite):
        c.dechiffrer(blob, b"2|visage")
    with pytest.raises(ErreurIntegrite):
        Chiffreur(b"\x01" * 32).dechiffrer(blob, b"1|visage")
    with pytest.raises(ErreurIntegrite):
        c.dechiffrer(blob[:20], b"1|visage")


def test_cle_de_mauvaise_taille_refusee():
    with pytest.raises(ValueError):
        Chiffreur(b"trop courte")
