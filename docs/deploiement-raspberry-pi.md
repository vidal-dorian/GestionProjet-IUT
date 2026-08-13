# Déploiement sur Raspberry Pi

Ce document s'adresse à l'agent (ou à la personne) chargé de déployer
**GestionProjet-IUT** sur un Raspberry Pi et de l'exposer publiquement via
Cloudflare Tunnel. Il part du principe que le Raspberry Pi tourne un OS
64 bits (Raspberry Pi OS 64-bit ou équivalent) et que Docker y est déjà
installé, ou peut l'être.

## Architecture cible

```
Internet
   │  HTTPS (TLS terminé par Cloudflare)
   ▼
Cloudflare Tunnel (cloudflared, tourne sur le Pi)
   │  HTTP (loopback, à l'intérieur du Pi)
   ▼
nginx (conteneur "frontend", écoute sur le port hôte 8080)
   ├── sert les fichiers statiques du frontend (React)
   └── /api/*  ──reverse proxy──▶  backend (conteneur FastAPI, port 8000, réseau Docker interne)
                                        │
                                        ▼
                                   MySQL (conteneur, port interne uniquement,
                                   volume Docker persistant)
```

Points importants de cette architecture :

- **Un seul point d'entrée public** : nginx sert le frontend *et* fait
  reverse-proxy `/api/*` vers le backend. Le navigateur ne voit qu'une seule
  origine, ce qui évite tout problème de CORS et garde le cookie de session
  scopé au bon domaine. Un seul hostname Cloudflare Tunnel suffit — pas
  besoin d'un sous-domaine séparé pour l'API.
- **MySQL n'est jamais exposé** à l'extérieur du réseau Docker interne créé
  par `docker compose` (pas de `ports:` sur le service `mysql`).
- **Les données persistent** dans un volume Docker nommé (`mysql_data`), qui
  survit aux redémarrages de conteneurs et aux `docker compose up` répétés.

## Prérequis sur le Raspberry Pi

- Un Raspberry Pi avec un OS 64 bits (vérifier avec `uname -m` → doit
  afficher `aarch64`).
- Docker Engine + le plugin Docker Compose (`docker compose version` doit
  fonctionner). Si absent :
  ```bash
  curl -fsSL https://get.docker.com | sh
  sudo usermod -aG docker $USER
  # se reconnecter (ou `newgrp docker`) pour que le groupe soit pris en compte
  ```
- `git` installé.
- Un nom de domaine (ou sous-domaine) déjà géré par Cloudflare, et un compte
  Cloudflare avec Zero Trust activé (gratuit) pour Cloudflare Tunnel.
- Idéalement, les données MySQL sur un support autre que la carte SD (clé
  USB / SSD externe monté, par exemple sur `/mnt/ssd`) — la carte SD s'use
  vite avec des écritures fréquentes de base de données. Voir la section
  *Stockage* plus bas si c'est le cas.

## 1. Récupérer le code

```bash
git clone https://github.com/vidal-dorian/GestionProjet-IUT.git
cd GestionProjet-IUT
```

Si le dépôt est déjà cloné, mettre à jour :

```bash
cd GestionProjet-IUT
git pull origin main
```

## 2. Configurer les variables d'environnement

```bash
cp .env.example .env
```

Éditer `.env` et renseigner au minimum :

