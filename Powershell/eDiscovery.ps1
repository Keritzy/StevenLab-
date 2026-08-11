param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("Acquire","Analyze","Report")]
    [string]$Mode,
    [Parameter(Mandatory=$false)]
    [string]$TargetPath = "C:\",
    [Parameter(Mandatory=$false)]
    [string]$OutputDir = ".\ForensicOutput",
    [Parameter(Mandatory=$false)]
    [string[]]$FileExtensions = @(".exe",".dll",".sys",".ps1",".bat",".cmd",".vbs",".js",".jar",".class",".py",".rb",".pl",".sh",".elf",".apk",".dex",".xapk",".ipa",".app",".dmg",".pkg",".msi",".msp",".cab",".iso",".img",".vhd",".vmdk",".pst",".ost",".msg",".eml",".log",".evt",".evtx",".csv",".tsv",".json",".xml",".yaml",".yml",".ini",".conf",".config",".reg",".pol",".gpo",".admx",".adml",".inf",".sddl",".mof",".mof",".dll",".sys",".drv",".inf",".cat",".p7b",".p12",".pfx",".cer",".crt",".der",".key",".pem",".ppk",".pub",".asc",".gpg",".sig",".hash",".md5",".sha1",".sha256",".torrent",".nfo",".txt",".rtf",".doc",".docx",".xls",".xlsx",".ppt",".pptx",".pdf",".odt",".ods",".odp",".vsd",".vss",".vst",".pub",".one",".onepkg",".onetoc2",".url",".lnk",".scf",".shs",".pif",".com",".scr",".cpl",".cpl",".wsc",".wsf",".wsh",".htm",".html",".xhtml",".php",".asp",".aspx",".jsp",".do",".cgi",".pl",".rb",".go",".rs",".swift",".kt",".kts",".m",".mm",".c",".cpp",".h",".hpp",".cs",".vb",".fs",".fsx",".ts",".jsx",".tsx",".vue",".svelte",".scss",".less",".sass",".styl",".sql",".psql",".db",".sqlite",".sqlite3",".db3",".sdb",".mdb",".accdb",".adp",".fdb",".gdb",".ib",".frm",".myd",".myi",".dbf",".csv",".tsv",".dif",".slk",".wk1",".wk3",".wk4",".wks",".123",".wq1",".wq2",".wb1",".wb3",".wps",".xla",".xlam",".xlsb",".xlsm",".xlt",".xltm",".xltx",".xlw")
    [Parameter(Mandatory=$false)]
    [switch]$Hash = $true,
    [Parameter(Mandatory=$false)]
    [switch]$Timeline = $true,
    [Parameter(Mandatory=$false)]
    [switch]$Metadata = $true,
    [Parameter(Mandatory=$false)]
    [string]$HashAlgorithm = "SHA256",
    [Parameter(Mandatory=$false)]
    [int]$Parallelism = 4,
    [Parameter(Mandatory=$false)]
    [switch]$ZipOutput = $false
)

$ErrorActionPreference = "Stop"
$script:StartTime = Get-Date
$script:ProcessedCount = 0
$script:ErrorCount = 0

if (-not (Test-Path $TargetPath)) {
    Write-Error "Target path '$TargetPath' does not exist."
    exit 1
}

if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
}

$script:LogFile = Join-Path $OutputDir "forensic_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"
$script:MasterReport = Join-Path $OutputDir "forensic_report_$(Get-Date -Format 'yyyyMMdd_HHmmss').json"
$script:ManifestFile = Join-Path $OutputDir "file_manifest_$(Get-Date -Format 'yyyyMMdd_HHmmss').csv"

function Write-ForensicLog {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss.fff"
    $logEntry = "[$timestamp] [$Level] $Message"
    Add-Content -Path $script:LogFile -Value $logEntry
    if ($Level -eq "ERROR") {
        Write-Host $logEntry -ForegroundColor Red
    } elseif ($Level -eq "WARNING") {
        Write-Host $logEntry -ForegroundColor Yellow
    } else {
        Write-Host $logEntry -ForegroundColor Green
    }
}

function Get-FileMetadata {
    param([string]$FilePath)
    try {
        $file = Get-Item -Path $FilePath -Force -ErrorAction Stop
        $metadata = [PSCustomObject]@{
            FullPath = $file.FullName
            Name = $file.Name
            Extension = $file.Extension
            Size = $file.Length
            Created = $file.CreationTimeUtc.ToString("o")
            Modified = $file.LastWriteTimeUtc.ToString("o")
            Accessed = $file.LastAccessTimeUtc.ToString("o")
            Attributes = $file.Attributes.ToString()
            Owner = (Get-Acl -Path $file.FullName -ErrorAction SilentlyContinue).Owner
            IsReadOnly = $file.IsReadOnly
            IsHidden = (Get-ItemProperty -Path $file.FullName -Name "Attributes" -ErrorAction SilentlyContinue).Attributes -match "Hidden"
            IsSystem = (Get-ItemProperty -Path $file.FullName -Name "Attributes" -ErrorAction SilentlyContinue).Attributes -match "System"
            Extension = $file.Extension
        }
        return $metadata
    } catch {
        Write-ForensicLog "Failed to get metadata for '$FilePath': $_" "ERROR"
        return $null
    }
}

