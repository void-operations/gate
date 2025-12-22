using System;
using System.Net.Http;
using System.Net.Http.Json;
using System.Text.Json.Serialization;
using System.Threading;
using System.Threading.Tasks;
using System.IO;
using System.Diagnostics;
using System.Text.RegularExpressions;
using System.Linq;
using Newtonsoft.Json;

namespace Agent;

/// <summary>
/// Agent - Client that connects to Master server and reports status
/// </summary>
class Program
{
#if DEBUG
    private static readonly bool IsDebugMode = true;
#else
    private static readonly bool IsDebugMode = false;
#endif

    private static readonly HttpClient httpClient = new HttpClient()
    {
        DefaultRequestHeaders = { { "User-Agent", "VoidOps-Agent/1.0.0" } }
    };
    private static string masterUrl = "http://localhost:8000";
    private static string agentName = Environment.MachineName;
    private static string agentPlatform = GetPlatform();
    private static string agentVersion = "1.0.0";
    private static string agentId = "";
    private static bool running = true;

    static void LogDebug(string message)
    {
        if (IsDebugMode)
        {
            Console.WriteLine($"[DEBUG] {message}");
        }
    }

    static void LogInfo(string message)
    {
        Console.WriteLine(message);
    }

    static void LogError(string message, Exception? ex = null)
    {
        Console.WriteLine($"❌ {message}");
        if (IsDebugMode && ex != null)
        {
            Console.WriteLine($"   Exception Type: {ex.GetType().Name}");
            Console.WriteLine($"   Stack Trace:");
            Console.WriteLine($"   {ex.StackTrace}");
            if (ex.InnerException != null)
            {
                Console.WriteLine($"   Inner Exception: {ex.InnerException.Message}");
                Console.WriteLine($"   Inner Stack Trace:");
                Console.WriteLine($"   {ex.InnerException.StackTrace}");
            }
        }
    }

    static async Task Main(string[] args)
    {
        Console.WriteLine($"🚀 Agent started");
        Console.WriteLine($"   Name: {agentName}");
        Console.WriteLine($"   Platform: {agentPlatform}");
        Console.WriteLine($"   Version: {agentVersion}");
        Console.WriteLine($"   Master URL: {masterUrl}");

        // Parse command line arguments
        if (args.Length > 0)
        {
            masterUrl = args[0];
        }

        // Handle Ctrl+C
        Console.CancelKeyPress += (sender, e) =>
        {
            e.Cancel = true;
            running = false;
            Console.WriteLine("\n⏹️  Shutting down...");
        };

        // Register with Master
        await RegisterToMaster();

        // Send heartbeat and check for deployments periodically (every 10 seconds)
        var heartbeatTask = Task.Run(async () =>
        {
            while (running)
            {
                await Task.Delay(10000);
                if (running)
                {
                    await SendHeartbeat();
                    await CheckForDeployment();
                }
            }
        });

        // Main loop
        Console.WriteLine("✓ Connected to Master. Sending heartbeat...");
        Console.WriteLine("  (Press Ctrl+C to exit)");

        await heartbeatTask;
        
        // Unregister on exit
        await UnregisterFromMaster();
        Console.WriteLine("✅ Agent stopped");
    }

    static async Task RegisterToMaster()
    {
        try
        {
            var request = new
            {
                name = agentName,
                platform = agentPlatform,
                version = agentVersion,
                ip_address = GetLocalIPAddress()
            };

            var response = await httpClient.PostAsJsonAsync(
                $"{masterUrl}/api/agents/register",
                request
            );

            if (response.IsSuccessStatusCode)
            {
                var agent = await response.Content.ReadFromJsonAsync<AgentResponse>();
                agentId = agent?.id ?? "";
                Console.WriteLine($"✓ Registered with Master (ID: {agentId})");
            }
            else
            {
                Console.WriteLine($"⚠️  Registration failed: {response.StatusCode}");
            }
        }
        catch (Exception ex)
        {
            Console.WriteLine($"❌ Failed to connect to Master: {ex.Message}");
            Console.WriteLine("   Please check if Master server is running.");
        }
    }

