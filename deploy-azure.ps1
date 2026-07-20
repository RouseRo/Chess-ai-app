# Chess AI App - Azure Container Apps Deployment Script
# Run from the repo root: .\deploy-azure.ps1
# Prerequisites: az CLI logged in, Docker running

$ErrorActionPreference = "Stop"
$env:PATH = [System.Environment]::GetEnvironmentVariable("PATH","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH","User")

# ── Configuration ──────────────────────────────────────────────────────────────
$RG         = "chess-ai-rg"
$LOCATION   = "eastus"
$ACR        = "chessairegistry7646"
$STORAGE    = "chessaistorage4996"
$ENV_NAME   = "chess-ai-env"
$DATA_SHARE = "chessdata"
$USER_SHARE = "chessuserdata"
$JWT_SECRET = "chess-ai-jwt-secret-change-me-in-prod"
# ───────────────────────────────────────────────────────────────────────────────

Write-Host "=== Chess AI App - Azure Deployment ===" -ForegroundColor Cyan
Write-Host "Resource Group : $RG"
Write-Host "Location       : $LOCATION"
Write-Host "ACR            : $ACR"
Write-Host "Storage        : $STORAGE"
Write-Host "Environment    : $ENV_NAME"
Write-Host ""

# ── Step 0: Register required resource providers ────────────────────────────
Write-Host "[0/8] Registering Azure resource providers (may take 1-2 min)..." -ForegroundColor Yellow
$providers = @(
    "Microsoft.ContainerRegistry",
    "Microsoft.Storage",
    "Microsoft.App",
    "Microsoft.OperationalInsights",
    "Microsoft.ContainerService"
)
foreach ($p in $providers) {
    Write-Host "  Registering $p..."
    az provider register --namespace $p --wait
}
Write-Host "All providers registered." -ForegroundColor Green
Write-Host ""

# ── Step 1: Resource Group ──────────────────────────────────────────────────
Write-Host "[1/8] Creating resource group..." -ForegroundColor Yellow
az group create --name $RG --location $LOCATION --output table
Write-Host ""

# ── Step 2: Azure Container Registry ───────────────────────────────────────
Write-Host "[2/8] Creating Azure Container Registry..." -ForegroundColor Yellow
az acr create --resource-group $RG --name $ACR --sku Basic --admin-enabled true --output table
Write-Host ""

# ── Step 3: Storage Account + Azure Files shares ───────────────────────────
Write-Host "[3/8] Creating storage account and file shares..." -ForegroundColor Yellow
az storage account create --name $STORAGE --resource-group $RG --location $LOCATION --sku Standard_LRS --output table
$STORAGE_KEY = az storage account keys list --account-name $STORAGE --resource-group $RG --query "[0].value" --output tsv
az storage share create --name $DATA_SHARE --account-name $STORAGE --account-key $STORAGE_KEY --output table
az storage share create --name $USER_SHARE --account-name $STORAGE --account-key $STORAGE_KEY --output table
Write-Host ""

# ── Step 4: Container Apps Environment ─────────────────────────────────────
Write-Host "[4/8] Installing containerapp extension and creating environment..." -ForegroundColor Yellow
az extension add --name containerapp --upgrade --only-show-errors
az containerapp env create --name $ENV_NAME --resource-group $RG --location $LOCATION --output table
Write-Host ""

# ── Step 5: Link Azure Files to the environment ─────────────────────────────
Write-Host "[5/8] Linking Azure Files storage to environment..." -ForegroundColor Yellow
az containerapp env storage set `
  --name $ENV_NAME --resource-group $RG `
  --storage-name $DATA_SHARE `
  --azure-file-account-name $STORAGE `
  --azure-file-account-key $STORAGE_KEY `
  --azure-file-share-name $DATA_SHARE `
  --access-mode ReadWrite
az containerapp env storage set `
  --name $ENV_NAME --resource-group $RG `
  --storage-name $USER_SHARE `
  --azure-file-account-name $STORAGE `
  --azure-file-account-key $STORAGE_KEY `
  --azure-file-share-name $USER_SHARE `
  --access-mode ReadWrite
Write-Host ""

# ── Step 6: Build & push images ─────────────────────────────────────────────
Write-Host "[6/8] Building and pushing Docker images to ACR..." -ForegroundColor Yellow
$ACR_SERVER = "$ACR.azurecr.io"
az acr login --name $ACR
Set-Location $PSScriptRoot
az acr build --registry $ACR --image chess-engine:latest --file engine/Dockerfile     .
az acr build --registry $ACR --image chess-auth:latest   --file auth-service/Dockerfile .
az acr build --registry $ACR --image chess-admin:latest  --file admin-service/Dockerfile .
az acr build --registry $ACR --image chess-ui:latest     --file ui/Dockerfile         ui/
Write-Host ""

