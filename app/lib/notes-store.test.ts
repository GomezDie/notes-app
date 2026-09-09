import { beforeEach, describe, expect, it } from "vitest";
import {
  __resetNotes,
  addNote,
  listNotes,
  removeNote,
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
});