| Variable | Valeur attendue |
|---|---|
| `MYSQL_PASSWORD` | Un mot de passe fort, généré aléatoirement |
| `MYSQL_ROOT_PASSWORD` | Un mot de passe fort différent du précédent |
| `CORS_ORIGINS` | Le hostname public final, ex. `https://suivi.mondomaine.fr` (celui qui sera configuré dans Cloudflare Tunnel à l'étape 5) |
| `CLOUDFLARE_TEAM_DOMAIN` | Domaine de l'équipe Cloudflare Zero Trust, ex. `mon-equipe.cloudflareaccess.com` — voir étape 6 |
| `CLOUDFLARE_ACCESS_AUD` | "Application Audience (AUD) Tag" de l'application Access créée à l'étape 6 |

Laisser `VITE_API_URL` **vide** — c'est la configuration attendue pour le
reverse-proxy nginx décrit plus haut (le frontend appelle l'API en
same-origin, pas de domaine séparé à renseigner).

`CLOUDFLARE_TEAM_DOMAIN` et `CLOUDFLARE_ACCESS_AUD` ne sont connues qu'une
fois l'application Access créée (étape 6, après le tunnel) : il est normal
de laisser des valeurs provisoires ici pour le premier `docker compose up`,
tant qu'on sait qu'il faudra revenir les renseigner avant d'exposer
l'application publiquement — voir l'avertissement de l'étape 6.

`.env` contient des secrets réels : il ne doit **jamais** être commité (déjà
listé dans `.gitignore`) ni partagé.

## 3. Builder et lancer les conteneurs

```bash
docker compose up -d --build
```

Premier lancement : le build de l'image frontend (Node → nginx) et de
l'image backend (Python) peut prendre plusieurs minutes sur un Raspberry Pi
selon le modèle. Les lancements suivants (sans changement de code) seront
quasi instantanés grâce au cache Docker.

Vérifier que tout tourne :

```bash
docker compose ps
```

Les trois services (`mysql`, `backend`, `frontend`) doivent être `running`
(et `mysql` `healthy`). Si `backend` redémarre en boucle juste après le
lancement, c'est généralement que MySQL n'a pas fini son initialisation —
`restart: unless-stopped` fait qu'il retente automatiquement ; attendre
quelques dizaines de secondes.

## 4. Vérifier en local sur le Pi

```bash
curl -s http://localhost:8080/api/health
# doit renvoyer {"status":"ok"}

curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8080/
# doit renvoyer 200
```

Si ces deux commandes répondent correctement, l'application tourne. L'étape
suivante ne fait que l'exposer sur Internet.

## 5. Exposer via Cloudflare Tunnel

Cloudflare Tunnel permet d'exposer l'application sans ouvrir de port sur la
box/routeur.

### Installer `cloudflared`

```bash
curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg | sudo tee /usr/share/keyrings/cloudflare-main.gpg >/dev/null
echo 'deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared any main' | sudo tee /etc/apt/sources.list.d/cloudflared.list
sudo apt-get update && sudo apt-get install -y cloudflared
```

### Créer et configurer le tunnel

```bash
cloudflared tunnel login          # ouvre un lien à valider dans un navigateur, autorise le domaine
cloudflared tunnel create gestionprojet-iut
```

Cette dernière commande affiche un UUID de tunnel et crée un fichier
d'identifiants dans `~/.cloudflared/<UUID>.json`. Créer ensuite
`~/.cloudflared/config.yml` :

```yaml
tunnel: <UUID-du-tunnel>
credentials-file: /home/<utilisateur>/.cloudflared/<UUID-du-tunnel>.json

ingress:
  - hostname: suivi.mondomaine.fr
    service: http://localhost:8080
  - service: http_status:404
```

Remplacer `suivi.mondomaine.fr` par le hostname exact renseigné dans
`CORS_ORIGINS` à l'étape 2 — **les deux doivent correspondre exactement**,
sinon le navigateur bloquera les requêtes de l'API.

Router le DNS vers le tunnel :

```bash
cloudflared tunnel route dns gestionprojet-iut suivi.mondomaine.fr
```

### Lancer le tunnel comme service système (survit aux reboots)

```bash
sudo cloudflared service install
sudo systemctl enable --now cloudflared
sudo systemctl status cloudflared   # doit afficher "active (running)"
```

### Vérifier l'accès public

```bash
curl -s https://suivi.mondomaine.fr/api/health
```

Puis ouvrir `https://suivi.mondomaine.fr` dans un navigateur : la liste des
projets doit s'afficher.

À ce stade, l'application est accessible **sans aucune authentification** —
n'importe qui connaissant l'URL peut l'utiliser. L'étape suivante corrige
cela avant toute annonce de l'URL à qui que ce soit.

## 6. Protéger l'accès avec Cloudflare Access (authentification Google)

L'application ne gère plus elle-même l'authentification : elle délègue
entièrement le contrôle d'accès à **Cloudflare Access**, avec **Google**
comme fournisseur d'identité. Concrètement :

- Cloudflare Access s'interpose devant le hostname public (celui configuré
  dans le tunnel à l'étape 5) : personne n'atteint même le frontend sans
  s'être authentifié avec un compte Google autorisé.
- Une politique d'accès restreint qui peut se connecter (liste d'adresses
  e-mail précises, ou domaine complet type `*@mon-universite.fr`).
