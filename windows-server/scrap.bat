# 1. Read the CSV and pick out the Path column
# 2. Filter for only GStreamer bin files (to avoid copying System32 stuff)
# 3. Get unique filenames only
$csv = Import-Csv -Path "filtered_log.csv"
$neededFiles = $csv.Path | Where-Object { $_ -like "*gstreamer*bin*.dll" } | Get-Item | Select-Object -ExpandProperty Name -Unique

# Output the list to needed.txt
$neededFiles | Out-File -FilePath "needed_dlls.txt"

Write-Host "Found $($neededFiles.Count) unique GStreamer DLLs. List saved to needed_dlls.txt" -ForegroundColor Cyan