function Get-FileHashSafe {
    param([string]$FilePath, [string]$Algorithm = "SHA256")
    try {
        if (-not (Test-Path $FilePath)) {
            return $null
        }
        $hash = Get-FileHash -Path $FilePath -Algorithm $Algorithm -ErrorAction Stop
        return $hash.Hash
    } catch {
        Write-ForensicLog "Hash calculation failed for '$FilePath': $_" "ERROR"
        return "HASH_FAILED"
    }
}

function Get-FileTimeline {
    param([string]$FilePath)
    try {
        $item = Get-Item -Path $FilePath -Force -ErrorAction Stop
        $timeline = [PSCustomObject]@{
            FilePath = $item.FullName
            CreationTime = $item.CreationTimeUtc.ToString("o")
            LastWriteTime = $item.LastWriteTimeUtc.ToString("o")
            LastAccessTime = $item.LastAccessTimeUtc.ToString("o")
            CreationTimeLocal = $item.CreationTime.ToString("o")
            LastWriteTimeLocal = $item.LastWriteTime.ToString("o")
            LastAccessTimeLocal = $item.LastAccessTime.ToString("o")
        }
        return $timeline
    } catch {
        return $null
    }
}

function Invoke-Acquire {
    Write-ForensicLog "Starting acquisition phase for '$TargetPath'" "INFO"
    
    $fileList = Get-ChildItem -Path $TargetPath -Recurse -File -Force -ErrorAction SilentlyContinue | 
                Where-Object { $FileExtensions -contains $_.Extension -or $FileExtensions -contains "*" }
    
    $totalFiles = ($fileList | Measure-Object).Count
    Write-ForensicLog "Found $totalFiles files matching criteria" "INFO"
    
    $manifestData = @()
    $hashErrors = 0
    $metadataErrors = 0
    $timelineErrors = 0
    $processed = 0
    
    $fileList | ForEach-Object -Parallel {
        $currentFile = $_
        $local:processed = 0
        $local:hashErrors = 0
        $local:metadataErrors = 0
        $local:timelineErrors = 0
        
        try {
            $filePath = $currentFile.FullName
            $record = [PSCustomObject]@{
                Path = $filePath
                Name = $currentFile.Name
                Extension = $currentFile.Extension
                Size = $currentFile.Length
                Created = $currentFile.CreationTimeUtc.ToString("o")
                Modified = $currentFile.LastWriteTimeUtc.ToString("o")
                Accessed = $currentFile.LastAccessTimeUtc.ToString("o")
                Hash = $null
                HashAlgorithm = $null
                Owner = (Get-Acl -Path $filePath -ErrorAction SilentlyContinue).Owner
                Attributes = $currentFile.Attributes.ToString()
                IsHidden = ($currentFile.Attributes -match "Hidden")
                IsSystem = ($currentFile.Attributes -match "System")
                IsReadOnly = $currentFile.IsReadOnly
                Timeline = $null
            }
            
            if ($using:Hash) {
                $hash = Get-FileHashSafe -FilePath $filePath -Algorithm $using:HashAlgorithm
                $record.Hash = $hash
                $record.HashAlgorithm = $using:HashAlgorithm
                if ($hash -eq "HASH_FAILED") { $local:hashErrors++ }
            }
            
            if ($using:Metadata) {
                $metadata = Get-FileMetadata -FilePath $filePath
                if ($metadata -eq $null) { $local:metadataErrors++ }
            }
            
            if ($using:Timeline) {
                $timeline = Get-FileTimeline -FilePath $filePath
                if ($timeline -eq $null) { $local:timelineErrors++ }
                $record.Timeline = $timeline
            }
            
            $manifestData += $record
            $local:processed++
            
            if ($local:processed % 100 -eq 0) {
                Write-ForensicLog "Processed $local:processed files in parallel batch" "INFO"
            }
        } catch {
            Write-ForensicLog "Error processing '$($currentFile.FullName)': $_" "ERROR"
            $global:ErrorCount++
        }
    } -ThrottleLimit $Parallelism
    
    Write-ForensicLog "Acquisition completed. Processed $processed files with $hashErrors hash errors, $metadataErrors metadata errors, $timelineErrors timeline errors" "INFO"
    
    $manifestData | Export-Csv -Path $script:ManifestFile -NoTypeInformation
    Write-ForensicLog "Manifest exported to $script:ManifestFile" "INFO"
}

