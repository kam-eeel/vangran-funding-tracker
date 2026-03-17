export interface Filters {
  department?: string;
  program?: string;
  postal_code?: string;
  start_date_from?: string;
  start_date_to?: string;
  amount_min?: string;
  amount_max?: string;
  search?: string;
}

interface WhereClause {
  conditions: string[];
  params: unknown[];
}

function applyFilters(filters: Filters): WhereClause {
  const conditions: string[] = [];
  const params: unknown[] = [];

  if (filters.department) {
    conditions.push("department = ?");
    params.push(filters.department);
  }
  if (filters.program) {
    conditions.push("program_name = ?");
    params.push(filters.program);
  }
  if (filters.postal_code) {
    conditions.push("UPPER(postal_code) LIKE ?");
    params.push(filters.postal_code.toUpperCase() + "%");
  }
  if (filters.start_date_from) {
    conditions.push("start_date >= ?");
    params.push(filters.start_date_from);
  }
  if (filters.start_date_to) {
    conditions.push("start_date <= ?");
    params.push(filters.start_date_to);
  }
  if (filters.amount_min) {
    const val = parseFloat(filters.amount_min);
    if (!isNaN(val)) {
      conditions.push("amount >= ?");
      params.push(val);
    }
  }
  if (filters.amount_max) {
    const val = parseFloat(filters.amount_max);
    if (!isNaN(val)) {
      conditions.push("amount <= ?");
      params.push(val);
    }
  }
  if (filters.search) {
    const term = `%${filters.search}%`;
    conditions.push(
      "(recipient_name LIKE ? OR program_name LIKE ? OR ref_n LIKE ?)"
    );
    params.push(term, term, term);
  }

  return { conditions, params };
}

function whereSQL(clause: WhereClause): string {
  if (clause.conditions.length === 0) return "";
  return " WHERE " + clause.conditions.join(" AND ");
}

export async function getKpis(db: D1Database) {
  const today = new Date().toISOString().split("T")[0];
  const result = await db
    .prepare(
      `SELECT
        COALESCE(SUM(amount), 0) AS total_funding,
        COUNT(*) AS record_count,
        COALESCE(AVG(amount), 0) AS avg_amount,
        COUNT(DISTINCT program_name) AS program_count,
        COUNT(DISTINCT department) AS department_count,
        COALESCE(SUM(CASE WHEN end_date < ? THEN amount ELSE 0 END), 0) AS funding_delivered,
        COALESCE(SUM(CASE WHEN end_date >= ? THEN amount ELSE 0 END), 0) AS funding_committed
      FROM records`
    )
    .bind(today, today)
    .first();

  return {
    total_funding: Number(result!.total_funding),
    record_count: Number(result!.record_count),
    avg_amount: Number(result!.avg_amount),
    program_count: Number(result!.program_count),
    department_count: Number(result!.department_count),
    funding_delivered: Number(result!.funding_delivered),
    funding_committed: Number(result!.funding_committed),
  };
}

export async function getFundingByDepartment(
  db: D1Database,
  filters: Filters = {},
  limit: number = 10
) {
  const where = applyFilters(filters);
  const whereStr = whereSQL(where);
  const limitStr = limit > 0 ? ` LIMIT ${limit}` : "";

  const { results } = await db
    .prepare(
      `SELECT department AS name, SUM(amount) AS total, COUNT(*) AS count
       FROM records${whereStr}
       GROUP BY department
       ORDER BY SUM(amount) DESC${limitStr}`
    )
    .bind(...where.params)
    .all();

  return results.map((r: Record<string, unknown>) => ({
    name: r.name as string,
    short_name: shortDepartment(r.name as string),
    total: Number(r.total),
    count: Number(r.count),
  }));
}

export async function getFundingByProgram(
  db: D1Database,
  filters: Filters = {},
  limit: number = 10
) {
  const where = applyFilters(filters);
  const whereStr = whereSQL(where);
  const limitStr = limit > 0 ? ` LIMIT ${limit}` : "";

  const { results } = await db
    .prepare(
      `SELECT program_name AS name, SUM(amount) AS total, COUNT(*) AS count
       FROM records${whereStr}
       GROUP BY program_name
       ORDER BY SUM(amount) DESC${limitStr}`
    )
    .bind(...where.params)
    .all();

  const result = results.map((r: Record<string, unknown>) => ({
    name: (r.name as string) || "Unknown",
    total: Number(r.total),
    count: Number(r.count),
  }));

  // Compute "Other" when using a limit
  if (limit > 0) {
    const totalResult = await db
      .prepare(
        `SELECT COALESCE(SUM(amount), 0) AS total_all, COUNT(*) AS count_all FROM records${whereStr}`
      )
      .bind(...where.params)
      .first();

    const totalAll = Number(totalResult!.total_all);
    const countAll = Number(totalResult!.count_all);
    const topTotal = result.reduce((s, r) => s + r.total, 0);
    const topCount = result.reduce((s, r) => s + r.count, 0);
    const otherTotal = totalAll - topTotal;
    const otherCount = countAll - topCount;

    if (otherTotal > 0) {
      result.push({ name: "Other", total: otherTotal, count: otherCount });
    }
  }

  return result;
}

