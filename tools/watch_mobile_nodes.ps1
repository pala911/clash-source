$ProgressPreference = 'SilentlyContinue'
$deadline = (Get-Date).AddMinutes(28)
while ((Get-Date) -lt $deadline) {
    Start-Sleep -Seconds 60
    try {
        $r = Invoke-WebRequest -UseBasicParsing -Uri 'https://pala911.github.io/clash-source/nodes/mobile.yaml' -TimeoutSec 15 -Proxy 'http://127.0.0.1:7897'
        if ($r.StatusCode -eq 200 -and $r.Content.Length -gt 100) {
            Write-Output ('MOBILE-NODES-LIVE ' + (Get-Date -Format 'HH:mm:ss') + ' bytes=' + $r.Content.Length)
            exit 0
        }
    } catch {}
}
Write-Output 'TIMEOUT-NOT-LIVE'
