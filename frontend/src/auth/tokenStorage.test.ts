import { describe, expect, it } from "vitest";

import { fakeToken } from "../test/utils";
import { decodeExpiry, isExpired, tokenStorage } from "./tokenStorage";

describe("tokenStorage", () => {
  it("keeps a valid token and drops an expired one", () => {
    const valid = fakeToken();
    tokenStorage.set(valid);
    expect(tokenStorage.get()).toBe(valid);

    tokenStorage.set(fakeToken(Math.floor(Date.now() / 1000) - 10));
    expect(tokenStorage.get()).toBeNull();
    expect(localStorage.getItem("sachealth.token")).toBeNull();
  });

  it("reads the exp claim and tolerates malformed tokens", () => {
    expect(decodeExpiry(fakeToken(1_700_000_000))).toBe(1_700_000_000_000);
    expect(decodeExpiry("not-a-jwt")).toBeNull();
    expect(isExpired("not-a-jwt")).toBe(false);
  });
});
