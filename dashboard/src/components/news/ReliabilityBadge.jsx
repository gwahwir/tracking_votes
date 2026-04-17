import { Badge, Group, Text } from '@mantine/core'

/**
 * ReliabilityBadge — Color-coded reliability score
 */
export const ReliabilityBadge = ({ score }) => {
  const getColor = () => {
    if (score >= 70) return 'lime'
    if (score >= 40) return 'yellow'
    return 'red'
  }

  const getLabel = () => {
    if (score >= 70) return 'High'
    if (score >= 40) return 'Medium'
    return 'Low'
  }

  return (
    <Group gap="xs">
      <Badge size="sm" color={getColor()} variant="light">
        {getLabel()}
      </Badge>
      <Text size="xs" c="dimmed">
        {Math.round(score)}%
      </Text>
    </Group>
  )
}
