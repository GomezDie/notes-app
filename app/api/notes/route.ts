import { NextResponse } from "next/server";
import { addNote, listNotes } from "@/app/lib/notes-store";

export async function GET() {
  return NextResponse.json({ notes: listNotes() });
}

export async function POST(request: Request) {
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON body" }, { status: 400 });
  }

  const text =
    body && typeof body === "object" && "text" in body
      ? (body as { text: unknown }).text
      : undefined;

  if (typeof text !== "string" || !text.trim()) {
    return NextResponse.json(
      { error: "Field 'text' is required" },
      { status: 400 },
    );
  }

  const note = addNote(text);
  return NextResponse.json({ note }, { status: 201 });
}
