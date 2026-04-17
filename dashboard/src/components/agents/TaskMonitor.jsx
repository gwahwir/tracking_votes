import { useState, useEffect } from 'react'
import { Box, Group, Badge, Text, Stack, ScrollArea, Loader, ThemeIcon } from '@mantine/core'
import { useTaskStream } from '../../hooks/useApi'
import './TaskMonitor.css'

/**
 * Real-time task monitor with NODE_OUTPUT streaming
 * Displays live progress as agents execute tasks
 */
export default function TaskMonitor({ taskId, agentType }) {
  const { status, nodeOutputs, error } = useTaskStream(taskId)
  const [autoScroll, setAutoScroll] = useState(true)

  if (!taskId) {
    return (
      <Box className="task-monitor">
        <Text size="xs" c="dimmed" ta="center">
          No active task
        </Text>
      </Box>
    )
  }

  const statusColor = {
    pending: 'gray',
    running: 'cyan',
    completed: 'green',
    failed: 'red',
    cancelled: 'orange',
  }[status] || 'gray'

  const statusDisplay = {
    pending: 'Pending...',
    running: 'Running',
    completed: 'Completed',
    failed: 'Failed',
    cancelled: 'Cancelled',
  }[status] || 'Unknown'

  return (
    <Box className="task-monitor">
      <Stack gap="xs" style={{ height: '100%' }}>
        {/* Header with status */}
        <Group justify="space-between" align="center">
          <Group gap="xs">
            {status === 'running' && <Loader size="xs" color="cyan" />}
            {status === 'completed' && (
              <ThemeIcon size="xs" color="green" variant="light">
                ✓
              </ThemeIcon>
            )}
            {status === 'failed' && (
              <ThemeIcon size="xs" color="red" variant="light">
                ✕
              </ThemeIcon>
            )}
            <Text size="sm" fw={500}>
              Task {taskId.slice(0, 8)}... • {agentType || 'Agent'}
            </Text>
          </Group>
          <Badge color={statusColor} size="xs">
            {statusDisplay}
          </Badge>
        </Group>

        {/* Error display */}
        {error && (
          <Box className="error-banner">
            <Text size="xs" c="red">
              {error}
            </Text>
          </Box>
        )}

        {/* NODE_OUTPUT stream */}
        <ScrollArea className="node-output-scroll">
          <Stack gap="xs" className="node-output-list">
            {nodeOutputs.length === 0 ? (
              <Text size="xs" c="dimmed">
                {status === 'running'
                  ? 'Waiting for output...'
                  : 'No output received'}
              </Text>
            ) : (
              nodeOutputs.map((output, idx) => (
                <NodeOutputLine key={idx} output={output} />
              ))
            )}
          </Stack>
        </ScrollArea>
      </Stack>
    </Box>
  )
}

/**
 * Individual NODE_OUTPUT:: line
 * Format: NODE_OUTPUT::node_name::output_text
 */
function NodeOutputLine({ output }) {
  // Parse NODE_OUTPUT::node::content format
  const match = output.match(/NODE_OUTPUT::([^:]+)::(.+)/)
  if (!match) {
    return (
      <Text size="xs" className="output-line">
        {output}
      </Text>
    )
  }

  const [, node, content] = match
  const nodeColorMap = {
    'retrieve_wiki': 'cyan',
    'score': 'green',
    'political': 'blue',
    'demographic': 'purple',
    'historical': 'orange',
    'strategic': 'red',
    'factcheck': 'yellow',
    'bridget_welsh': 'indigo',
    'gather_signals': 'teal',
    'load_baseline': 'lime',
    'assess': 'pink',
    'store': 'gray',
  }[node] || 'gray'

  return (
    <Group gap="xs" align="flex-start" className="output-line">
      <Badge size="xs" color={nodeColorMap} variant="light" className="node-badge">
        {node}
      </Badge>
      <Text size="xs" className="output-text" style={{ flex: 1 }}>
        {content}
      </Text>
    </Group>
  )
}