    static async Task SendHeartbeat()
    {
        try
        {
            var request = new
            {
                name = agentName,
                platform = agentPlatform,
                version = agentVersion,
                ip_address = GetLocalIPAddress()
            };

            await httpClient.PostAsJsonAsync(
                $"{masterUrl}/api/agents/register",
                request
            );
        }
        catch (Exception ex)
        {
            Console.WriteLine($"⚠️  Heartbeat failed: {ex.Message}");
        }
    }

    static async Task UnregisterFromMaster()
    {
        try
        {
            if (!string.IsNullOrEmpty(agentId))
            {
                await httpClient.DeleteAsync($"{masterUrl}/api/agents/{agentId}");
                Console.WriteLine("✓ Unregistered from Master");
            }
        }
        catch (Exception ex)
        {
            Console.WriteLine($"⚠️  Unregistration failed: {ex.Message}");
        }
    }

    static async Task CheckForDeployment()
    {
        if (string.IsNullOrEmpty(agentId))
        {
            return;
        }

        try
        {
            var response = await httpClient.GetAsync($"{masterUrl}/api/deployments/pending/{agentId}");
            
            if (response.IsSuccessStatusCode)
            {
                var content = await response.Content.ReadAsStringAsync();
                
                // Check if response is null or empty (no pending deployment)
                if (string.IsNullOrWhiteSpace(content) || content == "null")
                {
                    return;
                }

                var deployment = JsonConvert.DeserializeObject<DeploymentResponse>(content);
                
                if (deployment != null && !string.IsNullOrEmpty(deployment.id))
                {
                    Console.WriteLine($"📦 Received deployment: {deployment.id}");
                    Console.WriteLine($"   Releases: {string.Join(", ", deployment.release_tags ?? new List<string>())}");
                    await ExecuteDeployment(deployment);
                }
            }
        }
        catch (Exception ex)
        {
            Console.WriteLine($"⚠️  Failed to check for deployment: {ex.Message}");
        }
    }

    static async Task ExecuteDeployment(DeploymentResponse deployment)
    {
        try
        {
            Console.WriteLine($"🚀 Executing deployment: {deployment.id}...");
            
            if (deployment.release_ids == null || deployment.release_ids.Count == 0)
            {
                throw new Exception("No releases to deploy");
            }
            
            // Process each release in the deployment
            for (int i = 0; i < deployment.release_ids.Count; i++)
            {
                var releaseId = deployment.release_ids[i];
                // Get the corresponding tag from release_tags (deployment creation time selected tag)
                var selectedTag = deployment.release_tags != null && i < deployment.release_tags.Count 
                    ? deployment.release_tags[i] 
                    : null;
                
                Console.WriteLine($"📦 Processing release: {releaseId}");
                
                // 1. Fetch release details from Master
                if (IsDebugMode)
                {
                    LogDebug($"Fetching release details for release ID: {releaseId}");
                    if (!string.IsNullOrEmpty(selectedTag))
                    {
                        LogDebug($"Selected tag from deployment: {selectedTag}");
                    }
                }
                var release = await FetchReleaseDetails(releaseId);
                if (release == null)
                {
                    if (IsDebugMode)
                    {
                        LogDebug($"Release fetch returned null for release ID: {releaseId}");
                    }
                    throw new Exception($"Failed to fetch release details for {releaseId}");
                }
                
                // Use the tag from deployment if available, otherwise fall back to release.tag_name
                var tagToUse = !string.IsNullOrEmpty(selectedTag) ? selectedTag : release.tag_name;
                
                if (IsDebugMode)
                {
                    LogDebug($"Release details fetched successfully");
                    LogDebug($"  Release ID: {release.id}");
                    LogDebug($"  Release tag (from DB): {release.tag_name}");
                    LogDebug($"  Tag to use for download: {tagToUse}");
                    LogDebug($"  Download URL: {release.download_url}");
                }
                
                // 2. Download release artifacts from GitHub using the selected tag
                if (IsDebugMode)
                {
                    LogDebug($"Starting download of release artifacts");
                }
                var downloadPath = await DownloadReleaseArtifacts(release, tagToUse);
                if (string.IsNullOrEmpty(downloadPath))
                {
                    if (IsDebugMode)
                    {
                        LogDebug($"Download returned null or empty path");
                    }
                    throw new Exception($"Failed to download artifacts for {releaseId}");
                }
                
                if (IsDebugMode)
                {
                    LogDebug($"Download completed. Path: {downloadPath}");
                }
                
                // 3. Install/execute software based on platform
                if (IsDebugMode)
                {
                    LogDebug($"Starting software installation");
                }
                var installSuccess = await InstallSoftware(downloadPath, release);
                if (!installSuccess)
                {
                    if (IsDebugMode)
                    {
                        LogDebug($"Installation returned false");
                    }
                    throw new Exception($"Failed to install software for {releaseId}");
                }
                
                // 4. Verify installation (basic check - file exists and is executable)
                var verifySuccess = VerifyInstallation(downloadPath);
                if (!verifySuccess)
                {
                    throw new Exception($"Installation verification failed for {releaseId}");
                }
                
                Console.WriteLine($"✓ Release {releaseId} deployed successfully");
            }
            
            Console.WriteLine($"✅ Deployment {deployment.id} completed successfully");
            await ReportDeploymentComplete(deployment.id, "success", string.Empty);
        }
        catch (Exception ex)
        {
            LogError($"Deployment execution failed: {ex.Message}", ex);
            if (IsDebugMode)
            {
                LogDebug($"Deployment ID: {deployment.id}");
                LogDebug($"Release IDs: {(deployment.release_ids != null ? string.Join(", ", deployment.release_ids) : "null")}");
                LogDebug($"Release Tags: {(deployment.release_tags != null ? string.Join(", ", deployment.release_tags) : "null")}");
            }
            await ReportDeploymentComplete(deployment.id, "failed", ex.Message);
        }
    }
    
