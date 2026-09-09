"use client";

import { useState } from "react";

type Note = {
  id: string;
  text: string;
  createdAt: number;
};

export default function NotesClient({
  initialNotes,
}: {
  initialNotes: Note[];
}) {
  const [notes, setNotes] = useState<Note[]>(initialNotes);
  const [text, setText] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const value = text.trim();
    if (!value) return;

    setSubmitting(true);
    setError(null);
    try {
      const res = await fetch("/api/notes", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: value }),
      });
      if (!res.ok) throw new Error(`Failed to add note (${res.status})`);
      const data = (await res.json()) as { note: Note };
      setNotes((prev) => [data.note, ...prev]);
      setText("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete(id: string) {
    const previous = notes;
    setNotes((prev) => prev.filter((n) => n.id !== id));
    setError(null);
    try {
      const res = await fetch(`/api/notes/${id}`, { method: "DELETE" });
      if (!res.ok && res.status !== 404) {
        throw new Error(`Failed to delete note (${res.status})`);
      }
    } catch (err) {
      setNotes(previous);
      setError(err instanceof Error ? err.message : "Something went wrong");
    }
  }

  return (
    <>
      <form onSubmit={handleSubmit} className="mt-6 flex gap-2">
        <label htmlFor="note" className="sr-only">
          New note
        </label>
        <input
          id="note"
          type="text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Write a note&hellip;"
          className="flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm outline-none focus:border-gray-900 focus:ring-1 focus:ring-gray-900"
        />
        <button
          type="submit"
          disabled={submitting || !text.trim()}
          className="rounded-md bg-gray-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-gray-700 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {submitting ? "Adding…" : "Add"}
        </button>
      </form>

      {error && (
        <div
          role="alert"
          className="mt-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700"
        >
          {error}
        </div>
      )}

      <div className="mt-6">
        {notes.length === 0 ? (
          <p className="text-sm text-gray-500">No notes yet.</p>
        ) : (
          <ul className="divide-y divide-gray-100 rounded-md border border-gray-200">
            {notes.map((note) => (
              <li
                key={note.id}
                className="flex items-center justify-between gap-3 px-3 py-2.5 text-sm"
              >
                <span className="min-w-0 break-words">{note.text}</span>
                <button
                  type="button"
                  onClick={() => void handleDelete(note.id)}
                  className="shrink-0 rounded px-2 py-1 text-xs font-medium text-gray-500 transition hover:bg-red-50 hover:text-red-700"
                  aria-label={`Delete note: ${note.text}`}
                >
                  Delete
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </>
  );
}
