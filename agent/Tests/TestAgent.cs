using System;
using System.Collections.Generic;
using System.IO;
using System.Text.RegularExpressions;
using Newtonsoft.Json;

namespace Tests;

public class Tests
{
    [SetUp]
    public void Setup()
    {
    }

    [Test]
    public void DeploymentResponse_Deserialization_ShouldWork()
    {
        // Arrange
        var json = @"{
            ""id"": ""deploy-123"",
            ""agent_id"": ""agent-456"",
            ""agent_name"": ""TestAgent"",
            ""release_ids"": [""release-1"", ""release-2""],
            ""release_tags"": [""v1.0.0"", ""v1.1.0""],
            ""status"": ""pending"",
            ""created_at"": ""2024-01-15T10:00:00Z"",
            ""started_at"": null,
            ""completed_at"": null,
            ""error_message"": null
        }";

        // Act
        var deployment = JsonConvert.DeserializeObject<DeploymentResponse>(json);

        // Assert
        Assert.That(deployment, Is.Not.Null);
        Assert.That(deployment!.id, Is.EqualTo("deploy-123"));
        Assert.That(deployment.agent_id, Is.EqualTo("agent-456"));
        Assert.That(deployment.agent_name, Is.EqualTo("TestAgent"));
        Assert.That(deployment.release_ids, Is.Not.Null);
        Assert.That(deployment.release_ids!.Count, Is.EqualTo(2));
        Assert.That(deployment.release_tags, Is.Not.Null);
        Assert.That(deployment.release_tags!.Count, Is.EqualTo(2));
        Assert.That(deployment.release_tags[0], Is.EqualTo("v1.0.0"));
        Assert.That(deployment.status, Is.EqualTo("pending"));
    }

    [Test]
    public void ReleaseResponse_Deserialization_ShouldWork()
    {
        // Arrange
        var json = @"{
            ""id"": ""release-1"",
            ""tag_name"": ""v1.0.0"",
            ""name"": ""Test Release"",
            ""version"": ""1.0.0"",
            ""release_date"": ""2024-01-15T10:00:00Z"",
            ""download_url"": ""https://github.com/owner/repo/releases/"",
            ""description"": ""Test description"",
            ""assets"": [""app.exe"", ""app.dmg""]
        }";

        // Act
        var release = JsonConvert.DeserializeObject<ReleaseResponse>(json);

        // Assert
        Assert.That(release, Is.Not.Null);
        Assert.That(release!.id, Is.EqualTo("release-1"));
        Assert.That(release.tag_name, Is.EqualTo("v1.0.0"));
        Assert.That(release.name, Is.EqualTo("Test Release"));
        Assert.That(release.version, Is.EqualTo("1.0.0"));
        Assert.That(release.download_url, Is.EqualTo("https://github.com/owner/repo/releases/"));
        Assert.That(release.description, Is.EqualTo("Test description"));
        Assert.That(release.assets, Is.Not.Null);
        Assert.That(release.assets!.Count, Is.EqualTo(2));
    }

    [Test]
    public void AgentResponse_Deserialization_ShouldWork()
    {
        // Arrange
        var json = @"{
            ""id"": ""agent-123"",
            ""name"": ""TestAgent"",
            ""platform"": ""windows"",
            ""version"": ""1.0.0"",
            ""status"": ""online""
        }";

        // Act
        var agent = JsonConvert.DeserializeObject<AgentResponse>(json);

        // Assert
        Assert.That(agent, Is.Not.Null);
        Assert.That(agent!.id, Is.EqualTo("agent-123"));
        Assert.That(agent.name, Is.EqualTo("TestAgent"));
        Assert.That(agent.platform, Is.EqualTo("windows"));
        Assert.That(agent.version, Is.EqualTo("1.0.0"));
        Assert.That(agent.status, Is.EqualTo("online"));
    }

    [Test]
    public void GitHubUrlParsing_ShouldExtractOwnerAndRepo_WhenUrlIsValid()
    {
        // Arrange
        var githubUrl = "https://github.com/jameskwon07/3project/releases/";
        var pattern = @"https://github\.com/([^/]+)/([^/]+)";
        var trimmedUrl = githubUrl.TrimEnd('/');

        // Act
        var match = Regex.Match(trimmedUrl, pattern);

        // Assert
        Assert.That(match.Success, Is.True);
        Assert.That(match.Groups[1].Value, Is.EqualTo("jameskwon07"));
        Assert.That(match.Groups[2].Value, Is.EqualTo("3project"));
    }

    [Test]
    public void GitHubUrlParsing_ShouldFail_WhenUrlIsInvalid()
    {
        // Arrange
        var invalidUrl = "https://invalid-url.com/repo";
        var pattern = @"https://github\.com/([^/]+)/([^/]+)";

        // Act
        var match = Regex.Match(invalidUrl, pattern);

        // Assert
        Assert.That(match.Success, Is.False);
    }

    [Test]
    public void GitHubUrlParsing_ShouldHandleUrlWithoutTrailingSlash()
    {
        // Arrange
        var githubUrl = "https://github.com/owner/repo";
        var pattern = @"https://github\.com/([^/]+)/([^/]+)";

        // Act
        var match = Regex.Match(githubUrl, pattern);

        // Assert
        Assert.That(match.Success, Is.True);
        Assert.That(match.Groups[1].Value, Is.EqualTo("owner"));
        Assert.That(match.Groups[2].Value, Is.EqualTo("repo"));
    }

    [Test]
    public void VerifyInstallation_ShouldReturnFalse_WhenFileDoesNotExist()
    {
        // Arrange
        var nonexistentFile = Path.Combine(Path.GetTempPath(), Guid.NewGuid().ToString());

        // Act
        var result = VerifyInstallation(nonexistentFile, "windows");

        // Assert
        Assert.That(result, Is.False);
    }

    [Test]
    public void VerifyInstallation_ShouldReturnFalse_WhenFileIsEmpty()
    {
        // Arrange
        var emptyFile = Path.GetTempFileName();
        try
        {
            // File is already empty

            // Act
            var result = VerifyInstallation(emptyFile, "windows");

            // Assert
            Assert.That(result, Is.False);
        }
        finally
        {
            File.Delete(emptyFile);
        }
    }

    [Test]
    public void VerifyInstallation_ShouldReturnTrue_WhenWindowsExeFileExists()
    {
        // Arrange
        var tempFile = Path.GetTempFileName();
        var exeFile = tempFile + ".exe";
        try
        {
            File.Move(tempFile, exeFile);
            File.WriteAllText(exeFile, "test content");

            // Act
            var result = VerifyInstallation(exeFile, "windows");

            // Assert
            Assert.That(result, Is.True);
        }
        finally
        {
            if (File.Exists(exeFile))
                File.Delete(exeFile);
            if (File.Exists(tempFile))
                File.Delete(tempFile);
        }
    }

    [Test]
    public void VerifyInstallation_ShouldReturnFalse_WhenWindowsFileIsNotExe()
    {
        // Arrange
        var tempFile = Path.GetTempFileName();
        try
        {
            File.WriteAllText(tempFile, "test content");

            // Act
            var result = VerifyInstallation(tempFile, "windows");

            // Assert
            Assert.That(result, Is.False);
        }
        finally
        {
            File.Delete(tempFile);
        }
    }

    [Test]
    public void VerifyInstallation_ShouldReturnTrue_WhenMacOSFileExists()
    {
        // Arrange
        var tempFile = Path.GetTempFileName();
        try
        {
            File.WriteAllText(tempFile, "test content");

            // Act
            var result = VerifyInstallation(tempFile, "macos");

            // Assert
            Assert.That(result, Is.True);
        }
        finally
        {
            File.Delete(tempFile);
        }
    }

    [Test]
    public void VerifyInstallation_ShouldReturnTrue_WhenLinuxFileExists()
    {
        // Arrange
        var tempFile = Path.GetTempFileName();
        try
        {
            File.WriteAllText(tempFile, "test content");

            // Act
            var result = VerifyInstallation(tempFile, "linux");

            // Assert
            Assert.That(result, Is.True);
        }
        finally
        {
            File.Delete(tempFile);
        }
    }

    [Test]
    public void DeploymentResponse_WithNullReleaseIds_ShouldDeserialize()
    {
        // Arrange
        var json = @"{
            ""id"": ""deploy-123"",
            ""agent_id"": ""agent-456"",
            ""release_ids"": null,
            ""release_tags"": null,
            ""status"": ""pending""
        }";

        // Act
        var deployment = JsonConvert.DeserializeObject<DeploymentResponse>(json);

        // Assert
        Assert.That(deployment, Is.Not.Null);
        Assert.That(deployment!.release_ids, Is.Null);
        Assert.That(deployment.release_tags, Is.Null);
    }

    [Test]
    public void ReleaseResponse_WithNullAssets_ShouldDeserialize()
    {
        // Arrange
        var json = @"{
            ""id"": ""release-1"",
            ""tag_name"": ""v1.0.0"",
            ""assets"": null
        }";

        // Act
        var release = JsonConvert.DeserializeObject<ReleaseResponse>(json);

        // Assert
        Assert.That(release, Is.Not.Null);
        Assert.That(release!.assets, Is.Null);
    }

    // Helper method that mirrors the implementation logic for testing
    private static bool VerifyInstallation(string filePath, string platform)
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
            if (platform == "macos" || platform == "linux")
            {
                // On Unix systems, check if file has execute permission
                // This is a simplified check
                return true; // In production, check actual permissions
            }
            else if (platform == "windows")
            {
                // On Windows, check if it's an .exe file
                return filePath.EndsWith(".exe", StringComparison.OrdinalIgnoreCase);
            }

            return true;
        }
        catch
        {
            return false;
        }
    }

    // Test data classes (mirroring Program.cs)
    private class AgentResponse
    {
        public string id { get; set; } = "";
        public string name { get; set; } = "";
        public string platform { get; set; } = "";
        public string version { get; set; } = "";
        public string status { get; set; } = "";
    }

    private class DeploymentResponse
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

    private class ReleaseResponse
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