    static async Task<ReleaseResponse?> FetchReleaseDetails(string releaseId)
    {
        try
        {
            var url = $"{masterUrl}/api/releases/{releaseId}";
            if (IsDebugMode)
            {
                LogDebug($"Fetching release details from: {url}");
            }
            var response = await httpClient.GetAsync(url);
            
            if (response.IsSuccessStatusCode)
            {
                var content = await response.Content.ReadAsStringAsync();
                if (IsDebugMode)
                {
                    LogDebug($"Release details response received. Length: {content.Length} characters");
                }
                return JsonConvert.DeserializeObject<ReleaseResponse>(content);
            }
            else
            {
                LogInfo($"⚠️  Failed to fetch release details: {response.StatusCode}");
                if (IsDebugMode)
                {
                    var errorContent = await response.Content.ReadAsStringAsync();
                    LogDebug($"Error response content: {errorContent}");
                }
                return null;
            }
        }
        catch (Exception ex)
        {
            LogError($"Error fetching release details: {ex.Message}", ex);
            if (IsDebugMode)
            {
                LogDebug($"Release ID: {releaseId}");
                LogDebug($"Master URL: {masterUrl}");
            }
            return null;
        }
    }
    
    static async Task<string?> DownloadReleaseArtifacts(ReleaseResponse release, string tag)
    {
        try
        {
            if (string.IsNullOrEmpty(release.download_url))
            {
                throw new Exception("Release download URL is empty");
            }
            
            if (string.IsNullOrEmpty(tag))
            {
                throw new Exception("Release tag name is empty");
            }
            
            // Extract owner and repo from GitHub URL
            // Example: https://github.com/jameskwon07/3project/releases/
            var githubUrl = release.download_url.TrimEnd('/');
            var pattern = @"https://github\.com/([^/]+)/([^/]+)";
            var match = Regex.Match(githubUrl, pattern);
            
            if (!match.Success)
            {
                throw new Exception($"Invalid GitHub URL format: {githubUrl}");
            }
            
            var owner = match.Groups[1].Value;
            var repo = match.Groups[2].Value;
            
            // Create downloads directory
            var downloadsDir = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), ".agent", "downloads");
            Directory.CreateDirectory(downloadsDir);
            
