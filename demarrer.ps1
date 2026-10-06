<#
  demarrer.ps1 - Installe (si nécessaire) puis lance BioAccess sous Windows.

  Utilisation : double-cliquer sur demarrer.bat
           ou : powershell -ExecutionPolicy Bypass -File .\demarrer.ps1 [-Port 8000]

  Chaque étape est idempotente : relancer le script ne réinstalle que ce qui manque
  ou ce qui a changé (dépendances Python et JavaScript suivies par empreinte SHA-256).
#>
param(
    [int]$Port = 8000
)

# Les erreurs des commandes externes sont vérifiées une à une via $LASTEXITCODE :
# avec 'Stop', Windows PowerShell 5.1 transformerait le moindre avertissement de pip en erreur.
$ErrorActionPreference = 'Continue'

$Racine     = $PSScriptRoot
$Backend    = Join-Path $Racine 'backend'
$Frontend   = Join-Path $Racine 'frontend'
$DossierVenv = Join-Path $Backend '.venv'
$PythonVenv = Join-Path $DossierVenv 'Scripts\python.exe'

function Etape([string]$texte) {
    Write-Host ''
    Write-Host "==> $texte" -ForegroundColor Cyan
}

function Echec([string]$texte) {
    Write-Host ''
    Write-Host "ERREUR : $texte" -ForegroundColor Red
    exit 1
}

function Verifier([string]$quoi) {
    if ($LASTEXITCODE -ne 0) { Echec "$quoi a échoué (code $LASTEXITCODE). Lisez le message juste au-dessus." }
}

function Existe([string]$commande) {
    return [bool](Get-Command $commande -ErrorAction SilentlyContinue)
}

# Empreinte d'un fichier, pour savoir si les dépendances ont changé depuis la dernière installation.
function Empreinte([string]$chemin) {
    return (Get-FileHash -Algorithm SHA256 -Path $chemin).Hash
}

function DejaInstalle([string]$fichierDependances, [string]$marqueur) {
    if (-not (Test-Path $marqueur)) { return $false }
    return ((Get-Content -Raw $marqueur).Trim() -eq (Empreinte $fichierDependances))
}

function PortOccupe([int]$p) {
    $client = New-Object System.Net.Sockets.TcpClient
    try { $client.Connect('127.0.0.1', $p); return $true } catch { return $false } finally { $client.Close() }
}

Write-Host 'BioAccess - installation et démarrage' -ForegroundColor Green
Write-Host "Dossier du projet : $Racine"

# --- 1. Prérequis --------------------------------------------------------------------------
Etape '1/5 Vérification des prérequis'
if (-not (Existe 'py')) {
    Echec "Python est introuvable. Installez Python 3.11 depuis https://www.python.org/downloads/ (cochez « Add python.exe to PATH »), fermez cette fenêtre puis relancez."
}
& py -3.11 --version
if ($LASTEXITCODE -ne 0) {
    Echec "Python 3.11 est introuvable (la commande « py -0 » liste les versions installées). Installez Python 3.11 depuis https://www.python.org/downloads/ puis relancez."
}
if (-not (Existe 'node')) {
    Echec 'Node.js est introuvable. Installez Node.js 22 LTS depuis https://nodejs.org/, fermez cette fenêtre puis relancez.'
}
$versionNode = (& node --version).Trim().TrimStart('v')
$partiesNode = $versionNode.Split('.')
$majeurNode = [int]$partiesNode[0]
$mineurNode = [int]$partiesNode[1]
if ($majeurNode -lt 20 -or ($majeurNode -eq 20 -and $mineurNode -lt 19)) {
    Echec "Node.js $versionNode est trop ancien : il faut la version 20.19 ou plus récente (22 LTS conseillée, https://nodejs.org/)."
}
Write-Host "Node.js $versionNode"

# --- 2. Environnement Python ---------------------------------------------------------------
Etape '2/5 Environnement Python et dépendances'
if (-not (Test-Path $PythonVenv)) {
    Write-Host 'Création de l''environnement virtuel (backend\.venv)...'
    & py -3.11 -m venv $DossierVenv
    Verifier 'La création de l''environnement Python'
}
$requirements = Join-Path $Backend 'requirements.txt'
$marqueurPython = Join-Path $DossierVenv 'bioaccess-dependances.sha256'
if (DejaInstalle $requirements $marqueurPython) {
    Write-Host 'Dépendances Python déjà à jour.'
} else {
    Write-Host 'Installation des dépendances Python (la première fois : plusieurs minutes)...'
    & $PythonVenv -m pip install --disable-pip-version-check --no-warn-script-location -r $requirements
    Verifier 'L''installation des dépendances Python'
    Set-Content -Path $marqueurPython -Value (Empreinte $requirements)
}

# --- 3. Modèles biométriques ---------------------------------------------------------------
Etape '3/5 Modèles biométriques InsightFace (environ 280 Mo, une seule fois)'
& $PythonVenv (Join-Path $Backend 'scripts\telecharger_modeles.py')
Verifier 'Le téléchargement des modèles'

# --- 4. Interface web ----------------------------------------------------------------------
Etape '4/5 Construction de l''interface web'
$verrouNpm = Join-Path $Frontend 'package-lock.json'
$marqueurNpm = Join-Path $Frontend 'node_modules\bioaccess-dependances.sha256'
Push-Location $Frontend
if (-not (DejaInstalle $verrouNpm $marqueurNpm)) {
    Write-Host 'Installation des dépendances JavaScript (npm ci)...'
    & npm ci --no-audit --no-fund
    Verifier 'L''installation des dépendances JavaScript (npm ci)'
    Set-Content -Path $marqueurNpm -Value (Empreinte $verrouNpm)
}
& npm run build
Verifier 'La construction de l''interface (npm run build)'
Pop-Location

# --- 5. Démarrage --------------------------------------------------------------------------
Etape '5/5 Démarrage de BioAccess'
$url = "http://localhost:$Port"
if (PortOccupe $Port) {
    Write-Host "Le port $Port est déjà utilisé : BioAccess tourne peut-être déjà dans une autre fenêtre." -ForegroundColor Yellow
    Write-Host "Ouvrez $url, ou fermez l'autre fenêtre, ou relancez avec un autre port : .\demarrer.ps1 -Port 8001"
    try { Start-Process $url } catch { }
    exit 0
}

# Ouvre le navigateur dès que l'API répond (le chargement des modèles prend quelques secondes).
$null = Start-Job -ArgumentList $Port, $url -ScriptBlock {
    param($port, $url)
    $pret = $false
    for ($i = 0; $i -lt 120 -and -not $pret; $i++) {
        try {
            Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$port/api/sante" -TimeoutSec 2 | Out-Null
            $pret = $true
        } catch {
            Start-Sleep -Seconds 1
        }
    }
    if ($pret) { Start-Process $url }
}

Write-Host "BioAccess démarre ; le navigateur s'ouvrira sur $url"
Write-Host 'Pour arrêter la plateforme : fermez cette fenêtre ou appuyez sur Ctrl+C.' -ForegroundColor Yellow
Push-Location $Backend
& $PythonVenv -m uvicorn app.main:app --host 127.0.0.1 --port $Port
Pop-Location