function Invoke-Analyze {
    Write-ForensicLog "Starting analysis phase" "INFO"
    
    if (-not (Test-Path $script:ManifestFile)) {
        Write-ForensicLog "Manifest file not found. Run acquisition first." "ERROR"
        return
    }
    
    $manifest = Import-Csv -Path $script:ManifestFile
    $analysisResults = @()
    $suspiciousExtensions = @(".exe",".dll",".scr",".pif",".cmd",".bat",".vbs",".js",".jar",".ps1")
    $suspiciousKeywords = @("password","backdoor","exploit","malware","trojan","ransomware","inject","keylog","spy","worm","virus","rootkit","stealth","payload","c2","callback","crypt","miner","bot","dropper","packed","obfuscated")
    
    foreach ($file in $manifest) {
        try {
            $analysis = [PSCustomObject]@{
                Path = $file.Path
                Name = $file.Name
                Extension = $file.Extension
                Size = [long]$file.Size
                Created = $file.Created
                Modified = $file.Modified
                Hash = $file.Hash
                SuspiciousScore = 0
                RiskIndicators = @()
                Owner = $file.Owner
                Attributes = $file.Attributes
                IsSystem = [bool]$file.IsSystem
                IsHidden = [bool]$file.IsHidden
                TimelineAnomalies = @()
            }
            
            if ($suspiciousExtensions -contains $file.Extension) {
                $analysis.SuspiciousScore += 20
                $analysis.RiskIndicators += "Suspicious extension: $($file.Extension)"
            }
            
            $fileName = $file.Name.ToLower()
            foreach ($keyword in $suspiciousKeywords) {
                if ($fileName -match $keyword) {
                    $analysis.SuspiciousScore += 10
                    $analysis.RiskIndicators += "Keyword found: $keyword"
                }
            }
            
            if ($file.Size -lt 1024 -and $file.Extension -match "\.(exe|dll|sys|drv)") {
                $analysis.SuspiciousScore += 15
                $analysis.RiskIndicators += "Unusually small executable/driver (< 1KB)"
            }
            
            if ($file.Size -gt 104857600 -and $file.Extension -match "\.(exe|dll)") {
                $analysis.SuspiciousScore += 10
                $analysis.RiskIndicators += "Large executable/dll (> 100MB)"
            }
            
            if ($file.IsHidden -eq "True" -and $file.Extension -match "\.(exe|dll|ps1|vbs|js)") {
                $analysis.SuspiciousScore += 15
                $analysis.RiskIndicators += "Hidden executable/script"
            }
            
            if ($file.IsSystem -eq "True" -and $file.IsHidden -eq "True") {
                $analysis.SuspiciousScore += 10
                $analysis.RiskIndicators += "System file with hidden attribute"
            }
            
            $created = [datetime]::ParseExact($file.Created, "yyyy-MM-ddTHH:mm:ss.fffffffZ", $null)
            $modified = [datetime]::ParseExact($file.Modified, "yyyy-MM-ddTHH:mm:ss.fffffffZ", $null)
            $timeDiff = ($modified - $created).TotalMinutes
            if ($timeDiff -lt 0) {
                $analysis.TimelineAnomalies += "Modified before created (timestamp skew)"
                $analysis.SuspiciousScore += 20
            }
            if ($timeDiff -lt 1 -and $timeDiff -ge 0 -and $file.Size -gt 1048576) {
                $analysis.TimelineAnomalies += "Created and modified within 1 minute (large file)"
                $analysis.SuspiciousScore += 15
            }
            
            if ($file.Owner -match "SYSTEM|LOCAL SERVICE|NETWORK SERVICE") {
                $analysis.RiskIndicators += "System-owned file in user directory"
                $analysis.SuspiciousScore += 10
            }
            
            if ($analysis.SuspiciousScore -ge 40) {
                $analysis.RiskLevel = "HIGH"
            } elseif ($analysis.SuspiciousScore -ge 20) {
                $analysis.RiskLevel = "MEDIUM"
            } else {
                $analysis.RiskLevel = "LOW"
            }
            
            $analysisResults += $analysis
        } catch {
            Write-ForensicLog "Analysis error for '$($file.Path)': $_" "ERROR"
        }
    }
    
    $highRisk = $analysisResults | Where-Object { $_.RiskLevel -eq "HIGH" }
    $mediumRisk = $analysisResults | Where-Object { $_.RiskLevel -eq "MEDIUM" }
    
    Write-ForensicLog "Analysis complete. Found $($highRisk.Count) HIGH risk, $($mediumRisk.Count) MEDIUM risk files" "INFO"
    
    $report = @{
        Timestamp = Get-Date -Format "o"
        TargetPath = $TargetPath
        TotalFilesAnalyzed = $analysisResults.Count
        HighRisk = $highRisk.Count
        MediumRisk = $mediumRisk.Count
        LowRisk = ($analysisResults.Count - $highRisk.Count - $mediumRisk.Count)
        HighRiskFiles = $highRisk
        MediumRiskFiles = $mediumRisk
        FullAnalysis = $analysisResults
        Summary = [PSCustomObject]@{
            SuspiciousExtensions = $analysisResults | Where-Object { $_.Extension -match "\.(exe|dll|scr|pif|cmd|bat|vbs|js|jar|ps1)" } | Measure-Object | Select-Object -ExpandProperty Count
            HiddenFiles = $analysisResults | Where-Object { $_.IsHidden -eq $true } | Measure-Object | Select-Object -ExpandProperty Count
            SystemFiles = $analysisResults | Where-Object { $_.IsSystem -eq $true } | Measure-Object | Select-Object -ExpandProperty Count
            TimelineAnomalies = $analysisResults | Where-Object { $_.TimelineAnomalies.Count -gt 0 } | Measure-Object | Select-Object -ExpandProperty Count
        }
    }
    
    $report | ConvertTo-Json -Depth 10 | Set-Content -Path $script:MasterReport
    Write-ForensicLog "Analysis report saved to $script:MasterReport" "INFO"
}