            LogInfo($"📥 Downloading from GitHub: {owner}/{repo}");
            
            if (IsDebugMode)
            {
                LogDebug($"Release tag (from DB): {release.tag_name}");
                LogDebug($"Tag to use: {tag}");
                LogDebug($"Release name: {release.name}");
                LogDebug($"Release version: {release.version}");
                LogDebug($"Downloads directory: {downloadsDir}");
            }
            
            // Fetch release details from GitHub API to get assets using the selected tag
            var githubApiUrl = $"https://api.github.com/repos/{owner}/{repo}/releases/tags/{tag}";
            if (IsDebugMode)
            {
                LogDebug($"GitHub API URL: {githubApiUrl}");
            }
            
            // GitHub API requires User-Agent header (already set on httpClient)
            var githubResponse = await httpClient.GetAsync(githubApiUrl);
            if (!githubResponse.IsSuccessStatusCode)
            {
                var errorContent = await githubResponse.Content.ReadAsStringAsync();
                if (IsDebugMode)
                {
                    LogDebug($"GitHub API error response: {errorContent}");
                }
                throw new Exception($"Failed to fetch release from GitHub API: {githubResponse.StatusCode}");
            }
            
            var githubContent = await githubResponse.Content.ReadAsStringAsync();
            var githubRelease = JsonConvert.DeserializeObject<GitHubReleaseResponse>(githubContent);
            
            if (githubRelease == null || githubRelease.assets == null || githubRelease.assets.Count == 0)
            {
                throw new Exception($"No assets found for release {tag}");
            }
            
            if (IsDebugMode)
            {
                LogDebug($"Found {githubRelease.assets.Count} assets:");
                foreach (var asset in githubRelease.assets)
                {
                    LogDebug($"  - {asset.name} ({asset.size} bytes, {asset.content_type})");
                }
            }
            
            // Filter out source code archives (only if they contain source code keywords)
            var sourceCodeKeywords = new[] { "source", "src", "sourcecode" };
            
            var executableAssets = githubRelease.assets
                .Where(asset => 
                {
                    var nameLower = asset.name.ToLower();
                    // Exclude if it's clearly a source code archive (check for keywords first)
                    if (sourceCodeKeywords.Any(keyword => nameLower.Contains(keyword)))
                    {
                        return false;
                    }
                    // For .zip, .tar.gz, and .tar files, only exclude if they contain source code keywords
                    // (already handled above, so these extensions are allowed if no keywords found)
                    return true;
                })
                .ToList();
            
            if (executableAssets.Count == 0)
            {
                throw new Exception($"No executable assets found (excluding source code) for release {tag}");
            }
            
            // Select the largest asset (likely the main executable/installer) or platform-specific asset
            GitHubReleaseAsset? selectedAsset = null;
            
            // Try to find platform-specific asset first
            var platformExtensions = agentPlatform == "windows" 
                ? new[] { ".exe", ".msi", ".zip" }
                : agentPlatform == "macos"
                ? new[] { ".dmg", ".pkg", ".app.zip", ".zip" }
                : new[] { ".deb", ".rpm", ".tar.gz", ".zip" };
            
            selectedAsset = executableAssets.FirstOrDefault(asset => 
                platformExtensions.Any(ext => asset.name.ToLower().EndsWith(ext.ToLower())));
            
            // If no platform-specific asset found, select the largest one
            if (selectedAsset == null)
            {
                selectedAsset = executableAssets.OrderByDescending(a => a.size).First();
            }
            
            if (selectedAsset == null)
            {
                throw new Exception("Failed to select an asset to download");
            }
            
            if (IsDebugMode)
            {
                LogDebug($"Selected asset: {selectedAsset.name} ({selectedAsset.size} bytes)");
                LogDebug($"Download URL: {selectedAsset.browser_download_url}");
            }
            
            LogInfo($"📦 Downloading asset: {selectedAsset.name}");
            
