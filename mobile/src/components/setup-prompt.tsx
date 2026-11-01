import { Pressable, StyleSheet } from 'react-native';
import { useRouter } from 'expo-router';

import { ThemedText } from './themed-text';
import { ThemedView } from './themed-view';
import { Spacing } from '@/constants/theme';

export function SetupPrompt() {
  const router = useRouter();

  return (
    <ThemedView style={styles.container}>
      <ThemedText type="subtitle">Welcome</ThemedText>
      <ThemedText themeColor="textSecondary" style={styles.body}>
        Connect to your backend to see your Sakai assignments and notifications.
      </ThemedText>
      <Pressable onPress={() => router.push('/settings')} style={({ pressed }) => pressed && styles.pressed}>
        <ThemedText type="linkPrimary">Configure connection →</ThemedText>
      </Pressable>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: Spacing.three,
    paddingHorizontal: Spacing.four,
  },
  body: {
    textAlign: 'center',
  },
  pressed: {
    opacity: 0.7,
  },
});
