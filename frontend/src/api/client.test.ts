import { describe, expect, it, vi } from "vitest";

import { mockApi } from "../test/utils";
import { ApiError, apiRequest, buildUrl, configureApiClient, messageFromDetail } from "./client";

describe("buildUrl", () => {
  it("skips empty params and encodes the rest", () => {
    expect(buildUrl("/patients", { q: "ana maría", limit: 10, offset: undefined, x: "" })).toBe(
      "/patients?q=ana+mar%C3%ADa&limit=10",
    );
    expect(buildUrl("/stats")).toBe("/stats");
  });
});

describe("messageFromDetail", () => {
  it("reads string and FastAPI validation-error details", () => {
    expect(messageFromDetail("Bed not found", "x")).toBe("Bed not found");
    expect(messageFromDetail([{ msg: "too short" }, { msg: "required" }], "x")).toBe("too short; required");
    expect(messageFromDetail(undefined, "fallback")).toBe("fallback");
  });
});

describe("apiRequest", () => {
  it("sends the bearer token and JSON body", async () => {
    const fetchMock = mockApi({ "POST /triage": { id: 1 } });
    configureApiClient({ getToken: () => "abc", onUnauthorized: () => {} });
    await apiRequest("/triage", { method: "POST", body: { age: 3 } });
    const init = fetchMock.mock.calls[0]![1]!;
    expect(new Headers(init.headers).get("Authorization")).toBe("Bearer abc");
    expect(init.body).toBe(JSON.stringify({ age: 3 }));
  });

  it("throws ApiError with the server's detail message", async () => {
    mockApi({ "POST /beds/3/assign": () => ({ status: 409, json: { detail: "Bed is Occupied, not Available" } }) });
    configureApiClient({ getToken: () => "abc", onUnauthorized: () => {} });
    const error = await apiRequest("/beds/3/assign", { method: "POST" }).catch((e) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ status: 409, message: "Bed is Occupied, not Available" });
  });

  it("calls onUnauthorized when a signed-in request gets 401", async () => {
    mockApi({ "GET /auth/me": () => ({ status: 401, json: { detail: "Not authenticated" } }) });
    const onUnauthorized = vi.fn();
    configureApiClient({ getToken: () => "expired", onUnauthorized });
    await expect(apiRequest("/auth/me")).rejects.toThrow("Not authenticated");
    expect(onUnauthorized).toHaveBeenCalledOnce();
  });

  it("reports network failures with status 0", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    await expect(apiRequest("/stats")).rejects.toMatchObject({ status: 0 });
  });
});
