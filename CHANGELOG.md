# Changelog

## [1.1.0](https://github.com/vidal-dorian/GestionProjet-IUT/compare/v1.0.0...v1.1.0) (2026-08-14)


### Features

* US-35 — appartenir à plusieurs projets ([4a7583a](https://github.com/vidal-dorian/GestionProjet-IUT/commit/4a7583af715a13d2113cc35e50405b80b6056141))
* US-36 — distinguer les rôles sur un projet ([793d0f4](https://github.com/vidal-dorian/GestionProjet-IUT/commit/793d0f458e38fc183c866ef8cf0996b607a47434))
* US-39 — refonte de l'interface graphique ([7f36052](https://github.com/vidal-dorian/GestionProjet-IUT/commit/7f36052683fb98239d83977f0955dcea3dcd83f3))
* US-39 — refonte de l'UX et de la navigation ([1ffcd4c](https://github.com/vidal-dorian/GestionProjet-IUT/commit/1ffcd4c279ca5795fddabe421889ff8e2db452fa))
* US-40 — imposer l'appartenance à un projet et retrait de membre par un admin ([a4ebec4](https://github.com/vidal-dorian/GestionProjet-IUT/commit/a4ebec42049e29830fa715f8c22ef734447941a1))
* US-42 — faire valider mon adhésion à un projet par un administrateur ([09ff47f](https://github.com/vidal-dorian/GestionProjet-IUT/commit/09ff47f63c1661a3b7010e959893665b9201e1b4))
* US-43 — rôles d'équipe par projet, assignables par sprint ([05c76e6](https://github.com/vidal-dorian/GestionProjet-IUT/commit/05c76e676cb44ce926c3f2131c53d8096c6dd303))

## [1.0.0](https://github.com/vidal-dorian/GestionProjet-IUT/compare/v0.2.0...v1.0.0) (2026-08-13)


### ⚠ BREAKING CHANGES

* remplace entièrement le système de membres avec PIN à 4 chiffres (US-05, US-08) par une authentification déléguée à Cloudflare Access, avec Google comme fournisseur d'identité.

### Features

* déploiement continu (CI/CD) sur le Raspberry Pi ([dd7f400](https://github.com/vidal-dorian/GestionProjet-IUT/commit/dd7f40025ca56f253dbf86d0c2cc6b9ea1848962))
* déploiement continu (CI/CD) sur le Raspberry Pi ([8736867](https://github.com/vidal-dorian/GestionProjet-IUT/commit/87368675ff73ecf40312191cf5417261ec405d79))
* Epic 8 — sprints (US-26, US-27, US-28) ([d6d668f](https://github.com/vidal-dorian/GestionProjet-IUT/commit/d6d668fdee35817f887cd14335a2e2793893876e))
* US-21 — lier un dépôt GitHub à un projet ([9b8dbc1](https://github.com/vidal-dorian/GestionProjet-IUT/commit/9b8dbc1785e20e397ebb18a3dddcf2eb0201ffa4))
* US-22 — synchroniser les issues GitHub ([9def9d7](https://github.com/vidal-dorian/GestionProjet-IUT/commit/9def9d7e400e6609466272b902799721b2209d87))
* US-23 — filtrer les issues GitHub remontées par label ([6d35548](https://github.com/vidal-dorian/GestionProjet-IUT/commit/6d35548e771d4c504babe51be69cfc6cdfcbf9b9))
* US-24 — pointer une saisie de temps sur une issue GitHub ([1cd2b79](https://github.com/vidal-dorian/GestionProjet-IUT/commit/1cd2b791b6402c28acffbf937a455e85057080dc))
* US-25 — visualiser les heures par User Story ([1ff4208](https://github.com/vidal-dorian/GestionProjet-IUT/commit/1ff420800b6fdc1e17c7ae41b348dfe75ffd40cc))
* US-30, US-31 — exporter les données en Excel ([d1ed237](https://github.com/vidal-dorian/GestionProjet-IUT/commit/d1ed237f8b73338c75c58cb0102f41843b64df75))
* US-37 — catégoriser mes saisies ([9cec8c3](https://github.com/vidal-dorian/GestionProjet-IUT/commit/9cec8c3cc2654fa6c728da57c035c9f21da243b2))
* US-41 — authentification via Google (Cloudflare Access) ([b367f56](https://github.com/vidal-dorian/GestionProjet-IUT/commit/b367f567b1c3381322c2c6ab88a235e0507163dc))


### Bug Fixes

* limiter la fréquence de synchronisation manuelle des issues GitHub ([c32095a](https://github.com/vidal-dorian/GestionProjet-IUT/commit/c32095a5454410c737ed42829bca094a576047fc))

## [0.2.0](https://github.com/vidal-dorian/GestionProjet-IUT/compare/v0.1.0...v0.2.0) (2026-08-13)


### Features

* complète le déploiement Docker et documente le déploiement Raspberry Pi ([bc60eac](https://github.com/vidal-dorian/GestionProjet-IUT/commit/bc60eac80e1294bf4b65d7a82fa0613b702b58d7))
* US-04 et US-07 — supprimer un projet et retirer un membre ([0d63397](https://github.com/vidal-dorian/GestionProjet-IUT/commit/0d633979b756f414c53118b864099c1ebf7f6fce))
