import { useState } from 'react';
import { Pressable, StyleSheet, TextInput } from 'react-native';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { MaxContentWidth, Spacing } from '@/constants/theme';
import { useTheme } from '@/hooks/use-theme';
import { DEFAULT_BASE_URL, useConfig } from '@/lib/config';

export default function SettingsScreen() {
  const { config, saveConfig } = useConfig();
  const theme = useTheme();
  const [baseUrl, setBaseUrl] = useState(config.baseUrl);
  const [apiKey, setApiKey] = useState(config.apiKey);
  const [saved, setSaved] = useState(false);

  const onSave = () => {
    saveConfig({ baseUrl: baseUrl.trim() || DEFAULT_BASE_URL, apiKey: apiKey.trim() });
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <ThemedView style={styles.container}>
      <ThemedText type="subtitle">Settings</ThemedText>
      <ThemedText themeColor="textSecondary">
        Point the app at your running backend. Your API key is stored only in this browser.
      </ThemedText>

      <ThemedText type="smallBold">Backend URL</ThemedText>
      <TextInput
        value={baseUrl}
        onChangeText={setBaseUrl}
        placeholder={DEFAULT_BASE_URL}
        autoCapitalize="none"
        autoCorrect={false}
        style={[styles.input, { color: theme.text, borderColor: theme.backgroundSelected }]}
        placeholderTextColor={theme.textSecondary}
      />

      <ThemedText type="smallBold">API key</ThemedText>
      <TextInput
        value={apiKey}
        onChangeText={setApiKey}
        placeholder="Paste your X-API-Key"
        autoCapitalize="none"
        autoCorrect={false}
        secureTextEntry
        style={[styles.input, { color: theme.text, borderColor: theme.backgroundSelected }]}
        placeholderTextColor={theme.textSecondary}
      />

      <Pressable onPress={onSave} style={({ pressed }) => pressed && styles.pressed}>
        <ThemedView type="backgroundSelected" style={styles.button}>
          <ThemedText type="smallBold">Save</ThemedText>
        </ThemedView>
      </Pressable>

      {saved ? (
        <ThemedText type="small" themeColor="textSecondary">
          Saved ✓
        </ThemedText>
      ) : null}
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignSelf: 'center',
    width: '100%',
    maxWidth: MaxContentWidth,
    padding: Spacing.three,
    gap: Spacing.two,
  },
  input: {
    borderWidth: 1,
    borderRadius: Spacing.two,
    paddingHorizontal: Spacing.three,
    paddingVertical: Spacing.two,
    fontSize: 16,
  },
  button: {
    alignSelf: 'flex-start',
    paddingHorizontal: Spacing.four,
    paddingVertical: Spacing.two,
    borderRadius: Spacing.two,
  },
  pressed: {
    opacity: 0.7,
  },
});
