import "server-only";
import { asPublic } from "./db";
import { PAGE_SIZE, type BillFilters } from "./search-params";

export type BillListItem = {
  id: string;
  session_id: string;
  bill_type: string;
  bill_number: number;
  identifier: string;
  chamber: string;
  caption: string;
  status: string;
  status_date: string | null;
  last_action_text: string | null;
  last_action_date: string | null;
  last_synced_at: Date;
};

export type Session = { id: string; name: string; end_date: string | null; bill_count: number };

export type Freshness = {
  session_id: string;
  last_successful_at: Date | null;
  last_run_status: string | null;
  last_run_finished_at: Date | null;
};

export async function getSessions(): Promise<Session[]> {
  return asPublic(
    (tx) => tx<Session[]>`
      select s.id, s.name, s.end_date::text as end_date, count(b.id)::int as bill_count
      from legislative_sessions s left join bills b on b.session_id = s.id
      group by s.id order by s.legislature_number desc, s.id desc`,
  );
}

export async function getFreshness(): Promise<Freshness[]> {
  return asPublic(
    (tx) => tx<Freshness[]>`
      select s.id as session_id, st.last_successful_at,
             r.status as last_run_status, r.finished_at as last_run_finished_at
      from legislative_sessions s
      left join sync_state st on st.session_id = s.id and st.source_id = 'tlc_ftp'
      left join lateral (
        select status, finished_at from sync_runs
        where session_id = s.id order by started_at desc limit 1) r on true
      order by s.legislature_number desc`,
  );
}

export async function getTopics(session: string | null, limit = 40): Promise<string[]> {
  const rows = await asPublic(
    (tx) => tx<{ topic: string }[]>`
      select topic from (
        select unnest(subjects) as topic from bills
        where ${session ? tx`session_id = ${session}` : tx`true`}) t
      group by topic order by count(*) desc, topic limit ${limit}`,
  );
  return rows.map((r) => r.topic).sort((a, b) => a.localeCompare(b));
}

export async function searchBills(filters: BillFilters): Promise<{ bills: BillListItem[]; total: number }> {
  return asPublic(async (tx) => {
    const conditions = [];
    if (filters.billNumber) {
      conditions.push(tx`b.bill_type = ${filters.billNumber.billType} and b.bill_number = ${filters.billNumber.number}`);
    } else if (filters.q) {
      conditions.push(tx`b.search @@ websearch_to_tsquery('english', ${filters.q})`);
    }
    if (filters.session) conditions.push(tx`b.session_id = ${filters.session}`);
    if (filters.chamber) conditions.push(tx`b.chamber = ${filters.chamber}`);
    if (filters.status) conditions.push(tx`b.status = ${filters.status}`);
    if (filters.topic) conditions.push(tx`${filters.topic} = any(b.subjects)`);

    const where = conditions.reduce((acc, c) => tx`${acc} and ${c}`, tx`true`);
    const keywordRank = !filters.billNumber && filters.q;
    const order =
      filters.sort === "number"
        ? tx`b.session_id desc, b.bill_type, b.bill_number`
        : keywordRank
          ? tx`ts_rank(b.search, websearch_to_tsquery('english', ${filters.q})) desc, b.last_action_date desc nulls last`
          : tx`b.last_action_date desc nulls last, b.session_id desc, b.bill_type, b.bill_number`;

    const offset = (filters.page - 1) * PAGE_SIZE;
    const bills = await tx<BillListItem[]>`
      select b.id, b.session_id, b.bill_type, b.bill_number, b.identifier, b.chamber, b.caption, b.status,
             b.status_date::text, b.last_action_text, b.last_action_date::text, b.last_synced_at
      from bills b where ${where}
      order by ${order}
      limit ${PAGE_SIZE} offset ${offset}`;
    const [{ total }] = await tx<{ total: number }[]>`select count(*)::int as total from bills b where ${where}`;
    return { bills, total };
  });
}

export type BillDetail = BillListItem & {
  caption_version: string | null;
  subjects: string[];
  companions: string | null;
  source_url: string;
  official_url: string;
  source_updated_at: Date | null;
  session_name: string;
  session_end_date: string | null;
  source_name: string;
  source_attribution: string | null;
  source_license_notes: string | null;
};

export type Sponsor = { display_name: string; role: string; chamber: string };
export type Action = {
  sequence: number;
  action_code: string | null;
  actor: string;
  action_date: string | null;
  description: string;
  comment: string | null;
};
export type CommitteeRow = {
  chamber: string;
  name: string;
  status: string | null;
  yeas: number | null;
  nays: number | null;
  present_not_voting: number | null;
  absent: number | null;
};
export type FloorVote = { chamber: string; vote_date: string | null; motion: string | null; source_reference: string };
export type Version = {
  id: string;
  version_code: string;
  description: string;
  ordinal: number;
  html_url: string | null;
  pdf_url: string | null;
  document_id: string | null;
  retrieved_at: Date | null;
  content_hash: string | null;
  snapshot_count: number;
};
export type FiscalNote = { version_code: string; description: string; html_url: string | null; pdf_url: string | null; retrieved_at: Date | null };
export type Summary = {
  id: string;
  version_code: string;
  model_id: string;
  provider: string;
  generated_at: Date;
  reviewed_at: Date | null;
  content: unknown;
};

