import { Hono } from "hono";
import type { Filters } from "../db/queries";
import {
  getKpis,
  getFundingByDepartment,
  getFundingByProgram,
  getFundingByPostalCode,
  getFundingTimeline,
  getFilterOptions,
  getLastUpdated,
  getRecordById,
  searchRecords,
} from "../db/queries";

type Env = { Bindings: { DB: D1Database } };

const api = new Hono<Env>();

function extractFilters(c: { req: { query: (key: string) => string | undefined } }): Filters {
  return {
    department: c.req.query("department"),
    program: c.req.query("program"),
    postal_code: c.req.query("postal_code"),
    start_date_from: c.req.query("start_date_from"),
    start_date_to: c.req.query("start_date_to"),
    amount_min: c.req.query("amount_min"),
    amount_max: c.req.query("amount_max"),
    search: c.req.query("search"),
  };
}

api.get("/kpis", async (c) => {
  const data = await getKpis(c.env.DB);
  return c.json(data);
});

api.get("/charts/department", async (c) => {
  const filters = extractFilters(c);
  const limit = parseInt(c.req.query("limit") || "10", 10);
  const data = await getFundingByDepartment(c.env.DB, filters, limit);
  return c.json({
    labels: data.map((d) => d.short_name),
    data: data.map((d) => d.total),
    counts: data.map((d) => d.count),
    full_names: data.map((d) => d.name),
  });
});

api.get("/charts/program", async (c) => {
  const filters = extractFilters(c);
  const limit = parseInt(c.req.query("limit") || "10", 10);
  const data = await getFundingByProgram(c.env.DB, filters, limit);
  return c.json({
    labels: data.map((d) => d.name),
    data: data.map((d) => d.total),
    counts: data.map((d) => d.count),
  });
});

api.get("/charts/postal", async (c) => {
  const filters = extractFilters(c);
  const data = await getFundingByPostalCode(c.env.DB, filters);
  return c.json({
    labels: data.map((d) => d.fsa),
    data: data.map((d) => d.total),
    counts: data.map((d) => d.count),
  });
});

api.get("/charts/timeline", async (c) => {
  const filters = extractFilters(c);
  const data = await getFundingTimeline(c.env.DB, filters);
  return c.json({
    labels: data.map((d) => d.year),
    amounts: data.map((d) => d.total),
    counts: data.map((d) => d.count),
  });
});

api.get("/records", async (c) => {
  const filters = extractFilters(c);
  const sort = c.req.query("sort") || "amount";
  const direction = c.req.query("direction") || "desc";
  const page = parseInt(c.req.query("page") || "1", 10);
  const perPage = parseInt(c.req.query("per_page") || "50", 10);
  const data = await searchRecords(
    c.env.DB,
    filters,
    sort,
    direction,
    page,
    perPage
  );
  return c.json(data);
});

api.get("/records/:id", async (c) => {
  const id = parseInt(c.req.param("id"), 10);
  const record = await getRecordById(c.env.DB, id);
  if (!record) return c.json({ error: "Not found" }, 404);
  return c.json(record);
});

api.get("/filters", async (c) => {
  const data = await getFilterOptions(c.env.DB);
  return c.json(data);
});

api.get("/last-updated", async (c) => {
  const lu = await getLastUpdated(c.env.DB);
  return c.json({ last_updated: lu });
});

export default api;
