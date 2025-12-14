using System;
using System.Net.Http;
using System.Net.Http.Json;
using System.Text.Json.Serialization;
using System.Threading;
using System.Threading.Tasks;
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

        // Send heartbeat periodically (every 10 seconds)
        var heartbeatTask = Task.Run(async () =>
        {
            while (running)
            {
                await Task.Delay(10000);
                if (running)
                {
                    await SendHeartbeat();
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
                Console.WriteLine($"✓ Registered with Master (ID: {agent?.id})");
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
            var agentId = $"{agentPlatform}-{agentName}";
            await httpClient.DeleteAsync($"{masterUrl}/api/agents/{agentId}");
            Console.WriteLine("✓ Unregistered from Master");
        }
        catch (Exception ex)
        {
            Console.WriteLine($"⚠️  Unregistration failed: {ex.Message}");
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

    static string GetLocalIPAddress()
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
        public string id { get; set; }
        public string name { get; set; }
        public string platform { get; set; }
        public string version { get; set; }
        public string status { get; set; }
    }
}