export async function getFundingByPostalCode(
  db: D1Database,
  filters: Filters = {}
) {
  const where = applyFilters(filters);
  const whereStr = whereSQL(where);

  const { results } = await db
    .prepare(
      `SELECT UPPER(SUBSTR(postal_code, 1, 3)) AS fsa, SUM(amount) AS total, COUNT(*) AS count
       FROM records${whereStr}
       GROUP BY fsa
       ORDER BY SUM(amount) DESC`
    )
    .bind(...where.params)
    .all();

  return results.map((r: Record<string, unknown>) => ({
    fsa: r.fsa as string,
    total: Number(r.total),
    count: Number(r.count),
  }));
}

export async function getFundingTimeline(
  db: D1Database,
  filters: Filters = {}
) {
  const where = applyFilters(filters);
  const whereStr = whereSQL(where);

  const { results } = await db
    .prepare(
      `SELECT SUBSTR(start_date, 1, 4) AS year, SUM(amount) AS total, COUNT(*) AS count
       FROM records${whereStr}
       GROUP BY year
       ORDER BY year`
    )
    .bind(...where.params)
    .all();

  return results.map((r: Record<string, unknown>) => ({
    year: r.year as string,
    total: Number(r.total),
    count: Number(r.count),
  }));
}

export async function getFilterOptions(db: D1Database) {
  const [departments, programs, postalCodes, dateRange, amountRange] =
    await Promise.all([
      db
        .prepare(
          "SELECT DISTINCT department FROM records ORDER BY department"
        )
        .all(),
      db
        .prepare(
          "SELECT DISTINCT program_name FROM records WHERE program_name IS NOT NULL ORDER BY program_name"
        )
        .all(),
      db
        .prepare(
          "SELECT DISTINCT UPPER(SUBSTR(postal_code, 1, 3)) AS fsa FROM records ORDER BY fsa"
        )
        .all(),
      db
        .prepare(
          "SELECT MIN(start_date) AS min_date, MAX(start_date) AS max_date FROM records"
        )
        .first(),
      db
        .prepare(
          "SELECT MIN(amount) AS min_amount, MAX(amount) AS max_amount FROM records"
        )
        .first(),
    ]);

  return {
    departments: departments.results.map(
      (r: Record<string, unknown>) => r.department as string
    ),
    programs: programs.results.map(
      (r: Record<string, unknown>) => r.program_name as string
    ),
    postal_codes: postalCodes.results.map(
      (r: Record<string, unknown>) => r.fsa as string
    ),
    min_date: (dateRange?.min_date as string) || "",
    max_date: (dateRange?.max_date as string) || "",
    min_amount: Number(dateRange?.min_amount) || 0,
    max_amount: Number(amountRange?.max_amount) || 0,
  };
}

export async function getLastUpdated(db: D1Database): Promise<string | null> {
  const result = await db
    .prepare("SELECT MAX(last_updated) AS lu FROM records")
    .first();
  return (result?.lu as string) || null;
}

export async function getRecordById(db: D1Database, id: number) {
  return db.prepare("SELECT * FROM records WHERE id = ?").bind(id).first();
}

const SORTABLE_COLUMNS = new Set([
  "ref_n",
  "recipient_name",
  "postal_code",
  "program_name",
  "amount",
  "start_date",
  "end_date",
  "department",
]);

export async function searchRecords(
  db: D1Database,
  filters: Filters = {},
  sort: string = "amount",
  direction: string = "desc",
  page: number = 1,
  perPage: number = 50
) {
  const where = applyFilters(filters);
  const whereStr = whereSQL(where);

  const sortCol = SORTABLE_COLUMNS.has(sort) ? sort : "amount";
  const dir = direction === "asc" ? "ASC" : "DESC";

  // Get total count
  const countResult = await db
    .prepare(`SELECT COUNT(*) AS total FROM records${whereStr}`)
    .bind(...where.params)
    .first();
  const total = Number(countResult!.total);

  const pages = Math.max(1, Math.ceil(total / perPage));
  page = Math.max(1, Math.min(page, pages));
  const offset = (page - 1) * perPage;

  const { results } = await db
    .prepare(
      `SELECT id, ref_n, recipient_name, postal_code, program_name, amount, start_date, end_date, department
       FROM records${whereStr}
       ORDER BY ${sortCol} ${dir}
       LIMIT ? OFFSET ?`
    )
    .bind(...where.params, perPage, offset)
    .all();

  return {
    records: results,
    total,
    page,
    pages,
    per_page: perPage,
  };
}

function shortDepartment(name: string): string {
  if (name.includes("|")) return name.split("|")[0].trim();
  if (name.includes(" - ")) {
    const parts = name.split(" - ");
    parts.pop();
    return parts.join(" - ").trim();
  }
  return name;
}
