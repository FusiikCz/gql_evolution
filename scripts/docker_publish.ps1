# Docker Hub Publishing Script (PowerShell)
# Publikuje Docker image na Docker Hub s tagem latest
# Použití: .\scripts\docker_publish.ps1 <dockerhub_user> <image_name>

param(
    [Parameter(Mandatory=$true)]
    [string]$DockerHubUser,
    
    [Parameter(Mandatory=$true)]
    [string]$ImageName
)

$FullImageName = "${DockerHubUser}/${ImageName}:latest"

Write-Host "Building Docker image: $FullImageName" -ForegroundColor Cyan
docker build -t $FullImageName .

Write-Host "Logging in to Docker Hub..." -ForegroundColor Yellow
docker login

Write-Host "Pushing image to Docker Hub: $FullImageName" -ForegroundColor Cyan
docker push $FullImageName

Write-Host "✅ Successfully published $FullImageName to Docker Hub" -ForegroundColor Green
Write-Host "Verify with: docker pull $FullImageName" -ForegroundColor Gray
