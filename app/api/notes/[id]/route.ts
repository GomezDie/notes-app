import { NextResponse } from "next/server";
import { removeNote } from "@/app/lib/notes-store";

export async function DELETE(
  _request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const removed = removeNote(id);

  if (!removed) {
    return NextResponse.json({ error: "Note not found" }, { status: 404 });
  }

  return new NextResponse(null, { status: 204 });
}
