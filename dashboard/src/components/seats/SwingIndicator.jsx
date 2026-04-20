import { Group, Text } from '@mantine/core'

/**
 * Shows hold/flip status comparing current prediction to last election result.
 */
export const SwingIndicator = ({ prediction, lastResult }) => {
  if (!prediction || !lastResult) return null

  const currentParty = prediction.leading_party
  const previousParty = lastResult.winner_coalition
  const sameParty = currentParty === previousParty

  return (
    <Group gap="xs">
      <Text size="sm" c="dimmed">vs {lastResult.election_year}:</Text>
      {sameParty ? (
        <Text size="sm" c="lime" fw={600}>
          HOLD ({currentParty})
        </Text>
      ) : (
        <Text size="sm" c="red" fw={600}>
          FLIP {previousParty} → {currentParty}
        </Text>
      )}
      {prediction.confidence != null && (
        <Text size="xs" c="dimmed">({prediction.confidence}% confidence)</Text>
      )}
    </Group>
  )
}