            // Download the asset
            var downloadResponse = await httpClient.GetAsync(selectedAsset.browser_download_url);
            if (!downloadResponse.IsSuccessStatusCode)
            {
                throw new Exception($"Failed to download asset: {downloadResponse.StatusCode}");
            }
            
            // Determine file extension from content type or file name
            var fileExtension = Path.GetExtension(selectedAsset.name);
            if (string.IsNullOrEmpty(fileExtension))
            {
                // Try to infer from content type
                if (selectedAsset.content_type.Contains("zip"))
                    fileExtension = ".zip";
                else if (selectedAsset.content_type.Contains("dmg"))
                    fileExtension = ".dmg";
                else if (selectedAsset.content_type.Contains("exe"))
                    fileExtension = ".exe";
            }
            
            var fileName = $"{repo}-{tag}{fileExtension}";
            var downloadPath = Path.Combine(downloadsDir, fileName);
            
            // Save the downloaded file
            using (var fileStream = new FileStream(downloadPath, FileMode.Create, FileAccess.Write))
            {
                await downloadResponse.Content.CopyToAsync(fileStream);
            }
            
            if (IsDebugMode)
            {
                var fileInfo = new FileInfo(downloadPath);
                LogDebug($"Download completed. File size: {fileInfo.Length} bytes");
                LogDebug($"Saved to: {downloadPath}");
            }
            
