import { useState, useCallback } from 'react'
import { Box, Group, Badge, Text, Stack, ActionIcon, Tooltip } from '@mantine/core'
import {
  ReactFlow,
  Controls,
  Background,
  Handle,
  Position,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { useAgentGraph } from '../../hooks/useApi'
import './AgentGraph.css'

/**
 * Custom node component for agent visualization
 */
function AgentNode({ data }) {
  const isHealthy = data.healthy
  return (
    <div className="agent-node">
      <Handle type="target" position={Position.Top} />
      <div className="agent-node-content">
        <div className={`agent-node-dot ${isHealthy ? 'healthy' : 'unhealthy'}`} />
        <div className="agent-node-label">
          <div className="agent-node-name">{data.label}</div>
          <div className="agent-node-tasks">{data.task_count || 0} task{data.task_count !== 1 ? 's' : ''}</div>
        </div>
      </div>
      <Handle type="source" position={Position.Bottom} />
    </div>
  )
}

/**
 * Agent topology visualization with @xyflow/react
 * Shows real-time agent health and task counts
 */
function AgentGraph() {
  const { graph, loading, error, refetch } = useAgentGraph()
  const [autoLayout, setAutoLayout] = useState(true)

  // Convert graph data to ReactFlow nodes and edges
  const computeNodesAndEdges = useCallback(() => {
    if (!graph) return { nodes: [], edges: [] }

    const flowNodes = graph.nodes.map((node, idx) => {
      const isControlPlane = node.type_id === 'control_plane'
      const angle = isControlPlane ? 0 : ((idx - 1) * (360 / (graph.nodes.length - 1))) * (Math.PI / 180)
      const radius = isControlPlane ? 0 : 200

      return {
        id: node.id,
        data: {
          label: node.data.label,
          healthy: node.data.healthy,
          task_count: node.data.task_count,
        },
        position: isControlPlane
          ? { x: 0, y: 0 }
          : {
              x: Math.cos(angle) * radius,
              y: Math.sin(angle) * radius,
            },
      }
    })

    const flowEdges = graph.edges.map((edge) => ({
      id: edge.id,
      source: edge.source,
      target: edge.target,
      animated: true,
    }))

    return { nodes: flowNodes, edges: flowEdges }
  }, [graph])

  const { nodes, edges } = computeNodesAndEdges()

  if (error) {
    return (
      <Box className="agent-graph-error">
        <Text size="xs" c="red">
          Failed to load agent graph: {error}
        </Text>
      </Box>
    )
  }

  if (loading || !graph) {
    return (
      <Box className="agent-graph-loading">
        <Text size="xs">Loading agent topology...</Text>
      </Box>
    )
  }

  return (
    <Box className="agent-graph-container">
      <Group justify="space-between" align="center" className="graph-header">
        <Text size="sm" fw={500}>
          Agent Topology • {graph.nodes.length} agents
        </Text>
        <Group gap={4}>
          <Tooltip label="Refresh topology">
            <ActionIcon size="xs" variant="light" onClick={refetch}>
              🔄
            </ActionIcon>
          </Tooltip>
          <Tooltip label="Auto-layout">
            <ActionIcon
              size="xs"
              variant={autoLayout ? 'filled' : 'light'}
              color="cyan"
              onClick={() => setAutoLayout(!autoLayout)}
            >
              📐
            </ActionIcon>
          </Tooltip>
        </Group>
      </Group>

      <ReactFlow
        nodes={nodes}
        edges={edges}
        fitView
        className="reactflow-graph"
        nodeTypes={{ default: AgentNode }}
      >
        <Background color="#1a1a20" gap={16} />
        <Controls />
      </ReactFlow>

      {/* Agent status legend */}
      <Stack gap={6} className="agent-legend">
        {graph.nodes
          .filter((n) => n.type_id !== 'control_plane')
          .map((agent) => (
            <AgentStatusBadge key={agent.id} agent={agent} />
          ))}
      </Stack>
    </Box>
  )
}

/**
 * Individual agent status badge
 */
function AgentStatusBadge({ agent }) {
  const healthColor = agent.data.healthy ? 'green' : 'red'
  const lastSeen = agent.data.last_seen
    ? new Date(agent.data.last_seen).toLocaleTimeString()
    : 'unknown'

  return (
    <Group gap={6} align="center" className="agent-status-badge">
      <div
        className="health-dot"
        style={{
          backgroundColor: healthColor === 'green' ? '#39ff14' : '#ff3131',
        }}
      />
      <Text size="xs" style={{ flex: 1 }}>
        {agent.data.label}
      </Text>
      <Badge size="xs" color={healthColor} variant="light">
        {agent.data.task_count || 0} task{agent.data.task_count !== 1 ? 's' : ''}
      </Badge>
      <Text size="xs" c="dimmed">
        {lastSeen}
      </Text>
    </Group>
  )
}

export default AgentGraph
