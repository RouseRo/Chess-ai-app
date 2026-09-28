# Redeploy script — runs only steps 6-8 (build chess-ui + deploy all Container Apps)
# Use this when infra already exists from deploy-azure.ps1
$env:PATH = [System.Environment]::GetEnvironmentVariable("PATH","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH","User")

$RG         = "chess-ai-rg"
$LOCATION   = "eastus"
$ACR        = "chessairegistry7646"
$ENV_NAME   = "chess-ai-env"
$DATA_SHARE = "chessdata"
$USER_SHARE = "chessuserdata"
$JWT_SECRET = "chess-ai-jwt-secret-change-me-in-prod"
# SMTP — read from caller's environment; email verification is disabled on Azure
# until these are set (e.g. via $env:SMTP_HOST = '...' before running the script).
$SMTP_HOST      = $env:SMTP_HOST
$SMTP_PORT      = if ($env:SMTP_PORT)       { $env:SMTP_PORT }       else { "587" }
$SMTP_USER      = $env:SMTP_USER
$SMTP_PASSWORD  = $env:SMTP_PASSWORD
$SMTP_FROM      = if ($env:SMTP_FROM_EMAIL) { $env:SMTP_FROM_EMAIL } else { $SMTP_USER }
$ACR_SERVER     = "$ACR.azurecr.io"

# Timestamp tag — forces a new ACA revision on every deploy
$TAG = Get-Date -Format "yyyyMMdd-HHmm"

# Get ACR credentials
$ACR_USER = az acr credential show --name $ACR --query username --output tsv
$ACR_PASS = az acr credential show --name $ACR --query "passwords[0].value" --output tsv

# Rebuild and push chess-auth (feedback endpoints added)
Write-Host "[1/3] Rebuilding chess-auth image..." -ForegroundColor Yellow
az acr login --name $ACR
az acr build --registry $ACR --image chess-auth:latest --file auth-service/Dockerfile .
Write-Host "chess-auth image pushed." -ForegroundColor Green

# Rebuild and push chess-ui (nginx.conf + UI changes)
Write-Host "[2/3] Rebuilding chess-ui image..." -ForegroundColor Yellow
az acr build --registry $ACR --image chess-ui:latest --file ui/Dockerfile ui/
Write-Host "chess-ui image pushed." -ForegroundColor Green

# Helper: write YAML (no BOM) to temp file and deploy / update
function Deploy-App($name, $yaml) {
  $file = "$env:TEMP\$name.yaml"
  [System.IO.File]::WriteAllText($file, $yaml, (New-Object System.Text.UTF8Encoding $false))
  # Try create first, fall back to update if already exists
  Write-Host "  Deploying $name..." -ForegroundColor White
  $result = az containerapp create --name $name --resource-group $RG --yaml $file --output table 2>&1
  if ($LASTEXITCODE -ne 0) {
    Write-Host "  Create failed, trying update..." -ForegroundColor DarkYellow
    az containerapp update --name $name --resource-group $RG --yaml $file --output table
  }
}

Write-Host "[3/3] Deploying all 4 Container Apps..." -ForegroundColor Yellow

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
      external: true
      targetPort: 8002
      transport: http
  template:
    containers:
      - name: chess-auth
        image: ${ACR_SERVER}/chess-auth:latest
        resources:
          cpu: 0.25
          memory: 0.5Gi
        env:
          - name: JWT_SECRET_KEY
            value: $JWT_SECRET
          - name: CHESS_DEV_MODE
            value: "false"
          - name: SMTP_HOST
            value: $SMTP_HOST
          - name: SMTP_PORT
            value: "$SMTP_PORT"
          - name: SMTP_USER
            value: $SMTP_USER
          - name: SMTP_PASSWORD
            value: $SMTP_PASSWORD
          - name: SMTP_FROM_EMAIL
            value: $SMTP_FROM
        volumeMounts:
          - volumeName: $DATA_SHARE
            mountPath: /app/data
    volumes:
      - name: $DATA_SHARE
        storageType: AzureFile
        storageName: $DATA_SHARE
    revisionSuffix: $TAG
    scale:
      minReplicas: 1
      maxReplicas: 1
"@

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
        image: ${ACR_SERVER}/chess-admin:latest
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
    revisionSuffix: $TAG
    scale:
      minReplicas: 1
      maxReplicas: 1
"@

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
        image: ${ACR_SERVER}/chess-engine:latest
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
    revisionSuffix: $TAG
    scale:
      minReplicas: 1
      maxReplicas: 1
"@

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
        image: ${ACR_SERVER}/chess-ui:latest
        resources:
          cpu: 0.25
          memory: 0.5Gi
    revisionSuffix: $TAG
    scale:
      minReplicas: 1
      maxReplicas: 2
"@

Write-Host "`n=== Done! Public URL ===" -ForegroundColor Green
$UI_FQDN = az containerapp show --name chess-ui --resource-group $RG --query "properties.configuration.ingress.fqdn" --output tsv
Write-Host $UI_FQDN

# Patch APP_BASE_URL into chess-auth so email verification links use the real URL
if ($UI_FQDN) {
  Write-Host "`nSetting APP_BASE_URL on chess-auth..." -ForegroundColor Yellow
  az containerapp update --name chess-auth --resource-group $RG `
    --set-env-vars "APP_BASE_URL=https://$UI_FQDN" --output none
  Write-Host "APP_BASE_URL set to https://$UI_FQDN" -ForegroundColor Green
}
