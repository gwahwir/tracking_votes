import { Stack, Text, Group, Progress } from '@mantine/core'

const ETHNIC_COLORS = {
  malay: '#3366cc',
  chinese: '#ff3333',
  indian: '#ffcc00',
  others: '#999999',
}

export const DemographicsChart = ({ demographics, loading }) => {
  if (loading) return <Text c="dimmed" size="sm">Loading demographics...</Text>
  if (!demographics) return <Text c="dimmed" size="sm">No demographic data available.</Text>

  const segments = [
    { label: 'Malay', value: demographics.malay_pct ?? 0, color: ETHNIC_COLORS.malay },
    { label: 'Chinese', value: demographics.chinese_pct ?? 0, color: ETHNIC_COLORS.chinese },
    { label: 'Indian', value: demographics.indian_pct ?? 0, color: ETHNIC_COLORS.indian },
    { label: 'Others', value: demographics.others_pct ?? 0, color: ETHNIC_COLORS.others },
  ].filter((s) => s.value > 0)

  return (
    <Stack gap="md" mt="sm">
      <Text fw={600} size="sm" c="cyan">Ethnic Composition</Text>

      <Progress.Root size={28}>
        {segments.map((s) => (
          <Progress.Section key={s.label} value={s.value} color={s.color}>
            <Progress.Label>
              {s.value >= 10 ? `${s.label} ${s.value.toFixed(0)}%` : ''}
            </Progress.Label>
          </Progress.Section>
        ))}
      </Progress.Root>

      <Group gap="lg">
        {segments.map((s) => (
          <Group key={s.label} gap="xs">
            <div style={{ width: 12, height: 12, borderRadius: 2, backgroundColor: s.color }} />
            <Text size="xs">{s.label}: {s.value.toFixed(1)}%</Text>
          </Group>
        ))}
      </Group>

      <Group gap="xs">
        <Text size="sm" c="dimmed">Classification:</Text>
        <Text size="sm" fw={500}>{demographics.urban_rural || 'Unknown'}</Text>
      </Group>

      {demographics.region && (
        <Group gap="xs">
          <Text size="sm" c="dimmed">Region:</Text>
          <Text size="sm" fw={500}>{demographics.region}</Text>
        </Group>
      )}
    </Stack>
  )
}
