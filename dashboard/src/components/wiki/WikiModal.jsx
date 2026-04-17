import { Modal, Stack, Text, Input, List, Badge, Group, Loader } from '@mantine/core'
import { useWikiPages } from '../../hooks/useApi'
import { useState, useEffect } from 'react'

/**
 * WikiModal — Browse wiki knowledge base
 */
export const WikiModal = ({ onClose }) => {
  const { pages, loading } = useWikiPages()
  const [search, setSearch] = useState('')
  const [filtered, setFiltered] = useState([])

  useEffect(() => {
    if (!pages) return
    const results = pages.filter((page) =>
      page.title.toLowerCase().includes(search.toLowerCase()) ||
      page.path.toLowerCase().includes(search.toLowerCase())
    )
    setFiltered(results)
  }, [pages, search])

  return (
    <Modal title="Wiki Knowledge Base" opened={true} onClose={onClose} size="lg">
      <Stack gap="md">
        <Input
          placeholder="Search pages..."
          value={search}
          onChange={(e) => setSearch(e.currentTarget.value)}
          leftSection="🔍"
        />

        {loading && <Loader size="sm" />}

        {filtered.length === 0 && !loading && (
          <Text size="sm" c="dimmed">
            No pages found
          </Text>
        )}

        <List spacing="sm">
          {filtered.map((page) => (
            <List.Item key={page.path}>
              <Group justify="space-between" grow>
                <div>
                  <Text size="sm" fw={600}>
                    {page.title}
                  </Text>
                  <Text size="xs" c="dimmed">
                    {page.path}
                  </Text>
                </div>
                <Badge size="sm" variant="light">
                  {new Date(page.updated_at).toLocaleDateString()}
                </Badge>
              </Group>
            </List.Item>
          ))}
        </List>
      </Stack>
    </Modal>
  )
}
