import { describe, expect, it } from "vitest";

import { formatDateTime, parseApiDate } from "./format";

describe("parseApiDate", () => {
  it("reads offset-less API timestamps (SQLite) as UTC", () => {
    expect(parseApiDate("2026-11-20T04:00:00").toISOString()).toBe("2026-11-20T04:00:00.000Z");
    expect(parseApiDate("2026-11-20T04:00:00.123456").toISOString()).toBe("2026-11-20T04:00:00.123Z");
  });

  it("keeps explicit offsets (PostgreSQL) unchanged", () => {
    expect(parseApiDate("2026-11-20T04:00:00Z").toISOString()).toBe("2026-11-20T04:00:00.000Z");
    expect(parseApiDate("2026-11-19T20:00:00-08:00").toISOString()).toBe("2026-11-20T04:00:00.000Z");
    expect(formatDateTime("2026-11-20T04:00:00")).toBe(formatDateTime("2026-11-20T04:00:00+00:00"));
  });
});
