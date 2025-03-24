# PowerShell script to convert WAV files to MP3
$wavFiles = Get-ChildItem -Path ".\static\sfx\pop-*.wav"

# Create mp3 directory if it doesn't exist
$mp3Dir = ".\static\sfx\mp3"
if (-not (Test-Path -Path $mp3Dir)) {
    New-Item -ItemType Directory -Path $mp3Dir | Out-Null
    Write-Host "Created directory: $mp3Dir"
}

foreach ($wavFile in $wavFiles) {
    $baseName = $wavFile.BaseName
    $mp3File = Join-Path -Path $mp3Dir -ChildPath "$baseName.mp3"
    
    Write-Host "Converting $($wavFile.Name) to MP3..."
    ffmpeg -i $wavFile.FullName -codec:a libmp3lame -qscale:a 2 $mp3File -y
}

Write-Host "Conversion complete! MP3 files are in $mp3Dir"