export type BillPage = {
  bill: BillDetail;
  sponsors: Sponsor[];
  actions: Action[];
  committees: CommitteeRow[];
  floorVotes: FloorVote[];
  versions: Version[];
  fiscalNotes: FiscalNote[];
  summaries: Summary[];
};

export async function getBill(session: string, billType: string, number: number): Promise<BillPage | null> {
  return asPublic(async (tx) => {
    const [bill] = await tx<BillDetail[]>`
      select b.id, b.session_id, b.bill_type, b.bill_number, b.identifier, b.chamber, b.caption, b.caption_version,
             b.status, b.status_date::text, b.last_action_text, b.last_action_date::text, b.last_synced_at,
             b.subjects, b.companions, b.source_url, b.official_url, b.source_updated_at,
             s.name as session_name, s.end_date::text as session_end_date,
             d.name as source_name, d.attribution as source_attribution, d.license_notes as source_license_notes
      from bills b
      join legislative_sessions s on s.id = b.session_id
      join data_sources d on d.id = b.source_id
      where b.session_id = ${session} and b.bill_type = ${billType} and b.bill_number = ${number}`;
    if (!bill) return null;

    const [sponsors, actions, committees, floorVotes, versions, fiscalNotes, summaries] = await Promise.all([
      tx<Sponsor[]>`
        select l.display_name, s.role, l.chamber from bill_sponsors s join legislators l on l.id = s.legislator_id
        where s.bill_id = ${bill.id} order by array_position(array['author','sponsor','coauthor','cosponsor'], s.role), s.position`,
      tx<Action[]>`
        select sequence, action_code, actor, action_date::text, description, comment
        from bill_actions where bill_id = ${bill.id} order by sequence`,
      tx<CommitteeRow[]>`
        select c.chamber, c.name, r.status, v.yeas, v.nays, v.present_not_voting, v.absent
        from bill_committee_referrals r join committees c on c.id = r.committee_id
        left join votes v on v.bill_id = r.bill_id and v.committee_id = c.id and v.vote_type = 'committee'
        where r.bill_id = ${bill.id} order by c.chamber = ${bill.chamber} desc`,
      tx<FloorVote[]>`
        select chamber, vote_date::text, motion, source_reference from votes
        where bill_id = ${bill.id} and vote_type = 'floor' order by vote_date nulls last`,
      tx<Version[]>`
        select v.id, v.version_code, v.description, v.ordinal, v.html_url, v.pdf_url,
               d.id as document_id, d.retrieved_at, d.content_hash,
               (select count(*)::int from source_documents x
                 where x.bill_id = v.bill_id and x.doc_type = 'bill_text' and x.version_code = v.version_code) as snapshot_count
        from bill_versions v
        left join source_documents d on d.bill_id = v.bill_id and d.doc_type = 'bill_text'
             and d.version_code = v.version_code and d.is_current
        where v.bill_id = ${bill.id} order by v.ordinal`,
      tx<FiscalNote[]>`
        select f.version_code, f.description, f.html_url, f.pdf_url, d.retrieved_at
        from fiscal_notes f left join source_documents d on d.id = f.source_document_id
        where f.bill_id = ${bill.id} order by f.first_seen_at, f.version_code`,
      // RLS returns only approved summaries to the public.
      tx<Summary[]>`
        select s.id, v.version_code, s.model_id, s.provider, s.generated_at, s.reviewed_at, s.content
        from ai_summaries s join bill_versions v on v.id = s.bill_version_id
        where s.bill_id = ${bill.id} order by v.ordinal desc`,
    ]);
    return { bill, sponsors, actions, committees, floorVotes, versions, fiscalNotes, summaries };
  });
}

export async function getDocumentText(documentId: string): Promise<string | null> {
  const rows = await asPublic(
    (tx) => tx<{ plain_text: string }[]>`select plain_text from source_documents where id = ${documentId}`,
  );
  return rows[0]?.plain_text ?? null;
}

export async function getRecentlyUpdated(limit = 6): Promise<BillListItem[]> {
  return asPublic(
    (tx) => tx<BillListItem[]>`
      select id, session_id, bill_type, bill_number, identifier, chamber, caption, status, status_date::text,
             last_action_text, last_action_date::text, last_synced_at
      from bills order by last_action_date desc nulls last, bill_number limit ${limit}`,
  );
}

export async function getCounts(): Promise<{ bills: number; documents: number; actions: number }> {
  return asPublic(async (tx) => {
    const [row] = await tx<{ bills: number; documents: number; actions: number }[]>`
      select (select count(*)::int from bills) as bills,
             (select count(*)::int from source_documents) as documents,
             (select count(*)::int from bill_actions) as actions`;
    return row;
  });
}