- Une fois authentifié, Cloudflare transmet l'identité au backend via un
  jeton signé (`Cf-Access-Jwt-Assertion`) que l'application vérifie
  elle-même avant de faire confiance à l'e-mail reçu — voir
  `backend/app/cloudflare_auth.py` pour le détail de cette vérification côté
  code si besoin de débugger.
- **Aucun compte à créer manuellement** : au premier accès réussi d'une
  adresse e-mail, l'application crée automatiquement le compte applicatif
  correspondant.

### Créer l'application Access

1. Aller sur [one.dash.cloudflare.com](https://one.dash.cloudflare.com) →
   **Zero Trust** → **Access** → **Applications** → **Add an application** →
   **Self-hosted**.
2. Renseigner :
   - **Application name** : `GestionProjet-IUT` (libre).
   - **Session duration** : durée de validité de la session avant nouvelle
     authentification Google (ex. `24h` ou `7 days`, au choix).
   - **Application domain** : le hostname exact utilisé pour `CORS_ORIGINS`
     et le tunnel (ex. `suivi.mondomaine.fr`), sans schéma ni slash final.
3. Étape **Identity providers** : sélectionner **Google** (l'activer au
   préalable dans **Settings → Authentication** si ce n'est pas déjà fait —
   Cloudflare guide pas à pas la création des identifiants OAuth Google).
4. Étape **Add policies** : créer une politique **Allow** avec une règle
   **Emails** (une ou plusieurs adresses précises) ou **Email domain**
   (`@mon-universite.fr` par exemple) selon qui doit pouvoir accéder à
   l'application. Sans politique correspondante, personne ne passe.
5. Valider. Cloudflare affiche alors la page de l'application créée.

### Récupérer les valeurs pour `.env`

Sur la page de l'application Access créée à l'instant :

- **Application Audience (AUD) Tag** : visible dans l'onglet **Overview** de
  l'application → coller dans `CLOUDFLARE_ACCESS_AUD` dans `.env`.
- **Team domain** : visible dans **Zero Trust → Settings → Custom Pages** (ou
  dans l'URL du tableau de bord Zero Trust, `<team-name>.cloudflareaccess.com`)
  → coller dans `CLOUDFLARE_TEAM_DOMAIN` dans `.env` (sans `https://`).

Puis relancer le backend pour qu'il prenne en compte ces valeurs :

```bash
docker compose up -d --build backend
```

### Vérifier

Ouvrir `https://suivi.mondomaine.fr` dans une fenêtre de navigation privée :
Cloudflare doit rediriger vers un écran de connexion Google avant de laisser
passer quoi que ce soit. Se connecter avec un compte Google autorisé par la
politique de l'étape 4 doit ensuite donner accès normal à l'application ; un
compte non autorisé doit être bloqué par Cloudflare lui-même, avant même
d'atteindre le serveur.

## 7. Mettre en place le déploiement continu (CI/CD)

Une fois les étapes 1 à 6 terminées et l'application vérifiée en
production, l'étape suivante rend les mises à jour automatiques : chaque
`git push` sur `main` (typiquement le merge d'une pull request) redéploie
l'application sur le Pi sans intervention manuelle.

### Comment ça marche

Le workflow `.github/workflows/ci-cd.yml` définit trois jobs :

1. **`backend-tests`** et **`frontend-build`** tournent sur les runners
   GitHub (cloud) à chaque push et pull request : tests `pytest` côté
   backend, `npm run build` + `npm run lint` côté frontend. Ils ne
   touchent jamais au Raspberry Pi.
2. **`deploy`** ne se déclenche que sur un push sur `main`, uniquement si
   les deux jobs précédents ont réussi. Il tourne sur un **runner
   self-hosted** — c'est-à-dire un agent GitHub Actions installé et
   exécuté directement sur le Raspberry Pi — qui récupère le code puis
   lance `docker compose up -d --build`.

Ce découpage évite de déployer du code cassé : si les tests ou le build
échouent, le job `deploy` ne se lance pas et l'application en production
n'est pas touchée.

### Installer le runner self-hosted sur le Pi

1. Sur GitHub : **Settings** du dépôt → **Actions** → **Runners** → **New
   self-hosted runner**, choisir **Linux** / **ARM64**. GitHub affiche une
   série de commandes à copier-coller (téléchargement, configuration avec
   un jeton d'enregistrement propre à ce dépôt).
2. Exécuter ces commandes **sur le Raspberry Pi**, dans un dossier dédié
   (ex. `~/actions-runner`), avec l'utilisateur qui possède déjà l'accès
   Docker (membre du groupe `docker`, cf. prérequis en haut de ce
   document).
3. Installer le runner comme service système pour qu'il survive aux
   redémarrages :
   ```bash
   sudo ./svc.sh install
   sudo ./svc.sh start
   sudo ./svc.sh status   # doit afficher le service actif
   ```
4. **Étape à ne pas oublier** : le job `deploy` fait un `actions/checkout`
   dans le dossier de travail du runner (par défaut
   `~/actions-runner/_work/GestionProjet-IUT/GestionProjet-IUT`), qui ne
   contient donc **pas** de fichier `.env` (il n'est jamais versionné). Il
   faut le créer une seule fois manuellement dans ce dossier exact, avec
   les mêmes valeurs que celles utilisées aux étapes 2 et 6 (copier le
   `.env` déjà en place, ou refaire `cp .env.example .env` puis le
   remplir). Le `.env` n'est ensuite plus jamais écrasé par les déploiements
   suivants (`clean: false` dans le workflow protège ce fichier).
5. Si l'application avait été déployée manuellement avant la mise en place
   du runner (étapes 1 à 6 ci-dessus, dans un dossier `~/GestionProjet-IUT`
   séparé) : arrêter cette pile-là (`docker compose down`, **sans** `-v`)
   pour éviter que deux piles se disputent le port 8080. Le nom du dossier
   de travail du runner étant identique (`GestionProjet-IUT`), Docker
   Compose retrouve automatiquement le même volume nommé `mysql_data` —
   les données ne sont pas perdues dans la bascule.
6. Déclencher un premier déploiement pour valider l'installation : soit en
   poussant un commit sur `main`, soit manuellement via **Actions** → *CI/CD*
   → **Run workflow** (déclenchement `workflow_dispatch`).

### Vérifier

Dans l'onglet **Actions** du dépôt, le run du workflow doit afficher les
trois jobs en vert, `deploy` compris. Le job `deploy` inclut une vérification
`curl` sur `/api/health` après le redémarrage des conteneurs : s'il échoue,
le run passe en rouge sans qu'il soit nécessaire de se connecter au Pi pour
s'en apercevoir.

## Mettre à jour l'application

**Avec le CI/CD en place (étape 7)** : rien à faire, chaque merge sur `main`
redéploie automatiquement.

**Sans CI/CD, ou en secours si le runner est indisponible** :

```bash
cd GestionProjet-IUT
git pull origin main
docker compose up -d --build
```

Les données MySQL ne sont pas affectées par cette opération (volume
persistant, indépendant des conteneurs).

## Sauvegardes

La base de données vit entièrement dans le volume Docker `mysql_data`.
Sauvegarde logique simple, à planifier périodiquement (ex. cron) :

```bash
docker compose exec mysql sh -c \
  'exec mysqldump -uroot -p"$MYSQL_ROOT_PASSWORD" --all-databases' \
  > backup-$(date +%Y%m%d).sql
```

Conserver ces fichiers `.sql` hors du Raspberry Pi (autre machine, stockage
cloud personnel) — une panne de carte SD ou de disque emporterait sinon
aussi bien l'application que ses sauvegardes locales.

## Stockage (carte SD vs disque externe)

Les écritures fréquentes de MySQL usent prématurément une carte SD. Si un
disque externe (clé USB, SSD) est disponible et monté (ex. sur `/mnt/ssd`),
faire pointer le volume MySQL dessus en ajoutant dans `docker-compose.yml` :

```yaml
volumes:
  mysql_data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /mnt/ssd/gestionprojet-mysql
```

(créer le dossier `/mnt/ssd/gestionprojet-mysql` au préalable). Ce n'est pas
nécessaire pour un premier déploiement de test, mais recommandé pour un
usage prolongé.

## Dépannage

- **Logs d'un service** : `docker compose logs -f backend` (remplacer
  `backend` par `frontend` ou `mysql`).
- **Un conteneur ne démarre pas** : `docker compose ps` pour voir l'état,
  puis `docker compose logs <service>` pour la raison exacte.
- **`docker compose up` échoue en signalant une variable manquante** (ex.
  `required variable CLOUDFLARE_ACCESS_AUD is missing a value`) : le fichier
  `.env` est absent ou incomplet — revoir l'étape 2 (et l'étape 6 si ce sont
  les variables Cloudflare Access qui manquent).
- **`403`/écran Cloudflare bloquant même les comptes autorisés** : vérifier
  la politique **Allow** de l'application Access (étape 6) — l'adresse ou le
  domaine e-mail utilisé doit y figurer exactement.
- **L'application affiche « Authentification requise » alors que Cloudflare
  a bien laissé passer la connexion** : `CLOUDFLARE_TEAM_DOMAIN` ou
  `CLOUDFLARE_ACCESS_AUD` dans `.env` ne correspondent pas à l'application
  Access réellement configurée — revoir l'étape 6, puis
  `docker compose up -d --build backend`.
- **Un hostname dans `CORS_ORIGINS`, dans `config.yml` de `cloudflared` et
  dans l'application Access qui ne correspondent pas exactement** (schéma
  `https://` inclus dans `CORS_ORIGINS`, sans slash final) empêche
  l'application de fonctionner correctement même si le tunnel répond.
- **Le job `deploy` reste bloqué en "queued" dans Actions** : le runner
  self-hosted n'est pas démarré ou n'est pas connecté — sur le Pi,
  `sudo ./svc.sh status` dans le dossier du runner (voir étape 7).
- **Le job `deploy` échoue sur `required variable ... is missing a
  value`** : le `.env` du dossier de travail du runner n'a pas été créé ou
  est incomplet (c'est un fichier différent de celui utilisé lors d'un
  déploiement manuel précédent) — revoir le point 4 de l'étape 7.
- **Repartir de zéro sans perdre les données** : `docker compose down` puis
  `docker compose up -d --build` (le volume `mysql_data` n'est pas supprimé
  par `down` sans l'option `-v`). Ne jamais lancer `docker compose down -v`
  sans une sauvegarde récente : `-v` supprime aussi le volume de données.

## Rappel de sécurité

L'authentification repose entièrement sur Cloudflare Access (étape 6) : sans
application Access correctement configurée avec une politique **Allow**
restrictive, l'application est accessible à quiconque connaît l'URL
publique. Ne jamais considérer le déploiement comme terminé avant d'avoir
vérifié l'étape 6 (fenêtre de navigation privée → écran de connexion
Google → politique appliquée).

`DEV_BYPASS_AUTH_ENABLED` (variable backend, absente de la configuration
Docker Compose fournie) permet de contourner Cloudflare Access en local pour
le développement, via un en-tête `X-Dev-Email` non vérifié. Elle ne doit
**jamais** être positionnée à `true` dans `.env` en production — sa simple
présence désactiverait toute vérification d'identité pour l'application
exposée publiquement.
