import { useEffect, useState } from 'react';
import { ActivityIndicator, FlatList, StyleSheet, View } from 'react-native';

import { SetupPrompt } from '@/components/setup-prompt';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { MaxContentWidth, Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';
import { fetchMe, fetchNotifications, type Notification } from '@/lib/api';
import { useConfig } from '@/lib/config';

function NotificationRow({ item }: { item: Notification }) {
  return (
    <ThemedView type="backgroundElement" style={[styles.row, item.read && styles.read]}>
      <View style={styles.rowHeader}>
        <ThemedText type="smallBold" style={styles.badge}>
          {item.category}
        </ThemedText>
        {item.read ? (
          <ThemedText type="small" themeColor="textSecondary">
            read
          </ThemedText>
        ) : null}
      </View>
      <ThemedText type="smallBold">{item.title ?? '(no title)'}</ThemedText>
      <ThemedText type="small" themeColor="textSecondary">
        {item.site_title ?? '—'}
      </ThemedText>
      <ThemedText type="small" themeColor="textSecondary">
        {item.formatted_event_date ?? ''}
      </ThemedText>
      {item.body_text ? (
        <ThemedText type="small" themeColor="textSecondary" style={styles.body}>
          {item.body_text}
        </ThemedText>
      ) : null}
    </ThemedView>
  );
}

export default function NotificationsScreen() {
  const { config, isConfigured } = useConfig();
  const theme = useTheme();
  const [items, setItems] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isConfigured) return;
    let cancelled = false;
    fetchMe(config)
      .then((me) => fetchNotifications(config, me.id))
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
            Notifications{items.length ? ` (${items.length})` : ''}
          </ThemedText>
        }
        ListEmptyComponent={
          loading ? (
            <ActivityIndicator style={styles.loading} />
          ) : (
            <ThemedText themeColor="textSecondary">No notifications yet.</ThemedText>
          )
        }
        renderItem={({ item }) => <NotificationRow item={item} />}
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
  rowHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  badge: {
    textTransform: 'uppercase',
  },
  body: {
    marginTop: Spacing.one,
  },
  read: {
    opacity: 0.55,
  },
});