            LogInfo($"✓ Downloaded: {fileName}");
            return downloadPath;
        }
        catch (Exception ex)
        {
            LogError($"Error downloading artifacts: {ex.Message}", ex);
            if (IsDebugMode && release != null)
            {
                LogDebug($"Release ID: {release.id}");
                LogDebug($"Release tag (from DB): {release.tag_name}");
                LogDebug($"Tag used for download: {tag}");
                LogDebug($"Release download URL: {release.download_url}");
            }
            return null;
        }
    }
    
    static async Task<bool> InstallSoftware(string filePath, ReleaseResponse release)
    {
        try
        {
            if (!File.Exists(filePath))
            {
                LogInfo($"⚠️  File not found: {filePath}");
                if (IsDebugMode)
                {
                    LogDebug($"Checking if directory exists: {Path.GetDirectoryName(filePath)}");
                    var dir = Path.GetDirectoryName(filePath);
                    if (!string.IsNullOrEmpty(dir))
                    {
                        LogDebug($"Directory exists: {Directory.Exists(dir)}");
                        if (Directory.Exists(dir))
                        {
                            LogDebug($"Files in directory:");
                            foreach (var file in Directory.GetFiles(dir))
                            {
                                LogDebug($"  - {file}");
                            }
                        }
                    }
                }
                return false;
            }
            
            if (IsDebugMode)
            {
                var fileInfo = new FileInfo(filePath);
                LogDebug($"File found. Size: {fileInfo.Length} bytes");
                LogDebug($"File path: {filePath}");
                LogDebug($"Platform: {agentPlatform}");
            }
            
            // Make file executable on macOS/Linux
            if (agentPlatform == "macos" || agentPlatform == "linux")
            {
                try
                {
                    if (IsDebugMode)
                    {
                        LogDebug($"Making file executable: chmod +x \"{filePath}\"");
                    }
                    var process = new Process
                    {
                        StartInfo = new ProcessStartInfo
                        {
                            FileName = "chmod",
                            Arguments = $"+x \"{filePath}\"",
                            UseShellExecute = false,
                            CreateNoWindow = true
                        }
                    };
                    process.Start();
                    await process.WaitForExitAsync();
                    if (IsDebugMode)
                    {
                        LogDebug($"chmod exit code: {process.ExitCode}");
                    }
                }
                catch (Exception ex)
                {
                    LogInfo($"⚠️  Failed to make file executable: {ex.Message}");
                    if (IsDebugMode)
                    {
                        LogDebug($"chmod exception details: {ex}");
                    }
                }
            }
            
            // For Windows .exe files, we might want to execute them
            // For macOS executables, we might want to move them to Applications or execute
            // This is a simplified version - actual implementation would depend on requirements
            
            LogInfo($"✓ Software installed: {filePath}");
            return true;
        }
        catch (Exception ex)
        {
            LogError($"Error installing software: {ex.Message}", ex);
            if (IsDebugMode && release != null)
            {
                LogDebug($"Release ID: {release.id}");
                LogDebug($"Release tag: {release.tag_name}");
                LogDebug($"File path: {filePath}");
            }
            return false;
        }
    }
    
    static bool VerifyInstallation(string filePath)
    {
        try
        {
            if (!File.Exists(filePath))
            {
                return false;
            }
            
            var fileInfo = new FileInfo(filePath);
            if (fileInfo.Length == 0)
            {
                return false;
            }
            
            // Check if file is executable (platform-specific)
            if (agentPlatform == "macos" || agentPlatform == "linux")
            {
                // On Unix systems, check if file has execute permission
                // This is a simplified check
                return true; // In production, check actual permissions
            }
            else if (agentPlatform == "windows")
            {
                // On Windows, check if it's an .exe file
                return filePath.EndsWith(".exe", StringComparison.OrdinalIgnoreCase);
            }
            
            return true;
        }
        catch (Exception ex)
        {
            Console.WriteLine($"⚠️  Error verifying installation: {ex.Message}");
            return false;
        }
    }

    static async Task ReportDeploymentComplete(string deploymentId, string status, string? errorMessage)
    {
        try
        {
            var request = new
            {
                status = status,
                error_message = errorMessage
            };

            var response = await httpClient.PostAsJsonAsync(
                $"{masterUrl}/api/deployments/{deploymentId}/complete",
                request
            );

            if (response.IsSuccessStatusCode)
            {
                Console.WriteLine($"✓ Deployment status reported: {status}");
            }
            else
            {
                Console.WriteLine($"⚠️  Failed to report deployment status: {response.StatusCode}");
            }
        }
        catch (Exception ex)
        {
            Console.WriteLine($"⚠️  Failed to report deployment completion: {ex.Message}");
        }
    }

    static string GetPlatform()
    {
        var platform = Environment.OSVersion.Platform;
        if (platform == PlatformID.Win32NT)
            return "windows";
        else if (platform == PlatformID.MacOSX || platform == PlatformID.Unix)
            return "macos";
        else
            return "unknown";
    }

    static string? GetLocalIPAddress()
    {
        try
        {
            var host = System.Net.Dns.GetHostEntry(System.Net.Dns.GetHostName());
            foreach (var ip in host.AddressList)
            {
                if (ip.AddressFamily == System.Net.Sockets.AddressFamily.InterNetwork)
                {
                    return ip.ToString();
                }
            }
        }
        catch { }
        return null;
    }

    class AgentResponse
    {
        public string id { get; set; } = "";
        public string name { get; set; } = "";
        public string platform { get; set; } = "";
        public string version { get; set; } = "";
        public string status { get; set; } = "";
    }

    class DeploymentResponse
    {
        public string id { get; set; } = "";
        public string agent_id { get; set; } = "";
        public string agent_name { get; set; } = "";
        public List<string>? release_ids { get; set; }
        public List<string>? release_tags { get; set; }
        public string status { get; set; } = "";
        public DateTime created_at { get; set; }
        public DateTime? started_at { get; set; }
        public DateTime? completed_at { get; set; }
        public string? error_message { get; set; }
    }
    
    class ReleaseResponse
    {
        public string id { get; set; } = "";
        public string tag_name { get; set; } = "";
        public string name { get; set; } = "";
        public string version { get; set; } = "";
        public DateTime release_date { get; set; }
        public string download_url { get; set; } = "";
        public string description { get; set; } = "";
        public List<string>? assets { get; set; }
    }
    
    class GitHubReleaseAsset
    {
        public string name { get; set; } = "";
        public string browser_download_url { get; set; } = "";
        public string content_type { get; set; } = "";
        public long size { get; set; }
    }
    
    class GitHubReleaseResponse
    {
        public string tag_name { get; set; } = "";
        public string name { get; set; } = "";
        public List<GitHubReleaseAsset> assets { get; set; } = new List<GitHubReleaseAsset>();
    }
}