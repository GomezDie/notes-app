import { beforeEach, describe, expect, it } from "vitest";
import {
  __resetNotes,
  addNote,
  listNotes,
  removeNote,
  updateNote,
} from "./notes-store";

beforeEach(() => {
  __resetNotes();
});

describe("notes-store", () => {
  it("starts empty", () => {
    expect(listNotes()).toEqual([]);
  });

  it("adds a note and returns it", () => {
    const note = addNote("buy milk");
    expect(note.text).toBe("buy milk");
    expect(note.id).toBeTruthy();
    expect(listNotes()).toHaveLength(1);
  });

  it("trims whitespace and rejects empty text", () => {
    expect(addNote("  hello  ").text).toBe("hello");
    expect(() => addNote("   ")).toThrow(/required/);
  });

  it("lists notes newest first", async () => {
    addNote("first");
    await new Promise((r) => setTimeout(r, 2));
    addNote("second");
    expect(listNotes().map((n) => n.text)).toEqual(["second", "first"]);
  });

  it("removes a note by id and reports whether it existed", () => {
    const note = addNote("temp");
    expect(removeNote(note.id)).toBe(true);
    expect(listNotes()).toHaveLength(0);
    expect(removeNote(note.id)).toBe(false);
  });

  it("updates a note's text and returns the updated note", () => {
    const note = addNote("draft");
    const updated = updateNote(note.id, "final");
    expect(updated?.id).toBe(note.id);
    expect(updated?.text).toBe("final");
    expect(listNotes()[0].text).toBe("final");
  });

  it("trims whitespace when updating", () => {
    const note = addNote("draft");
    expect(updateNote(note.id, "  spaced  ")?.text).toBe("spaced");
  });

  it("throws when updating with empty text", () => {
    const note = addNote("draft");
    expect(() => updateNote(note.id, "   ")).toThrow(/required/);
  });

  it("returns null when updating a missing id", () => {
    expect(updateNote("nope", "whatever")).toBeNull();
  });
});
