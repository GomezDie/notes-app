export type Note = {
  id: string;
  text: string;
  createdAt: number;
};

type Store = {
  notes: Note[];
};

// Persist across HMR reloads in dev by hanging the store off globalThis.
const globalForStore = globalThis as unknown as { __notesStore?: Store };

const store: Store = globalForStore.__notesStore ?? { notes: [] };
if (!globalForStore.__notesStore) {
  globalForStore.__notesStore = store;
}

export function listNotes(): Note[] {
  return [...store.notes].sort((a, b) => b.createdAt - a.createdAt);
}

export function addNote(text: string): Note {
  const trimmed = text.trim();
  if (!trimmed) {
    throw new Error("Note text is required");
  }
  const note: Note = {
    id: crypto.randomUUID(),
    text: trimmed,
    createdAt: Date.now(),
  };
  store.notes.push(note);
  return note;
}

export function removeNote(id: string): boolean {
  const before = store.notes.length;
  store.notes = store.notes.filter((n) => n.id !== id);
  return store.notes.length < before;
}

// Test-only helper.
export function __resetNotes(): void {
  store.notes = [];
}
