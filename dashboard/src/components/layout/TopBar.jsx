import { useState } from 'react'
import { Group, Text, Badge, Button, ActionIcon, Tooltip } from '@mantine/core'
import './TopBar.css'

/**
 * TopBar — Header with title, status, controls
 */
export const TopBar = ({
  status = 'LIVE',
  mapType = 'parlimen',
  useCartogram = false,
  onMapTypeChange,
  onCartogramToggle,
  onRefresh,
  onWikiOpen,
  showWikiButton = true,
}) => {
  return (
    <div className="topbar">
      <div className="topbar-left">
        <Text fw={700} c="cyan" size="xl" className="title">
          JOHOR ELECTION MONITOR
        </Text>
      </div>

      <div className="topbar-center">
        <Group gap="xs">
          <Badge
            size="lg"
            color={status === 'LIVE' ? 'lime' : 'red'}
            variant="light"
            leftSection={<StatusIndicator status={status} />}
          >
            {status}
          </Badge>
        </Group>
      </div>

      <div className="topbar-right">
        <Group gap="md">
          {/* Map Type Toggle */}
          <Group gap="xs" className="map-toggle">
            <button
              className={`toggle-btn ${mapType === 'parlimen' ? 'active' : ''}`}
              onClick={() => onMapTypeChange('parlimen')}
            >
              Parlimen
            </button>
            <button
              className={`toggle-btn ${mapType === 'dun' ? 'active' : ''}`}
              onClick={() => onMapTypeChange('dun')}
            >
              DUN
            </button>
          </Group>

          {/* Cartogram Toggle */}
          <Tooltip label={useCartogram ? 'Regular Map' : 'Cartogram'} withArrow>
            <ActionIcon
              variant={useCartogram ? 'filled' : 'light'}
              color="cyan"
              size="lg"
              onClick={onCartogramToggle}
              title="Toggle cartogram view"
            >
              {useCartogram ? '🗺' : '🗺'}
            </ActionIcon>
          </Tooltip>

          {/* Refresh */}
          <Tooltip label="Refresh data" withArrow>
            <ActionIcon
              variant="light"
              color="cyan"
              size="lg"
              onClick={onRefresh}
              title="Refresh all data"
            >
              🔄
            </ActionIcon>
          </Tooltip>

          {/* Wiki */}
          {showWikiButton && (
            <Tooltip label="Wiki knowledge base" withArrow>
              <ActionIcon
                variant="light"
                color="cyan"
                size="lg"
                onClick={onWikiOpen}
                title="Open wiki"
              >
                📚
              </ActionIcon>
            </Tooltip>
          )}
        </Group>
      </div>
    </div>
  )
}

const StatusIndicator = ({ status }) => (
  <span
    className="status-indicator"
    style={{
      display: 'inline-block',
      width: 8,
      height: 8,
      borderRadius: '50%',
      backgroundColor: status === 'LIVE' ? '#39ff14' : '#ff3131',
      animation: status === 'LIVE' ? 'pulse 1s infinite' : 'none',
    }}
  />
)
