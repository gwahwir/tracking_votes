import { Table, Text, Badge, Stack } from '@mantine/core'
import { PARTY_COLORS } from '../../theme'

export const HistoryTable = ({ results, loading }) => {
  if (loading) return <Text c="dimmed" size="sm">Loading history...</Text>
  if (!results?.length) return <Text c="dimmed" size="sm">No historical data available.</Text>

  const sorted = [...results]
    .sort((a, b) => b.election_year - a.election_year)
    .map((r) => ({
      ...r,
      candidates: typeof r.candidates === 'string' ? JSON.parse(r.candidates) : (r.candidates ?? []),
    }))

  return (
    <Stack gap="md" mt="sm">
      <Table striped highlightOnHover>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Year</Table.Th>
            <Table.Th>Winner</Table.Th>
            <Table.Th>Party</Table.Th>
            <Table.Th>Margin</Table.Th>
            <Table.Th>Turnout</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {sorted.map((r) => (
            <Table.Tr key={r.election_year}>
              <Table.Td>{r.election_year}</Table.Td>
              <Table.Td><Text size="sm">{r.winner_name}</Text></Table.Td>
              <Table.Td>
                <Badge size="sm" color={PARTY_COLORS[r.winner_coalition] ? undefined : 'gray'}
                  style={PARTY_COLORS[r.winner_coalition] ? { backgroundColor: PARTY_COLORS[r.winner_coalition] } : {}}>
                  {r.winner_party} ({r.winner_coalition})
                </Badge>
              </Table.Td>
              <Table.Td>
                <Text size="sm">
                  {r.margin_pct != null ? `${r.margin_pct.toFixed(1)}%` : '—'}
                  {r.margin != null && (
                    <Text span c="dimmed" size="xs"> ({r.margin.toLocaleString()} votes)</Text>
                  )}
                </Text>
              </Table.Td>
              <Table.Td>
                <Text size="sm">{r.turnout_pct != null ? `${r.turnout_pct.toFixed(1)}%` : '—'}</Text>
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>

      {sorted[0]?.candidates?.length > 0 && (
        <>
          <Text fw={600} size="sm" c="cyan">{sorted[0].election_year} Full Results</Text>
          <Table>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Candidate</Table.Th>
                <Table.Th>Party</Table.Th>
                <Table.Th>Votes</Table.Th>
                <Table.Th>%</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {[...sorted[0].candidates]
                .sort((a, b) => b.votes - a.votes)
                .map((c, i) => (
                  <Table.Tr key={i}>
                    <Table.Td>
                      <Text size="sm" fw={i === 0 ? 700 : 400}>{c.name}</Text>
                    </Table.Td>
                    <Table.Td>
                      <Badge size="xs">{c.party}</Badge>
                    </Table.Td>
                    <Table.Td>{c.votes?.toLocaleString() ?? '—'}</Table.Td>
                    <Table.Td>
                      {sorted[0].total_votes_cast && c.votes
                        ? `${((c.votes / sorted[0].total_votes_cast) * 100).toFixed(1)}%`
                        : '—'}
                    </Table.Td>
                  </Table.Tr>
                ))}
            </Table.Tbody>
          </Table>
        </>
      )}
    </Stack>
  )
}
