import { listNotes } from "@/app/lib/notes-store";
import NotesClient from "./notes-client";

export const dynamic = "force-dynamic";

export default function NotesPage() {
  const initialNotes = listNotes();

  return (
    <main className="mx-auto max-w-xl px-4 py-12">
      <h1 className="text-2xl font-semibold tracking-tight">Notes</h1>
      <p className="mt-1 text-sm text-gray-500">
        In-memory demo &mdash; notes reset when the server restarts.
      </p>
      <NotesClient initialNotes={initialNotes} />
    </main>
  );
}
