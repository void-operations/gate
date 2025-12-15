import { useState, useEffect } from 'react'
import axios from 'axios'
import { Button } from '@/components/ui/button'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Checkbox } from '@/components/ui/checkbox'
import { Eye, EyeOff } from 'lucide-react'

const API_BASE = 'http://localhost:8000/api'

function App() {
  const [currentSection, setCurrentSection] = useState('releases')
  const [health, setHealth] = useState({ status: 'unknown', agents_count: 0 })
  const [releases, setReleases] = useState([])
  const [agents, setAgents] = useState([])
  const [deployments, setDeployments] = useState([])
  const [releaseModalOpen, setReleaseModalOpen] = useState(false)
  const [deploymentModalOpen, setDeploymentModalOpen] = useState(false)
  const [selectedReleases, setSelectedReleases] = useState([])
  const [selectedAgent, setSelectedAgent] = useState('')
  const [releaseForm, setReleaseForm] = useState({
    tag_name: '',
    name: '',
    version: '',
    description: '',
    download_url: '',
  })
  const [githubToken, setGithubToken] = useState('')
  const [githubTokenPreview, setGithubTokenPreview] = useState('')
  const [hasGitHubToken, setHasGitHubToken] = useState(false)
  const [showGitHubToken, setShowGitHubToken] = useState(false)
  const [deploymentFilters, setDeploymentFilters] = useState({
    agent: '',
    dateFrom: '',
    software: '',
    softwareVersion: '',
  })

  // Load data
  useEffect(() => {
    updateHealth()
    loadReleases()
    loadAgents()
    loadDeployments()
    loadGitHubToken()

    const interval = setInterval(() => {
      updateHealth()
      if (currentSection === 'releases') loadReleases()
      if (currentSection === 'agents') loadAgents()
      if (currentSection === 'deployments') loadDeployments()
      if (currentSection === 'settings') loadGitHubToken()
    }, 5000)

    return () => clearInterval(interval)
  }, [currentSection])

  async function updateHealth() {
    try {
      const response = await axios.get(`${API_BASE}/health`)
      setHealth({ status: 'healthy', agents_count: response.data.agents_count })
    } catch (error) {
      setHealth({ status: 'error', agents_count: 0 })
    }
  }

  async function loadReleases() {
    try {
      const response = await axios.get(`${API_BASE}/releases`)
      setReleases(response.data)
    } catch (error) {
      console.error('Failed to load releases:', error)
    }
  }

  async function loadAgents() {
    try {
      const response = await axios.get(`${API_BASE}/agents`)
      setAgents(response.data)
    } catch (error) {
      console.error('Failed to load agents:', error)
    }
  }

  async function loadDeployments() {
    try {
      const response = await axios.get(`${API_BASE}/deployments/history`)
      setDeployments(response.data)
    } catch (error) {
      console.error('Failed to load deployments:', error)
    }
  }

  async function createRelease(e) {
    e.preventDefault()
    try {
      const releaseData = {
        tag_name: releaseForm.tag_name,
        name: releaseForm.name,
        version: releaseForm.version,
        description: releaseForm.description || null,
        download_url: releaseForm.download_url || null,
        assets: [],
      }
      await axios.post(`${API_BASE}/releases`, releaseData)
      setReleaseModalOpen(false)
      setReleaseForm({ tag_name: '', name: '', version: '', description: '', download_url: '' })
      await loadReleases()
    } catch (error) {
      console.error('Failed to create release:', error)
      alert('Failed to create release: ' + (error.response?.data?.detail || error.message))
    }
  }

  async function deleteRelease(releaseId) {
    if (!confirm('Are you sure you want to remove this release?')) {
      return
    }
    try {
      await axios.delete(`${API_BASE}/releases/${releaseId}`)
      await loadReleases()
    } catch (error) {
      console.error('Failed to delete release:', error)
      alert('Failed to delete release')
    }
  }

  async function deleteAgent(agentId) {
    if (!confirm('Are you sure you want to remove this agent?')) {
      return
    }
    try {
      await axios.delete(`${API_BASE}/agents/${agentId}`)
      await loadAgents()
    } catch (error) {
      console.error('Failed to delete agent:', error)
      alert('Failed to delete agent')
    }
  }

  async function createDeployment(e) {
    e.preventDefault()
    if (!selectedAgent || selectedReleases.length === 0) {
      alert('Please select an agent and at least one release')
      return
    }
    try {
      const deploymentData = {
        agent_id: selectedAgent,
        release_ids: selectedReleases,
      }
      await axios.post(`${API_BASE}/deployments`, deploymentData)
      setDeploymentModalOpen(false)
      setSelectedAgent('')
      setSelectedReleases([])
      await loadDeployments()
    } catch (error) {
      console.error('Failed to create deployment:', error)
      alert('Failed to create deployment: ' + (error.response?.data?.detail || error.message))
    }
  }

  function handleReleaseToggle(releaseId) {
    setSelectedReleases((prev) =>
      prev.includes(releaseId)
        ? prev.filter((id) => id !== releaseId)
        : [...prev, releaseId]
    )
  }

  async function loadGitHubToken() {
    try {
      const response = await axios.get(`${API_BASE}/settings/github-token`)
      setHasGitHubToken(response.data.has_token)
      if (response.data.has_token) {
        setGithubTokenPreview(response.data.token_preview)
      }
    } catch (error) {
      console.error('Failed to load GitHub token:', error)
    }
  }

  async function saveGitHubToken(e) {
    e.preventDefault()
    try {
      await axios.post(`${API_BASE}/settings/github-token`, { token: githubToken })
      setGithubToken('')
      await loadGitHubToken()
      alert('GitHub token saved successfully')
    } catch (error) {
      console.error('Failed to save GitHub token:', error)
      alert('Failed to save GitHub token: ' + (error.response?.data?.detail || error.message))
    }
  }

  async function updateGitHubToken(e) {
    e.preventDefault()
    try {
      await axios.post(`${API_BASE}/settings/github-token`, { token: githubToken })
      setGithubToken('')
      await loadGitHubToken()
      alert('GitHub token updated successfully')
    } catch (error) {
      console.error('Failed to update GitHub token:', error)
      alert('Failed to update GitHub token: ' + (error.response?.data?.detail || error.message))
    }
  }

  async function removeGitHubToken() {
    if (!confirm('Are you sure you want to remove the GitHub token?')) {
      return
    }
    try {
      await axios.delete(`${API_BASE}/settings/github-token`)
      setHasGitHubToken(false)
      setGithubTokenPreview('')
      alert('GitHub token removed successfully')
    } catch (error) {
      console.error('Failed to remove GitHub token:', error)
      alert('Failed to remove GitHub token')
    }
  }

  const sections = [
    { id: 'releases', icon: '📦', label: 'Release Management' },
    { id: 'agents', icon: '🤖', label: 'Agent Management' },
    { id: 'deployments', icon: '🚀', label: 'Deployment' },
    { id: 'settings', icon: '⚙️', label: 'Settings' },
  ]

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b bg-card">
        <div className="container mx-auto px-4 py-4 flex justify-between items-center">
          <h1 className="text-2xl font-bold text-primary">🔧 Master Agent Manager</h1>
          <div className="flex items-center gap-4">
            <span className={`text-sm ${health.status === 'healthy' ? 'text-green-600' : 'text-red-600'}`}>
              ● {health.status === 'healthy' ? 'Healthy' : 'Error'}
            </span>
            <span className="text-sm text-muted-foreground">Agents: {health.agents_count}</span>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-4 py-6 flex gap-6">
        {/* Sidebar */}
        <aside className="w-64 flex-shrink-0">
          <nav className="space-y-1">
            {sections.map((section) => (
              <button
                key={section.id}
                onClick={() => setCurrentSection(section.id)}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-md text-left transition-colors ${
                  currentSection === section.id
                    ? 'bg-primary text-primary-foreground'
                    : 'hover:bg-accent text-muted-foreground hover:text-foreground'
                }`}
              >
                <span className="text-xl">{section.icon}</span>
                <span>{section.label}</span>
              </button>
            ))}
          </nav>
        </aside>

        {/* Main Content */}
        <main className="flex-1 min-w-0">
          {currentSection === 'releases' && (
            <div>
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-2xl font-bold">Release Management</h2>
                <Dialog open={releaseModalOpen} onOpenChange={setReleaseModalOpen}>
                  <DialogTrigger asChild>
                    <Button>Add Release</Button>
                  </DialogTrigger>
                  <DialogContent>
                    <DialogHeader>
                      <DialogTitle>Add Release</DialogTitle>
                      <DialogDescription>
                        Add a new GitHub release to the system
                      </DialogDescription>
                    </DialogHeader>
                    <form onSubmit={createRelease} className="space-y-4">
                      <div className="space-y-2">
                        <Label htmlFor="tag-name">Tag Name *</Label>
                        <Input
                          id="tag-name"
                          value={releaseForm.tag_name}
                          onChange={(e) => setReleaseForm({ ...releaseForm, tag_name: e.target.value })}
                          required
                        />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="release-name">Name *</Label>
                        <Input
                          id="release-name"
                          value={releaseForm.name}
                          onChange={(e) => setReleaseForm({ ...releaseForm, name: e.target.value })}
                          required
                        />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="release-version">Version *</Label>
                        <Input
                          id="release-version"
                          value={releaseForm.version}
                          onChange={(e) => setReleaseForm({ ...releaseForm, version: e.target.value })}
                          required
                        />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="release-description">Description</Label>
                        <Textarea
                          id="release-description"
                          value={releaseForm.description}
                          onChange={(e) => setReleaseForm({ ...releaseForm, description: e.target.value })}
                          rows={3}
                        />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="release-download-url">Download URL</Label>
                        <Input
                          id="release-download-url"
                          type="url"
                          value={releaseForm.download_url}
                          onChange={(e) => setReleaseForm({ ...releaseForm, download_url: e.target.value })}
                        />
                      </div>
                      <div className="flex justify-end gap-2">
                        <Button
                          type="button"
                          variant="outline"
                          onClick={() => setReleaseModalOpen(false)}
                        >
                          Cancel
                        </Button>
                        <Button type="submit">Add Release</Button>
                      </div>
                    </form>
                  </DialogContent>
                </Dialog>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {releases.length === 0 ? (
                  <p className="text-muted-foreground">No releases added</p>
                ) : (
                  releases.map((release) => (
                    <Card key={release.id}>
                      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle>{release.name}</CardTitle>
                        <Button
                          variant="destructive"
                          size="sm"
                          onClick={() => deleteRelease(release.id)}
                        >
                          Remove
                        </Button>
                      </CardHeader>
                      <CardContent>
                        <p className="text-sm text-muted-foreground">Tag: {release.tag_name}</p>
                        <p className="text-sm text-muted-foreground">Version: {release.version}</p>
                        {release.description && (
                          <p className="text-sm text-muted-foreground mt-2">{release.description}</p>
                        )}
                        {release.download_url && (
                          <a
                            href={release.download_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-sm text-primary hover:underline mt-2 block"
                          >
                            Download
                          </a>
                        )}
                      </CardContent>
                    </Card>
                  ))
                )}
              </div>
            </div>
          )}

          {currentSection === 'agents' && (
            <div>
              <h2 className="text-2xl font-bold mb-6">Agent Management</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {agents.length === 0 ? (
                  <p className="text-muted-foreground">No agents registered</p>
                ) : (
                  agents.map((agent) => (
                    <Card key={agent.id}>
                      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle>{agent.name}</CardTitle>
                        <Button
                          variant="destructive"
                          size="sm"
                          onClick={() => deleteAgent(agent.id)}
                        >
                          Remove
                        </Button>
                      </CardHeader>
                      <CardContent>
                        <p className="text-sm text-muted-foreground">Platform: {agent.platform}</p>
                        <p className="text-sm text-muted-foreground">Status: {agent.status}</p>
                      </CardContent>
                    </Card>
                  ))
                )}
              </div>
            </div>
          )}

          {currentSection === 'deployments' && (
            <div>
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-2xl font-bold">Deployment</h2>
                <Dialog open={deploymentModalOpen} onOpenChange={setDeploymentModalOpen}>
                  <DialogTrigger asChild>
                    <Button>New Deployment</Button>
                  </DialogTrigger>
                  <DialogContent className="max-w-2xl">
                    <DialogHeader>
                      <DialogTitle>New Deployment</DialogTitle>
                      <DialogDescription>
                        Select an agent and one or more releases to deploy (Batch Deployment)
                      </DialogDescription>
                    </DialogHeader>
                    <form onSubmit={createDeployment} className="space-y-4">
                      <div className="space-y-2">
                        <Label htmlFor="deployment-agent">Agent *</Label>
                        <Select value={selectedAgent} onValueChange={setSelectedAgent} required>
                          <SelectTrigger id="deployment-agent">
                            <SelectValue placeholder="Select an agent..." />
                          </SelectTrigger>
                          <SelectContent>
                            {agents.map((agent) => (
                              <SelectItem key={agent.id} value={agent.id}>
                                {agent.name} ({agent.platform})
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                      <div className="space-y-2">
                        <Label>Releases * (Multiple selection)</Label>
                        <div className="border rounded-md p-4 max-h-60 overflow-y-auto space-y-2">
                          {releases.length === 0 ? (
                            <p className="text-sm text-muted-foreground">No releases available. Please add a release first.</p>
                          ) : (
                            releases.map((release) => (
                              <div key={release.id} className="flex items-center space-x-2">
                                <Checkbox
                                  id={`release-${release.id}`}
                                  checked={selectedReleases.includes(release.id)}
                                  onCheckedChange={() => handleReleaseToggle(release.id)}
                                />
                                <label
                                  htmlFor={`release-${release.id}`}
                                  className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer"
                                >
                                  {release.name} ({release.tag_name})
                                </label>
                              </div>
                            ))
                          )}
                        </div>
                      </div>
                      <div className="flex justify-end gap-2">
                        <Button
                          type="button"
                          variant="outline"
                          onClick={() => {
                            setDeploymentModalOpen(false)
                            setSelectedAgent('')
                            setSelectedReleases([])
                          }}
                        >
                          Cancel
                        </Button>
                        <Button type="submit">Deploy</Button>
                      </div>
                    </form>
                  </DialogContent>
                </Dialog>
              </div>
              <Card className="mb-4">
                <CardHeader>
                  <CardTitle>Filter Deployment History</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="filter-agent">Agent</Label>
                      <Select
                        value={deploymentFilters.agent}
                        onValueChange={(value) => setDeploymentFilters({ ...deploymentFilters, agent: value })}
                      >
                        <SelectTrigger id="filter-agent">
                          <SelectValue placeholder="All agents" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="">All agents</SelectItem>
                          {agents.map((agent) => (
                            <SelectItem key={agent.id} value={agent.id}>
                              {agent.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="filter-date-from">Date From</Label>
                      <Input
                        id="filter-date-from"
                        type="date"
                        value={deploymentFilters.dateFrom}
                        onChange={(e) => setDeploymentFilters({ ...deploymentFilters, dateFrom: e.target.value })}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="filter-software">Software</Label>
                      <Input
                        id="filter-software"
                        value={deploymentFilters.software}
                        onChange={(e) => setDeploymentFilters({ ...deploymentFilters, software: e.target.value })}
                        placeholder="Filter by software name"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="filter-version">Software Version</Label>
                      <Input
                        id="filter-version"
                        value={deploymentFilters.softwareVersion}
                        onChange={(e) => setDeploymentFilters({ ...deploymentFilters, softwareVersion: e.target.value })}
                        placeholder="Filter by version"
                      />
                    </div>
                  </div>
                </CardContent>
              </Card>
              <div className="space-y-4">
                {deployments.length === 0 ? (
                  <p className="text-muted-foreground">No deployments yet</p>
                ) : (
                  deployments
                    .filter((deployment) => {
                      if (deploymentFilters.agent && deployment.agent_id !== deploymentFilters.agent) return false
                      if (deploymentFilters.dateFrom) {
                        const filterDate = new Date(deploymentFilters.dateFrom)
                        const deployDate = new Date(deployment.created_at)
                        if (deployDate < filterDate) return false
                      }
                      if (deploymentFilters.software) {
                        const releaseTags = deployment.release_tags?.join(' ') || ''
                        if (!releaseTags.toLowerCase().includes(deploymentFilters.software.toLowerCase())) return false
                      }
                      if (deploymentFilters.softwareVersion) {
                        const releaseTags = deployment.release_tags?.join(' ') || ''
                        if (!releaseTags.includes(deploymentFilters.softwareVersion)) return false
                      }
                      return true
                    })
                    .map((deployment) => (
                      <Card key={deployment.id}>
                        <CardHeader>
                          <CardTitle>Deployment to {deployment.agent_name}</CardTitle>
                        </CardHeader>
                        <CardContent>
                          <p className="text-sm text-muted-foreground">
                            Releases: {deployment.release_tags?.join(', ') || deployment.release_ids?.join(', ')}
                          </p>
                          <p className="text-sm text-muted-foreground">Status: {deployment.status}</p>
                          <p className="text-sm text-muted-foreground">
                            Created: {new Date(deployment.created_at).toLocaleString()}
                          </p>
                          {deployment.error_message && (
                            <p className="text-sm text-red-600 mt-2">Error: {deployment.error_message}</p>
                          )}
                        </CardContent>
                      </Card>
                    ))
                )}
              </div>
            </div>
          )}

          {currentSection === 'settings' && (
            <div>
              <h2 className="text-2xl font-bold mb-6">Settings</h2>
              <Card>
                <CardHeader>
                  <CardTitle>GitHub Token</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  {hasGitHubToken ? (
                    <div className="space-y-4">
                      <div>
                        <p className="text-sm text-muted-foreground mb-2">
                          Current token: {githubTokenPreview}
                        </p>
                      </div>
                      <form onSubmit={updateGitHubToken} className="space-y-4">
                        <div className="space-y-2">
                          <Label htmlFor="github-token-update">New GitHub Token</Label>
                          <div className="relative">
                            <Input
                              id="github-token-update"
                              type={showGitHubToken ? 'text' : 'password'}
                              value={githubToken}
                              onChange={(e) => setGithubToken(e.target.value)}
                              placeholder="Enter new GitHub token"
                              className="pr-10"
                            />
                            <Button
                              type="button"
                              variant="ghost"
                              size="sm"
                              className="absolute right-0 top-0 h-full px-3 py-2 hover:bg-transparent"
                              onClick={() => setShowGitHubToken(!showGitHubToken)}
                            >
                              {showGitHubToken ? (
                                <EyeOff className="h-4 w-4 text-muted-foreground" />
                              ) : (
                                <Eye className="h-4 w-4 text-muted-foreground" />
                              )}
                            </Button>
                          </div>
                        </div>
                        <div className="flex gap-2">
                          <Button type="submit" variant="outline">
                            Update Token
                          </Button>
                          <Button
                            type="button"
                            variant="destructive"
                            onClick={removeGitHubToken}
                          >
                            Remove Token
                          </Button>
                        </div>
                      </form>
                    </div>
                  ) : (
                    <form onSubmit={saveGitHubToken} className="space-y-4">
                      <div className="space-y-2">
                        <Label htmlFor="github-token">GitHub Token</Label>
                        <div className="relative">
                          <Input
                            id="github-token"
                            type={showGitHubToken ? 'text' : 'password'}
                            value={githubToken}
                            onChange={(e) => setGithubToken(e.target.value)}
                            placeholder="Enter GitHub personal access token"
                            required
                            className="pr-10"
                          />
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            className="absolute right-0 top-0 h-full px-3 py-2 hover:bg-transparent"
                            onClick={() => setShowGitHubToken(!showGitHubToken)}
                          >
                            {showGitHubToken ? (
                              <EyeOff className="h-4 w-4 text-muted-foreground" />
                            ) : (
                              <Eye className="h-4 w-4 text-muted-foreground" />
                            )}
                          </Button>
                        </div>
                        <p className="text-xs text-muted-foreground">
                          Required for accessing GitHub releases
                        </p>
                      </div>
                      <Button type="submit">Add Token</Button>
                    </form>
                  )}
                </CardContent>
              </Card>
            </div>
          )}
        </main>
      </div>
    </div>
  )
}

export default App

