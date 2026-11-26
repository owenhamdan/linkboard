# Linkboard

A link shortener with click analytics. Paste a long URL, get a short slug, and see how many people clicked it, on which days and from which sites.

Assignment 2 splits the monolith into two services, each in its own folder with its own database:
* **links** (`services/links/`): create, look up, list and delete short links, and redirect `/<slug>`
* **analytics** (`services/analytics/`): record clicks and report stats per slug

The links service calls analytics over HTTP (`ANALYTICS_URL`) when a link is followed or deleted. Every call has a timeout; if analytics is down, redirects still work and the click is simply not counted.

The UI is a static page in `ui/` that calls both services from the browser. Their URLs come from `ui/config.js`.

## Diagrams

Mermaid sources and rendered images in `docs/diagrams/`: the Assignment 1 monolith (`before`), the split system (`after`), the deployment (`deployment`) and one database diagram per service (`db-links`, `db-analytics`).

## Running locally with Docker

```
docker compose up --build
```

SQL Server starts in a container first, then `db-init` runs `db/init.sql` to create one database and one login per service, then both services apply their migrations on startup. On Apple Silicon, turn on Rosetta emulation in Docker Desktop.

UI: http://localhost:8080, links: http://localhost:8001, analytics: http://localhost:8002

## Running a single service

```
cd services/links          # or services/analytics
pip install -r requirements.txt -r requirements-dev.txt
docker compose up -d db db-init     # a SQL Server to talk to
DATABASE_URL=mssql://links_user:LocalDev_links_123@localhost:1433/links \
  PORT=8001 ANALYTICS_URL=http://localhost:8002 python app.py
```

## Database migrations

Each service keeps its SQL Server schema in `services/<name>/migrations/` as numbered SQL files (`001_init.sql`, `002_...`). On startup `migrate.py` applies any file not yet listed in the `schema_migrations` table, in order, and logs `applying migration <file>`. Applied files are never edited; a change goes in a new numbered file.

## System description

`system.yaml` describes both services, their environment variables, the calls between them and their Azure resources, in the format of `system.schema.json` (provided by the course, unchanged). Each service has an `openapi.yaml`. CI checks all three:

* `check-jsonschema` validates `system.yaml` against the schema
* `openapi-spec-validator` validates both OpenAPI documents
* `tools/check_system.py` checks `system.yaml` against the code: every environment variable read in the code is listed, every endpoint one service calls exists in the other's OpenAPI document
* `tests/test_openapi.py` in each service checks the OpenAPI paths against the app's real routes

## Tests and coverage

```
docker compose up -d db db-init     # tests need SQL Server
cd services/links && python -m pytest --cov=. --cov-report=term
cd services/analytics && python -m pytest --cov=. --cov-report=term
```


## Deployment

Live URL: https://ohamdanieu2023ui.z28.web.core.windows.net

Every push to `main` runs `.github/workflows/cd.yml`:

1. CI (`ci.yml`, called through `workflow_call`): lint, tests against SQL Server with the 70% coverage gate, image builds, `system.yaml` and OpenAPI validation
2. Both images are pushed to GHCR as `ghcr.io/owenhamdan/linkboard-<service>:<commit sha>`
3. The workflow signs in to Azure as the managed identity `ohamdan-ieu2023-github` through OpenID Connect (no Azure password is stored anywhere)
4. Each Container App gets its new image, its database URL as a Container Apps secret, and its other settings as environment variables
5. `ui/config.js` is generated with the two service URLs and `ui/` is uploaded to the `$web` container of the storage account
6. The run fails unless both `/health` endpoints return 200 on the new commit within about five minutes

Changes reach `main` only through pull requests, so CI runs on the branch before CD runs on `main`.

### Initial Azure setup (done once, by hand, in Azure Cloud Shell Bash)

Everything after this is changed only by the pipeline. Passwords are generated in the shell and go straight into GitHub secrets; they are never written down.

