$env:PATH = [System.Environment]::GetEnvironmentVariable("PATH","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH","User")

$RG          = "chess-ai-rg"
$SUB         = "b2dbdeb1-b560-47fa-b29e-07339ad9160d"
$ACR_SERVER  = "chessairegistry7646.azurecr.io"
$JWT         = "chess-ai-jwt-secret-change-me-in-prod"
$ENV_MGR_ID  = "/subscriptions/$SUB/resourceGroups/$RG/providers/Microsoft.App/managedEnvironments/chess-ai-env"

function Update-WithVolumes($name, $yaml) {
    $file = "$env:TEMP\$name-vol.yaml"
    [System.IO.File]::WriteAllText($file, $yaml, (New-Object System.Text.UTF8Encoding $false))
    Write-Host "`n=== Updating $name with volumes ===" -ForegroundColor Yellow
    $out = az containerapp update --name $name --resource-group $RG --yaml $file 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: $out" -ForegroundColor Red
    } else {
        Write-Host "OK: $($out | Select-String 'provisioningState|runningStatus|volumes' | Select-Object -First 5)" -ForegroundColor Green
        $out | ConvertFrom-Json | Select-Object -ExpandProperty properties | Select-Object provisioningState,runningStatus
    }
}

# chess-auth: needs chessdata (/app/data)
Update-WithVolumes "chess-auth" @"
location: eastus
type: Microsoft.App/containerApps
kind: containerapp
properties:
  managedEnvironmentId: $ENV_MGR_ID
  configuration:
    ingress:
      external: false
      targetPort: 8002
      transport: Auto
  template:
    containers:
      - name: chess-auth
        image: ${ACR_SERVER}/chess-auth:latest
        resources:
          cpu: 0.25
          memory: 0.5Gi
        env:
          - name: JWT_SECRET_KEY
            value: $JWT
        volumeMounts:
          - volumeName: chessdata
            mountPath: /app/data
    volumes:
      - name: chessdata
        storageType: AzureFile
        storageName: chessdata
    scale:
      minReplicas: 1
      maxReplicas: 1
"@

# chess-admin: needs chessdata (/app/data) + chessuserdata (/app/user_data)
Update-WithVolumes "chess-admin" @"
location: eastus
type: Microsoft.App/containerApps
kind: containerapp
properties:
  managedEnvironmentId: $ENV_MGR_ID
  configuration:
    ingress:
      external: false
      targetPort: 8001
      transport: Auto
  template:
    containers:
      - name: chess-admin
        image: ${ACR_SERVER}/chess-admin:latest
        resources:
          cpu: 0.25
          memory: 0.5Gi
        volumeMounts:
          - volumeName: chessdata
            mountPath: /app/data
          - volumeName: chessuserdata
            mountPath: /app/user_data
    volumes:
      - name: chessdata
        storageType: AzureFile
        storageName: chessdata
      - name: chessuserdata
        storageType: AzureFile
        storageName: chessuserdata
    scale:
      minReplicas: 1
      maxReplicas: 1
"@

# chess-engine: needs chessuserdata (/app/user_data)
Update-WithVolumes "chess-engine" @"
location: eastus
type: Microsoft.App/containerApps
kind: containerapp
properties:
  managedEnvironmentId: $ENV_MGR_ID
  configuration:
    ingress:
      external: false
      targetPort: 8000
      transport: Auto
  template:
    containers:
      - name: chess-engine
        image: ${ACR_SERVER}/chess-engine:latest
        resources:
          cpu: 0.5
          memory: 1.0Gi
        env:
          - name: JWT_SECRET_KEY
            value: $JWT
          - name: AUTH_SERVICE_URL
            value: http://chess-auth
        volumeMounts:
          - volumeName: chessuserdata
            mountPath: /app/user_data
    volumes:
      - name: chessuserdata
        storageType: AzureFile
        storageName: chessuserdata
    scale:
      minReplicas: 1
      maxReplicas: 1
"@

Write-Host "`n=== Final status ===" -ForegroundColor Cyan
az containerapp list -g $RG -o table
