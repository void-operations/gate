using System;
using System.Net.Http;
using System.Net.Http.Json;
using System.Text.Json.Serialization;
using System.Threading;
using System.Threading.Tasks;
using System.IO;
using System.Diagnostics;
using System.Text.RegularExpressions;
using Newtonsoft.Json;

namespace Agent;

/// <summary>
/// Agent - Client that connects to Master server and reports status
/// </summary>
class Program
{
    private static readonly HttpClient httpClient = new HttpClient();
    private static string masterUrl = "http://localhost:8000";
    private static string agentName = Environment.MachineName;
    private static string agentPlatform = GetPlatform();
    private static string agentVersion = "1.0.0";
    private static string agentId = "";
    private static bool running = true;

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
            foreach (var releaseId in deployment.release_ids)
            {
                Console.WriteLine($"📦 Processing release: {releaseId}");
                
                // 1. Fetch release details from Master
                var release = await FetchReleaseDetails(releaseId);
                if (release == null)
                {
                    throw new Exception($"Failed to fetch release details for {releaseId}");
                }
                
                // 2. Download release artifacts from GitHub
                var downloadPath = await DownloadReleaseArtifacts(release);
                if (string.IsNullOrEmpty(downloadPath))
                {
                    throw new Exception($"Failed to download artifacts for {releaseId}");
                }
                
                // 3. Install/execute software based on platform
                var installSuccess = await InstallSoftware(downloadPath, release);
                if (!installSuccess)
                {
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
            Console.WriteLine($"❌ Deployment execution failed: {ex.Message}");
            await ReportDeploymentComplete(deployment.id, "failed", ex.Message);
        }
    }
    
    static async Task<ReleaseResponse?> FetchReleaseDetails(string releaseId)
    {
        try
        {
            var response = await httpClient.GetAsync($"{masterUrl}/api/releases/{releaseId}");
            
            if (response.IsSuccessStatusCode)
            {
                var content = await response.Content.ReadAsStringAsync();
                return JsonConvert.DeserializeObject<ReleaseResponse>(content);
            }
            else
            {
                Console.WriteLine($"⚠️  Failed to fetch release details: {response.StatusCode}");
                return null;
            }
        }
        catch (Exception ex)
        {
            Console.WriteLine($"⚠️  Error fetching release details: {ex.Message}");
            return null;
        }
    }
    
    static async Task<string?> DownloadReleaseArtifacts(ReleaseResponse release)
    {
        try
        {
            if (string.IsNullOrEmpty(release.download_url))
            {
                throw new Exception("Release download URL is empty");
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
            
            // For now, we'll download the latest release asset
            // In a full implementation, we would use GitHub API to get specific release assets
            // For simplicity, we'll construct a direct download URL for the latest release
            // This is a placeholder - actual implementation should use GitHub API
            
            Console.WriteLine($"📥 Downloading from GitHub: {owner}/{repo}");
            Console.WriteLine($"⚠️  Note: Full GitHub API integration needed for specific release versions");
            
            // Create a placeholder file path
            // In production, this should download actual artifacts from GitHub releases
            var downloadPath = Path.Combine(downloadsDir, $"{repo}-{release.tag_name}");
            
            // For now, return the path (actual download would happen here)
            // TODO: Implement actual GitHub release asset download
            // Simulate async operation
            await Task.CompletedTask;
            return downloadPath;
        }
        catch (Exception ex)
        {
            Console.WriteLine($"❌ Error downloading artifacts: {ex.Message}");
            return null;
        }
    }
    
    static async Task<bool> InstallSoftware(string filePath, ReleaseResponse release)
    {
        try
        {
            if (!File.Exists(filePath))
            {
                Console.WriteLine($"⚠️  File not found: {filePath}");
                return false;
            }
            
            // Make file executable on macOS/Linux
            if (agentPlatform == "macos" || agentPlatform == "linux")
            {
                try
                {
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
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"⚠️  Failed to make file executable: {ex.Message}");
                }
            }
            
            // For Windows .exe files, we might want to execute them
            // For macOS executables, we might want to move them to Applications or execute
            // This is a simplified version - actual implementation would depend on requirements
            
            Console.WriteLine($"✓ Software installed: {filePath}");
            return true;
        }
        catch (Exception ex)
        {
            Console.WriteLine($"❌ Error installing software: {ex.Message}");
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
}