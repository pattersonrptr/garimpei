import { describe, expect, it } from "vitest";

import {
  passwordChangeMessage,
  passwordChangeProblem,
  signInMessage,
  signUpMessage,
  signUpProblem,
} from "@/lib/authMessages";
import { secondsLeft, tokenClaims } from "@/lib/jwt";
import { safeNextPath, withNext } from "@/lib/nextPath";

function token(claims: object): string {
  const part = (value: object) => Buffer.from(JSON.stringify(value)).toString("base64url");
  return `${part({ alg: "HS256" })}.${part(claims)}.signature`;
}

describe("safeNextPath", () => {
  it("accepts paths inside the site", () => {
    expect(safeNextPath("/alertas/novo?isbn=9788535914849")).toBe(
      "/alertas/novo?isbn=9788535914849",
    );
  });

  it.each([null, "", "https://evil.example", "//evil.example", "/\\evil", "javascript:x", "/a\nb"])(
    "refuses %j",
    (raw) => {
      expect(safeNextPath(raw)).toBeNull();
    },
  );

  it("builds the sign-in link", () => {
    expect(withNext("/entrar", "/alertas")).toBe("/entrar?next=%2Falertas");
    expect(withNext("/entrar", "//evil")).toBe("/entrar");
  });
});

describe("jwt", () => {
  it("reads the claims", () => {
    expect(tokenClaims(token({ sub: "ana", user_id: 3 }))).toMatchObject({ sub: "ana", user_id: 3 });
  });

  it("is null for something that is not a token", () => {
    expect(tokenClaims("abc")).toBeNull();
    expect(tokenClaims("a.@@@.c")).toBeNull();
    expect(tokenClaims(null)).toBeNull();
  });

  it("counts the seconds left", () => {
    const now = Date.UTC(2026, 10, 11, 12, 0, 0);
    expect(secondsLeft(token({ exp: now / 1000 + 600 }), now)).toBe(600);
    expect(secondsLeft(token({ exp: now / 1000 - 5 }), now)).toBe(-5);
    expect(secondsLeft(token({ sub: "x" }), now)).toBeNull();
  });
});

describe("messages", () => {
  it("never says which of the two was wrong on sign-in", () => {
    expect(signInMessage({ status: 400, code: "INVALID_CREDENTIALS" })).toBe(
      "E-mail, usuário ou senha incorretos.",
    );
    expect(signInMessage({ status: 500 })).toMatch(/Tente de novo/);
  });

  it("explains sign-up conflicts", () => {
    expect(signUpMessage({ status: 409, code: "EMAIL_TAKEN" })).toMatch(/Entre com ele/);
    expect(signUpMessage({ status: 409, code: "USERNAME_TAKEN" })).toMatch(/em uso/);
    expect(signUpMessage({ status: 422, pointer: "/data/attributes/email" })).toBe(
      "Confira o e-mail.",
    );
  });

  it("checks the form before calling the backend", () => {
    const ok = { username: "ana", email: "ana@x.com", password: "12345678" };
    expect(signUpProblem(ok)).toBeNull();
    expect(signUpProblem({ ...ok, password: "1234567" })).toMatch(/8 caracteres/);
    expect(signUpProblem({ ...ok, username: "ana maria" })).toMatch(/espaços/);
    expect(signUpProblem({ ...ok, email: "ana" })).toBe("Confira o e-mail.");
    expect(signUpProblem({ ...ok, email: "" })).toBe("Preencha todos os campos.");
  });
});

describe("password change", () => {
  const ok = { current: "old-password", next: "new-password", confirm: "new-password" };

  it("accepts a good form", () => {
    expect(passwordChangeProblem(ok)).toBeNull();
  });

  it("checks the form before calling the backend", () => {
    expect(passwordChangeProblem({ ...ok, current: "" })).toBe("Preencha os três campos.");
    expect(passwordChangeProblem({ ...ok, next: "short", confirm: "short" })).toContain("8");
    expect(passwordChangeProblem({ ...ok, confirm: "other-password" })).toBe(
      "A confirmação não bate com a nova senha.",
    );
    expect(passwordChangeProblem({ current: "same-pass", next: "same-pass", confirm: "same-pass" })).toBe(
      "A nova senha precisa ser diferente da atual.",
    );
  });

  it("explains the backend's answer", () => {
    expect(passwordChangeMessage({ status: 400, code: "WRONG_PASSWORD" })).toBe(
      "A senha atual não está certa.",
    );
    expect(passwordChangeMessage({ status: 422 })).toContain("8");
    expect(passwordChangeMessage({ status: 500 })).toContain("Tente de novo");
  });
});