function Invoke-Report {
    Write-ForensicLog "Generating comprehensive forensic report" "INFO"
    
    if (-not (Test-Path $script:MasterReport)) {
        Write-ForensicLog "No analysis report found. Run analysis first." "ERROR"
        return
    }
    
    $reportData = Get-Content -Path $script:MasterReport | ConvertFrom-Json
    $reportSummary = @"
==========================================
        FORENSIC INVESTIGATION REPORT
==========================================
Timestamp: $($reportData.Timestamp)
Target Path: $($reportData.TargetPath)
Total Files Analyzed: $($reportData.TotalFilesAnalyzed)

RISK SUMMARY:
- HIGH Risk: $($reportData.HighRisk)
- MEDIUM Risk: $($reportData.MediumRisk)
- LOW Risk: $($reportData.LowRisk)

KEY FINDINGS:
- Suspicious Extensions: $($reportData.Summary.SuspiciousExtensions)
- Hidden Files: $($reportData.Summary.HiddenFiles)
- System Files: $($reportData.Summary.SystemFiles)
- Timeline Anomalies: $($reportData.Summary.TimelineAnomalies)

HIGH RISK FILES:
$($reportData.HighRiskFiles | ForEach-Object { "  - $($_.Name) ($($_.Extension)) [Score: $($_.SuspiciousScore)] Indicators: $($_.RiskIndicators -join ', ')" })

MEDIUM RISK FILES:
$($reportData.MediumRiskFiles | ForEach-Object { "  - $($_.Name) ($($_.Extension)) [Score: $($_.SuspiciousScore)] Indicators: $($_.RiskIndicators -join ', ')" })

==========================================
         END OF REPORT
==========================================
"@
    
    $reportFile = Join-Path $OutputDir "forensic_summary_$(Get-Date -Format 'yyyyMMdd_HHmmss').txt"
    $reportSummary | Set-Content -Path $reportFile
    Write-ForensicLog "Summary report generated at $reportFile" "INFO"
    
    if ($ZipOutput) {
        $zipName = "ForensicExport_$(Get-Date -Format 'yyyyMMdd_HHmmss').zip"
        Compress-Archive -Path $OutputDir\* -DestinationPath $zipName -CompressionLevel Optimal
        Write-ForensicLog "Output archived to $zipName" "INFO"
    }
}

try {
    switch ($Mode) {
        "Acquire" {
            Invoke-Acquire
            Write-ForensicLog "Acquisition phase completed successfully" "INFO"
        }
        "Analyze" {
            Invoke-Analyze
            Write-ForensicLog "Analysis phase completed successfully" "INFO"
        }
        "Report" {
            Invoke-Report
            Write-ForensicLog "Report phase completed successfully" "INFO"
        }
        default {
            Write-ForensicLog "Invalid mode. Use Acquire, Analyze, or Report" "ERROR"
            exit 1
        }
    }
} catch {
    Write-ForensicLog "Fatal error: $_" "ERROR"
    exit 1
}

$duration = (Get-Date) - $script:StartTime
Write-ForensicLog "Total execution time: $($duration.ToString('hh\:mm\:ss'))" "INFO"
Write-ForensicLog "Forensic investigation tool execution completed" "INFO"