import { writable } from 'svelte/store';

export const isGameSettingsOpen = writable<boolean>(false);

export const isLiveStatsOpen = writable<boolean>(false);

export const isHistoryOpen = writable<boolean>(false);

export const isFairOpen = writable<boolean>(false);
