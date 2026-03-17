import {
  RIDING_POSTAL_CODES,
  DATA_URL,
  FIELDS,
  OPTIONAL_FIELDS,
  type SourceRecord,
} from "../lib/constants";

function parseRow(row: string[]): SourceRecord {
  const record: Record<string, string | null> = {};
  for (let i = 0; i < FIELDS.length; i++) {
    record[FIELDS[i]] = row[i] ?? null;
  }
  return record as SourceRecord;
}

function checkRecord(record: SourceRecord): boolean {
  const city = record.recipient_city;
  if (city && !/^vancouver$/i.test(city.trim())) return false;

  const endDate = record.agreement_end_date;
  if (endDate) {
    const year = parseInt(endDate.split("-")[0], 10);
    if (year < 2021) return false;
  }
  return true;
}

async function fetchPostalCode(fsa: string): Promise<SourceRecord[]> {
  const params = new URLSearchParams({
    q: JSON.stringify({ recipient_postal_code: `${fsa}:*` }),
    plain: "False",
    language: "simple",
    sort: "_id asc",
    filters: "{}",
    format: "json",
    fields: ["_id", ...FIELDS].join(","),
    bom: "True",
  });

  const response = await fetch(`${DATA_URL}?${params}`);
  if (!response.ok) {
    console.error(`Failed to fetch FSA ${fsa}: ${response.status}`);
    return [];
  }

  const data = (await response.json()) as { records: string[][] };
  const records: SourceRecord[] = [];

  for (const row of data.records) {
    const record = parseRow(row);
    if (checkRecord(record)) {
      records.push(record);
    }
  }

  return records;
}

function buildAdditionalInfo(record: SourceRecord): string {
  const lines: string[] = [];
  for (const field of OPTIONAL_FIELDS) {
    const value = record[field];
    if (value) {
      lines.push(`${field}: ${value}`);
    }
  }
  return lines.join("\n");
}

export async function ingest(db: D1Database): Promise<number> {
  console.log("Starting data ingestion...");
  let totalInserted = 0;

  for (const fsa of RIDING_POSTAL_CODES) {
    console.log(`Fetching data for postal code ${fsa}...`);
    const records = await fetchPostalCode(fsa);
    console.log(`Got ${records.length} records for ${fsa}`);

    // Batch insert in chunks of 50 (D1 has limits on batch size)
    const batchSize = 50;
    for (let i = 0; i < records.length; i += batchSize) {
      const batch = records.slice(i, i + batchSize);
      const statements = batch.map((record) => {
        const startDate = record.agreement_start_date || "";
        const endDate = record.agreement_end_date || startDate;
        const department = `${record.owner_org_title} - ${(record.owner_org || "").toUpperCase()}`;
        const additionalInfo = buildAdditionalInfo(record);

        return db
          .prepare(
            `INSERT OR REPLACE INTO records (ref_n, recipient_name, postal_code, program_name, amount, start_date, end_date, department, additional_info, last_updated)
             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))`
          )
          .bind(
            record.ref_number,
            record.recipient_legal_name,
            record.recipient_postal_code,
            record.prog_name_en,
            parseFloat(record.agreement_value || "0"),
            startDate,
            endDate,
            department,
            additionalInfo
          );
      });

      await db.batch(statements);
      totalInserted += batch.length;
    }
  }

  console.log(`Ingestion complete. ${totalInserted} records processed.`);
  return totalInserted;
}
