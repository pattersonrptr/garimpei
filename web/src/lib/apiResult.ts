import type { ApiError } from "@/lib/authMessages";

/** A write to the backend: done, or the first JSON:API error. */
export type Result = { ok: true } | { ok: false; error: ApiError };

export async function toResult(response: Response): Promise<Result> {
  if (response.ok) return { ok: true };
  try {
    const error = (await response.json())?.errors?.[0];
    return {
      ok: false,
      error: { status: response.status, code: error?.code, pointer: error?.source?.pointer },
    };
  } catch {
    return { ok: false, error: { status: response.status } };
  }
}
