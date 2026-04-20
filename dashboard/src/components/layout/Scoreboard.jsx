import { Group, Text, Badge } from '@mantine/core'
import { PARTY_COLORS } from '../../theme'

export const Scoreboard = ({ predictions }) => {
  if (!predictions?.length) return null

  const counts = {}
  predictions.forEach((p) => {
    if (p.leading_party) {
      counts[p.leading_party] = (counts[p.leading_party] || 0) + 1
    }
  })

  const total = predictions.length
  const predicted = Object.values(counts).reduce((a, b) => a + b, 0)
  const sorted = Object.entries(counts).sort((a, b) => b[1] - a[1])

  return (
    <Group gap="lg" px="md" py="xs" style={{ borderBottom: '1px solid #373a40', background: '#0a0a0f' }}>
      {sorted.map(([party, count]) => (
        <Group key={party} gap="xs">
          <Badge
            size="lg"
            style={PARTY_COLORS[party] ? { backgroundColor: PARTY_COLORS[party], color: '#fff' } : {}}
          >
            {party}
          </Badge>
          <Text fw={700} c="white">{count}</Text>
        </Group>
      ))}
      <Text c="dimmed" size="xs" ml="auto">
        {predicted}/{total} seats predicted
      </Text>
    </Group>
  )
}