# ── Step 7: Get ACR credentials ─────────────────────────────────────────────
Write-Host "[7/8] Fetching ACR credentials..." -ForegroundColor Yellow
$ACR_USER = az acr credential show --name $ACR --query username --output tsv
$ACR_PASS = az acr credential show --name $ACR --query "passwords[0].value" --output tsv
Write-Host ""

# ── Step 8: Deploy Container Apps (YAML) ────────────────────────────────────
Write-Host "[8/8] Deploying Container Apps..." -ForegroundColor Yellow

# Helper: write YAML (no BOM) to temp file and deploy
function Deploy-App($name, $yaml) {
    $file = "$env:TEMP\$name.yaml"
    # Use no-BOM UTF-8 — PowerShell's Set-Content -Encoding UTF8 adds BOM on PS5
    [System.IO.File]::WriteAllText($file, $yaml, (New-Object System.Text.UTF8Encoding $false))
    Write-Host "  Deploying $name..." -ForegroundColor White
    az containerapp create --name $name --resource-group $RG --yaml $file --output table
}

# -- Auth Service (internal) --
Deploy-App "chess-auth" @"
location: $LOCATION
type: Microsoft.App/containerApps
kind: containerapp
properties:
  managedEnvironmentId: /subscriptions/b2dbdeb1-b560-47fa-b29e-07339ad9160d/resourceGroups/$RG/providers/Microsoft.App/managedEnvironments/$ENV_NAME
  configuration:
    registries:
      - server: $ACR_SERVER
        username: $ACR_USER
        passwordSecretRef: regpassword
    secrets:
      - name: regpassword
        value: $ACR_PASS
    ingress:
      external: false
      targetPort: 8002
      transport: http
  template:
    containers:
      - name: chess-auth
        image: $ACR_SERVER/chess-auth:latest
        resources:
          cpu: 0.25
          memory: 0.5Gi
        env:
          - name: JWT_SECRET_KEY
            value: $JWT_SECRET
          - name: CHESS_DEV_MODE
            value: "false"
        volumeMounts:
          - volumeName: $DATA_SHARE
            mountPath: /app/data
    volumes:
      - name: $DATA_SHARE
        storageType: AzureFile
        storageName: $DATA_SHARE
    scale:
      minReplicas: 1
      maxReplicas: 1
"@

# -- Admin Service (internal) --
Deploy-App "chess-admin" @"
location: $LOCATION
type: Microsoft.App/containerApps
kind: containerapp
properties:
  managedEnvironmentId: /subscriptions/b2dbdeb1-b560-47fa-b29e-07339ad9160d/resourceGroups/$RG/providers/Microsoft.App/managedEnvironments/$ENV_NAME
  configuration:
    registries:
      - server: $ACR_SERVER
        username: $ACR_USER
        passwordSecretRef: regpassword
    secrets:
      - name: regpassword
        value: $ACR_PASS
    ingress:
      external: false
      targetPort: 8001
      transport: http
  template:
    containers:
      - name: chess-admin
        image: $ACR_SERVER/chess-admin:latest
        resources:
          cpu: 0.25
          memory: 0.5Gi
        volumeMounts:
          - volumeName: $DATA_SHARE
            mountPath: /app/data
          - volumeName: $USER_SHARE
            mountPath: /app/user_data
    volumes:
      - name: $DATA_SHARE
        storageType: AzureFile
        storageName: $DATA_SHARE
      - name: $USER_SHARE
        storageType: AzureFile
        storageName: $USER_SHARE
    scale:
      minReplicas: 1
      maxReplicas: 1
"@

# -- Chess Engine (internal) --
Deploy-App "chess-engine" @"
location: $LOCATION
type: Microsoft.App/containerApps
kind: containerapp
properties:
  managedEnvironmentId: /subscriptions/b2dbdeb1-b560-47fa-b29e-07339ad9160d/resourceGroups/$RG/providers/Microsoft.App/managedEnvironments/$ENV_NAME
  configuration:
    registries:
      - server: $ACR_SERVER
        username: $ACR_USER
        passwordSecretRef: regpassword
    secrets:
      - name: regpassword
        value: $ACR_PASS
    ingress:
      external: false
      targetPort: 8000
      transport: http
  template:
    containers:
      - name: chess-engine
        image: $ACR_SERVER/chess-engine:latest
        resources:
          cpu: 0.5
          memory: 1.0Gi
        env:
          - name: JWT_SECRET_KEY
            value: $JWT_SECRET
          - name: AUTH_SERVICE_URL
            value: http://chess-auth
        volumeMounts:
          - volumeName: $USER_SHARE
            mountPath: /app/user_data
    volumes:
      - name: $USER_SHARE
        storageType: AzureFile
        storageName: $USER_SHARE
    scale:
      minReplicas: 1
      maxReplicas: 1
