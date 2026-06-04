import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";

const storageItems = new Map<string, string>();

const localStorageMock: Storage = {
  get length() {
    return storageItems.size;
  },
  clear() {
    storageItems.clear();
  },
  getItem(key: string) {
    return storageItems.get(key) ?? null;
  },
  key(index: number) {
    const keys = Array.from(storageItems.keys());
    return keys[index] ?? null;
  },
  removeItem(key: string) {
    storageItems.delete(key);
  },
  setItem(key: string, value: string) {
    storageItems.set(key, value);
  },
};

vi.stubGlobal("localStorage", localStorageMock);

afterEach(() => {
  cleanup();
});
