# simo-homesi-ops

Salesforce, n8n, Customer.io and BigQuery ops for Homesi & Simo Solutions Group.

Repositorio de operaciones: metadata de Salesforce, workflows de n8n y la documentación que
antes vivía en el Claude Project "Salesforce". Está preparado para trabajar con Claude Code.

> **Repositorio privado.** `docs/handover/` contiene identidades, números de cuenta y
> debilidades de seguridad conocidas.

---

## Estructura

```
CLAUDE.md              contexto que Claude Code carga en cada sesión (corto a propósito)
docs/INDEX.md          qué documento es dueño de cada verdad — empieza aquí
docs/                  toda la documentación de referencia
salesforce/            proyecto SFDX (los comandos sf se corren desde aquí)
n8n/                   exportaciones JSON de workflows + script de exportación
data/                  archivos de trabajo locales — ignorado por git (puede tener PII)
.claude/settings.json  permisos y hook de protección de producción
.claude/hooks/         guard.py — bloquea o pide confirmación según docs/CHANGE_POLICY.md
.claude/managed/       managed settings de referencia (reglas para toda la organización)
.github/               plantilla de PR, CODEOWNERS, CI
.claude/commands/      /sync-docs, /prod-preflight y /ship
.claude/skills/        skills del proyecto (ver README interno)
.mcp.json              servidores MCP (sin secretos, usa variables)
.env.example           nombres de variables; copia a .env y llénalo
```

---

## Puesta en marcha (una vez por máquina)

**1. Requisitos:** Git, Python 3, [Salesforce CLI](https://developer.salesforce.com/tools/salesforcecli)
(`sf`), [Claude Code](https://docs.claude.com/en/docs/claude-code/overview), y opcionalmente
[direnv](https://direnv.net/) y [pre-commit](https://pre-commit.com/).

**2. Secretos:**
```bash
cp .env.example .env      # llénalo; nunca se sube a git
direnv allow              # si usas direnv: carga .env al entrar a la carpeta
```
Sin direnv, carga las variables en la terminal **antes** de abrir Claude Code
(Claude Code no lee `.env` por sí solo):
```bash
set -a; source .env; set +a
claude
```

**3. Salesforce CLI** (la autenticación queda fuera del repo):
```bash
sf org login web --alias prod
sf org login web --alias homesi-staging --instance-url https://test.salesforce.com
sf org list
```

**4. Protección de commits:**
```bash
pip install pre-commit
pre-commit install       # instala los hooks pre-commit y pre-push
pre-commit autoupdate     # actualiza las versiones fijadas
```

**5. Servidores MCP:** abre `claude` en la raíz del repo, aprueba los servidores del proyecto y
ejecuta `/mcp` para autenticar los que usan OAuth (Salesforce, Customer.io). Luego en cada
servidor de Salesforce corre `getUserInfo`: el que devuelve `companyName: "Homesi"` es prod.

---

## Primeras tareas después de clonar

1. **Traer la metadata de Salesforce.** Lo ideal es copiar el árbol SFDX de la carpeta
   `Salesforce Workspace` del administrador saliente dentro de `salesforce/`, **excepto**:
   los CSV/XLSX de leads (PII), `.sf/`, `.sfdx/` y las carpetas de despliegue parcial
   (`furprod/w1…w18` y similares). Reemplaza también `sfdx-project.json` y `.forceignore`
   por los originales. Si no hay acceso a esa carpeta, recupera desde prod:
   ```bash
   cd salesforce
   sf project retrieve start --metadata ApexClass ApexTrigger Flow CustomObject \
     FlexiPage Layout LightningComponentBundle --target-org prod
   ```
2. **Exportar los workflows de n8n:** `python3 n8n/scripts/export_workflows.py`
3. **Reemplazar las dos referencias grandes** por las copias más nuevas del laptop
   (ver "Known stale content" en `docs/INDEX.md`).
4. **Copiar las skills** a `.claude/skills/` (ver `.claude/skills/README.md`).
5. Commit por partes: primero docs y configuración, luego metadata, luego workflows.

---

## Cómo protege producción

La política completa (qué camino sigue un cambio a cada sistema y qué está prohibido) está en
[`docs/CHANGE_POLICY.md`](docs/CHANGE_POLICY.md). Resumen:

- **Nunca directo a `main`.** Rama `area/descripcion` → PR → merge (`/ship` lo hace). Lo
  bloquean el hook, pre-commit (commit y push) y el ruleset `protect-main` de GitHub.
- **`guard.py`** (hook PreToolUse) **bloquea**: commit/push a `main`, force push, deploys
  locales de Lambdas (`serverless`, `sam`, `cdk`, `aws lambda update-function-*`) y deploys
  de Salesforce a prod que no salgan de `main` limpio y actualizado. **Pide confirmación**
  ante: escrituras `sf` a prod o sin `--target-org`, escrituras MCP a Salesforce prod, n8n,
  Customer.io, Make o BigQuery, escrituras de AWS, lectura de secretos y cualquier cosa que
  toque `fur_settings` / `Test_Mode__c`. Si no encuentra Python, pide confirmación en todo
  (falla cerrado). Tests: `python .claude/hooks/test_guard.py`.
- **Permisos** en `.claude/settings.json`: Claude no puede leer `.env`, ni mostrar variables
  de entorno, ni hacer `git push --force`. Deploys, escrituras de datos y `git push` piden
  confirmación.
- **`.gitignore`** excluye secretos, `data/`, y todo CSV, XLSX y PDF.
- **gitleaks** en pre-commit bloquea commits con algo con forma de clave.

> `guard.sh` busca `python3`, `python` o `py -3`, así que funciona en Windows sin cambios.

## Reglas de oro

- Si un secreto llega a un commit, **se rota**. Borrarlo del historial no basta.
- Nada de PII de prestatarios en el repo: usa Ids de registro.
- Después de cambiar un sistema en vivo, actualiza el documento dueño en la misma sesión
  (`/sync-docs` ayuda).