"@

# -- Chess UI (external / public) --
Deploy-App "chess-ui" @"
location: $LOCATION
type: Microsoft.App/containerApps
kind: containerapp
properties:
  managedEnvironmentId: /subscriptions/b2dbdeb1-b560-47fa-b29e-07339ad9160d/resourceGroups/$RG/providers/Microsoft.App/managedEnvironments/$ENV_NAME
  configuration:
    registries:
      - server: $ACR_SERVER
        username: $ACR_USER
        passwordSecretRef: regpassword
    secrets:
      - name: regpassword
        value: $ACR_PASS
    ingress:
      external: true
      targetPort: 80
      transport: http
  template:
    containers:
      - name: chess-ui
        image: $ACR_SERVER/chess-ui:latest
        resources:
          cpu: 0.25
          memory: 0.5Gi
    scale:
      minReplicas: 1
      maxReplicas: 2
"@

# ── Done ────────────────────────────────────────────────────────────────────
Write-Host "`n=== Deployment Complete! ===" -ForegroundColor Green
Write-Host "`nPublic URL (Chess UI):" -ForegroundColor Cyan
az containerapp show --name chess-ui --resource-group $RG --query "properties.configuration.ingress.fqdn" --output tsv
Write-Host "`nVisit https://<above-url> to play chess!" -ForegroundColor Cyan


$ErrorActionPreference = "Stop"

# ── Configuration ──────────────────────────────────────────────────────────────
$RG       = "chess-ai-rg"
$LOCATION = "eastus"
$ACR      = "chessairegistry7646"
$STORAGE  = "chessaistorage4996"
$ENV      = "chess-ai-env"
$SHARE    = "chessdata"
$SUB_ID   = "b2dbdeb1-b560-47fa-b29e-07339ad9160d"
# ───────────────────────────────────────────────────────────────────────────────

Write-Host "=== Chess AI App - Azure Deployment ===" -ForegroundColor Cyan
Write-Host "Resource Group : $RG"
Write-Host "Location       : $LOCATION"
Write-Host "ACR            : $ACR"
Write-Host "Storage Acct   : $STORAGE"
Write-Host "CA Environment : $ENV"
Write-Host ""

# Step 1: Resource Group
Write-Host "[1/8] Creating resource group..." -ForegroundColor Yellow
az group create --name $RG --location $LOCATION --output table
Write-Host "Done." -ForegroundColor Green

# Step 2: Azure Container Registry
Write-Host "[2/8] Creating Azure Container Registry..." -ForegroundColor Yellow
az acr create --resource-group $RG --name $ACR --sku Basic --admin-enabled true --output table
Write-Host "Done." -ForegroundColor Green

# Step 3: Storage Account + Azure Files share (for shared SQLite DB volume)
Write-Host "[3/8] Creating storage account and file share..." -ForegroundColor Yellow
az storage account create --name $STORAGE --resource-group $RG --location $LOCATION --sku Standard_LRS --output table
$STORAGE_KEY = az storage account keys list --account-name $STORAGE --resource-group $RG --query "[0].value" --output tsv
az storage share create --name $SHARE --account-name $STORAGE --account-key $STORAGE_KEY --output table
# Second share for user_data
az storage share create --name "chessuserdata" --account-name $STORAGE --account-key $STORAGE_KEY --output table
Write-Host "Done." -ForegroundColor Green

# Step 4: Install containerapp extension + create environment
Write-Host "[4/8] Installing containerapp extension and creating environment..." -ForegroundColor Yellow
az extension add --name containerapp --upgrade --only-show-errors
az provider register --namespace Microsoft.App --wait
az provider register --namespace Microsoft.OperationalInsights --wait
az containerapp env create --name $ENV --resource-group $RG --location $LOCATION --output table
Write-Host "Done." -ForegroundColor Green

# Step 5: Mount Azure Files storage to the environment
Write-Host "[5/8] Linking Azure Files to Container Apps environment..." -ForegroundColor Yellow
az containerapp env storage set `
  --name $ENV --resource-group $RG `
  --storage-name chessdata `
  --azure-file-account-name $STORAGE `
  --azure-file-account-key $STORAGE_KEY `
  --azure-file-share-name $SHARE `
  --access-mode ReadWrite `
  --output table

az containerapp env storage set `
  --name $ENV --resource-group $RG `
  --storage-name chessuserdata `
  --azure-file-account-name $STORAGE `
  --azure-file-account-key $STORAGE_KEY `
  --azure-file-share-name chessuserdata `
  --access-mode ReadWrite `
  --output table
