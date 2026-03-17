import { Hono } from "hono";
import api from "./routes/api";
import { ingest } from "./ingestion/ingest";

type Env = { DB: D1Database };

const app = new Hono<{ Bindings: Env }>();

app.route("/api", api);

export default {
  fetch: app.fetch,

  async scheduled(
    controller: ScheduledController,
    env: Env,
    ctx: ExecutionContext
  ) {
    console.log(`Cron triggered at ${new Date(controller.scheduledTime).toISOString()}`);
    ctx.waitUntil(ingest(env.DB));
  },
};