```bash
# 1. Subscription and region
az login --use-device-code                      # pick "Azure for Students"
az policy assignment list --query "[?displayName=='Allowed resource deployment regions'].parameters.listOfAllowedLocations.value" -o json
# allowed: belgiumcentral, polandcentral, francecentral, switzerlandnorth, austriaeast -> francecentral

# 2. Providers and resource group
PREFIX=ohamdan-ieu2023; RG=rg-$PREFIX; LOC=francecentral; UI=ohamdanieu2023ui; SQL=$PREFIX-sql; ENV=$PREFIX-env
for p in Microsoft.App Microsoft.OperationalInsights Microsoft.Sql Microsoft.Storage Microsoft.ManagedIdentity; do az provider register --namespace $p; done
az group create -n $RG -l $LOC

# 3. Storage static website for the UI
az storage account create -n $UI -g $RG -l $LOC --sku Standard_LRS --kind StorageV2
az storage blob service-properties update --account-name $UI --static-website --index-document index.html

# 4. SQL server, two serverless free offer databases, one contained user per database
set +H
ADMIN_PW='Aa1!'$(openssl rand -hex 16); LINKS_PW='Aa1!'$(openssl rand -hex 16); ANALYTICS_PW='Aa1!'$(openssl rand -hex 16)
az sql server create -n $SQL -g $RG -l $LOC --admin-user sqladmin --admin-password "$ADMIN_PW"
az sql server firewall-rule create -g $RG -s $SQL -n AllowAzureServices --start-ip-address 0.0.0.0 --end-ip-address 0.0.0.0
for s in links analytics; do
  az sql db create -g $RG -s $SQL -n $PREFIX-$s-db -e GeneralPurpose -f Gen5 --compute-model Serverless \
    --min-capacity 0.5 -c 1 --backup-storage-redundancy Local --use-free-limit true --free-limit-exhaustion-behavior AutoPause
done
MYIP=$(curl -s https://api.ipify.org)
az sql server firewall-rule create -g $RG -s $SQL -n setup-ip --start-ip-address $MYIP --end-ip-address $MYIP
for s in links analytics; do
  PW=$([ $s = links ] && echo $LINKS_PW || echo $ANALYTICS_PW)
  sqlcmd -S $SQL.database.windows.net -d $PREFIX-$s-db -U sqladmin -P "$ADMIN_PW" -Q "CREATE USER ${s}_user WITH PASSWORD = '$PW'; ALTER ROLE db_ddladmin ADD MEMBER ${s}_user; ALTER ROLE db_datareader ADD MEMBER ${s}_user; ALTER ROLE db_datawriter ADD MEMBER ${s}_user;"
done
az sql server firewall-rule delete -g $RG -s $SQL -n setup-ip

# 5. Container Apps environment (Azure also creates its Log Analytics workspace) and two apps on a placeholder image
az containerapp env create -n $ENV -g $RG -l $LOC
for s in analytics links; do
  az containerapp create -n $PREFIX-$s -g $RG --environment $ENV --image mcr.microsoft.com/k8se/quickstart:latest \
    --ingress external --target-port 80 --min-replicas 0 --max-replicas 1 --cpu 0.25 --memory 0.5Gi
done

# 6. The pipeline's identity: Contributor on the resource group only, trusted only for main of this repo
az identity create -n $PREFIX-github -g $RG -l $LOC
CLIENT_ID=$(az identity show -n $PREFIX-github -g $RG --query clientId -o tsv)
PRINCIPAL_ID=$(az identity show -n $PREFIX-github -g $RG --query principalId -o tsv)
RG_ID=$(az group show -n $RG --query id -o tsv)
az role assignment create --assignee-object-id $PRINCIPAL_ID --assignee-principal-type ServicePrincipal --role Contributor --scope $RG_ID
az identity federated-credential create --name github-main --identity-name $PREFIX-github -g $RG \
  --issuer https://token.actions.githubusercontent.com --subject "repo:owenhamdan/linkboard:ref:refs/heads/main" --audiences api://AzureADTokenExchange
az identity federated-credential create --name github-main-ids --identity-name $PREFIX-github -g $RG \
  --issuer https://token.actions.githubusercontent.com --subject "repo:owenhamdan@73236480/linkboard@1404852395:ref:refs/heads/main" --audiences api://AzureADTokenExchange

# 7. GitHub secrets and variables
gh auth login -h github.com -p https -w
R=owenhamdan/linkboard
gh secret set AZURE_CLIENT_ID -R $R --body "$CLIENT_ID"
gh secret set AZURE_TENANT_ID -R $R --body "$(az account show --query tenantId -o tsv)"
gh secret set AZURE_SUBSCRIPTION_ID -R $R --body "$(az account show --query id -o tsv)"
gh secret set LINKS_DB_PASSWORD -R $R --body "$LINKS_PW"
gh secret set ANALYTICS_DB_PASSWORD -R $R --body "$ANALYTICS_PW"
gh variable set PREFIX -R $R --body "$PREFIX"
gh variable set RESOURCE_GROUP -R $R --body "$RG"
gh variable set UI_STORAGE -R $R --body "$UI"

# 8. Read access for the professors
for p in amartini@faculty.ie.edu bserra@faculty.ie.edu; do az role assignment create --assignee $p --role Reader --scope $RG_ID; done
```

The GHCR packages (`linkboard-links`, `linkboard-analytics`) take the visibility of this public repository, so Container Apps can pull them without registry credentials.
