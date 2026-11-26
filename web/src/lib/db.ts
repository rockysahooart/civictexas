import "server-only";
import postgres from "postgres";

// Server-side only. DATABASE_URL is never exposed to the browser.
//
// Every public query runs inside a transaction that switches to the `anon`
// role, so row-level security applies exactly as it would for any public
// client (e.g. unreviewed AI summaries stay hidden).

export class DataUnavailableError extends Error {}

type Sql = postgres.Sql;
type Tx = postgres.TransactionSql;

const globalForDb = globalThis as unknown as { civictexasSql?: Sql };

function client(): Sql {
  const url = process.env.DATABASE_URL;
  if (!url) throw new DataUnavailableError("DATABASE_URL is not configured");
  if (!globalForDb.civictexasSql) {
    globalForDb.civictexasSql = postgres(url, {
      max: 5,
      prepare: false, // compatible with Supabase's transaction pooler
      idle_timeout: 20,
      connect_timeout: 10,
    });
  }
  return globalForDb.civictexasSql;
}

export async function asPublic<T>(fn: (tx: Tx) => Promise<T>): Promise<T> {
  try {
    return (await client().begin(async (tx) => {
      await tx`set local role anon`;
      return fn(tx);
    })) as T;
  } catch (error) {
    if (error instanceof DataUnavailableError) throw error;
    const code = (error as { code?: string }).code;
    if (code === "ECONNREFUSED" || code === "ENOTFOUND" || code === "CONNECT_TIMEOUT") {
      throw new DataUnavailableError("The legislative database is unreachable");
    }
    throw error;
  }
}
