import { useEffect, useState } from 'react';
import { ActivityIndicator, FlatList, StyleSheet, View } from 'react-native';

import { SetupPrompt } from '@/components/setup-prompt';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { MaxContentWidth, Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';
import { fetchAssignments, fetchMe, type Assignment } from '@/lib/api';
import { useConfig } from '@/lib/config';

function formatDue(iso: string | null): string {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });
}

function AssignmentRow({ item }: { item: Assignment }) {
  return (
    <ThemedView type="backgroundElement" style={styles.row}>
      <ThemedText type="smallBold">{item.title}</ThemedText>
      <ThemedText type="small" themeColor="textSecondary">
        {item.course}
      </ThemedText>
      <ThemedText type="small" themeColor="textSecondary">
        Due: {formatDue(item.due_at)}
      </ThemedText>
      {item.status_label ? (
        <ThemedText type="small" themeColor="textSecondary">
          Status: {item.status_label}
        </ThemedText>
      ) : null}
    </ThemedView>
  );
}

export default function AssignmentsScreen() {
  const { config, isConfigured } = useConfig();
  const theme = useTheme();
  const [items, setItems] = useState<Assignment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isConfigured) return;
    let cancelled = false;
    fetchMe(config)
      .then((me) => fetchAssignments(config, me.id))
      .then((list) => {
        if (cancelled) return;
        setItems(list);
        setError(null);
        setLoading(false);
      })
      .catch((e: unknown) => {
        if (cancelled) return;
        setError(e instanceof Error ? e.message : String(e));
        setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [config, isConfigured]);

  if (!isConfigured) {
    return <SetupPrompt />;
  }

  return (
    <View style={[styles.screen, { backgroundColor: theme.background }]}>
      <FlatList
        data={items}
        keyExtractor={(it) => String(it.id)}
        contentContainerStyle={styles.list}
        ListHeaderComponent={
          <ThemedText type="subtitle" style={styles.header}>
            Assignments{items.length ? ` (${items.length})` : ''}
          </ThemedText>
        }
        ListEmptyComponent={
          loading ? (
            <ActivityIndicator style={styles.loading} />
          ) : (
            <ThemedText themeColor="textSecondary">No assignments found.</ThemedText>
          )
        }
        renderItem={({ item }) => <AssignmentRow item={item} />}
      />
      {error ? (
        <ThemedText type="small" themeColor="textSecondary" style={styles.error}>
          {error}
        </ThemedText>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1 },
  list: {
    width: '100%',
    maxWidth: MaxContentWidth,
    alignSelf: 'center',
    padding: Spacing.three,
    gap: Spacing.two,
  },
  header: {
    paddingVertical: Spacing.two,
  },
  loading: {
    marginTop: Spacing.four,
  },
  error: {
    paddingHorizontal: Spacing.three,
    paddingBottom: Spacing.three,
  },
  row: {
    padding: Spacing.three,
    borderRadius: Spacing.two,
    gap: Spacing.one,
  },
});