Write-Host "Done." -ForegroundColor Green

# Step 6: Build and push images to ACR
Write-Host "[6/8] Building and pushing Docker images to ACR..." -ForegroundColor Yellow
az acr login --name $ACR

# Build all 4 images
az acr build --registry $ACR --image chess-engine:latest    --file engine/Dockerfile      . --output table
az acr build --registry $ACR --image chess-auth:latest      --file auth-service/Dockerfile . --output table
az acr build --registry $ACR --image chess-admin:latest     --file admin-service/Dockerfile . --output table
az acr build --registry $ACR --image chess-ui:latest        --file ui/Dockerfile           ui/ --output table
Write-Host "Done." -ForegroundColor Green

# Step 7: Get ACR credentials
Write-Host "[7/8] Fetching ACR credentials..." -ForegroundColor Yellow
$ACR_SERVER   = "$ACR.azurecr.io"
$ACR_USERNAME = az acr credential show --name $ACR --query username --output tsv
$ACR_PASSWORD = az acr credential show --name $ACR --query "passwords[0].value" --output tsv
Write-Host "Done." -ForegroundColor Green

# Step 8: Deploy Container Apps
Write-Host "[8/8] Deploying Container Apps..." -ForegroundColor Yellow

# -- Auth Service (internal only) --
az containerapp create `
  --name chess-auth `
  --resource-group $RG `
  --environment $ENV `
  --image "$ACR_SERVER/chess-auth:latest" `
  --registry-server $ACR_SERVER `
  --registry-username $ACR_USERNAME `
  --registry-password $ACR_PASSWORD `
  --target-port 8002 `
  --ingress internal `
  --cpu 0.25 --memory 0.5Gi `
  --min-replicas 1 --max-replicas 1 `
  --env-vars "JWT_SECRET_KEY=chess-ai-jwt-secret-change-me" "CHESS_DEV_MODE=false" `
  --volume-mount-path "/app/data" `
  --mount-volume-name chessdata `
  --output table

# -- Admin Service (internal only) --
az containerapp create `
  --name chess-admin `
  --resource-group $RG `
  --environment $ENV `
  --image "$ACR_SERVER/chess-admin:latest" `
  --registry-server $ACR_SERVER `
  --registry-username $ACR_USERNAME `
  --registry-password $ACR_PASSWORD `
  --target-port 8001 `
  --ingress internal `
  --cpu 0.25 --memory 0.5Gi `
  --min-replicas 1 --max-replicas 1 `
  --volume-mount-path "/app/data" `
  --mount-volume-name chessdata `
  --output table

# -- Engine (internal only) --
az containerapp create `
  --name chess-engine `
  --resource-group $RG `
  --environment $ENV `
  --image "$ACR_SERVER/chess-engine:latest" `
  --registry-server $ACR_SERVER `
  --registry-username $ACR_USERNAME `
  --registry-password $ACR_PASSWORD `
  --target-port 8000 `
  --ingress internal `
  --cpu 0.5 --memory 1.0Gi `
  --min-replicas 1 --max-replicas 1 `
  --env-vars "JWT_SECRET_KEY=chess-ai-jwt-secret-change-me" "AUTH_SERVICE_URL=https://chess-auth" `
  --volume-mount-path "/app/user_data" `
  --mount-volume-name chessuserdata `
  --output table

# -- UI (public) --
az containerapp create `
  --name chess-ui `
  --resource-group $RG `
  --environment $ENV `
  --image "$ACR_SERVER/chess-ui:latest" `
  --registry-server $ACR_SERVER `
  --registry-username $ACR_USERNAME `
  --registry-password $ACR_PASSWORD `
  --target-port 80 `
  --ingress external `
  --cpu 0.25 --memory 0.5Gi `
  --min-replicas 1 --max-replicas 2 `
  --output table

Write-Host "`n=== Deployment Complete! ===" -ForegroundColor Cyan

# Print URLs
Write-Host "`nPublic URL:" -ForegroundColor Cyan
az containerapp show --name chess-ui --resource-group $RG --query "properties.configuration.ingress.fqdn" --output tsv

Write-Host "`nInternal service FQDNs:" -ForegroundColor Cyan
az containerapp show --name chess-auth   --resource-group $RG --query "properties.configuration.ingress.fqdn" --output tsv
az containerapp show --name chess-admin  --resource-group $RG --query "properties.configuration.ingress.fqdn" --output tsv
az containerapp show --name chess-engine --resource-group $RG --query "properties.configuration.ingress.fqdn" --output tsv
