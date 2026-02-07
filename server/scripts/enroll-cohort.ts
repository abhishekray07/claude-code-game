// Enroll Stripe cohort customers into Claude Code Game D1 database
//
// Usage:
//   STRIPE_SECRET_KEY=sk_... npx tsx scripts/enroll-cohort.ts
//   STRIPE_SECRET_KEY=sk_... npx tsx scripts/enroll-cohort.ts --execute
//
// Without --execute: prints SQL and wrangler command (dry run)
// With --execute: runs wrangler d1 execute directly

import Stripe from "stripe";
import { execSync } from "child_process";

const COHORT = process.env.COHORT || "claude-code-cohort-3";
const DB_NAME = "claude-code-game";

async function main() {
  const key = process.env.STRIPE_SECRET_KEY;
  if (!key) {
    console.error("Error: STRIPE_SECRET_KEY env var is required");
    process.exit(1);
  }

  const execute = process.argv.includes("--execute");
  const stripe = new Stripe(key);

  console.log(`Fetching Stripe customers with metadata.courseType === "${COHORT}"...\n`);

  const customers: { email: string; name: string }[] = [];

  for await (const customer of stripe.customers.list({ limit: 100 })) {
    if (
      customer.metadata.courseType === COHORT &&
      customer.metadata.paymentMethodId
    ) {
      if (customer.email) {
        customers.push({
          email: customer.email.toLowerCase(),
          name: customer.name || customer.email.split("@")[0],
        });
      }
    }
  }

  if (customers.length === 0) {
    console.log("No customers found matching criteria.");
    return;
  }

  console.log(`Found ${customers.length} customers:\n`);
  for (const c of customers) {
    console.log(`  ${c.email} (${c.name})`);
  }

  // Build SQL — use INSERT OR IGNORE so re-runs are safe
  const values = customers
    .map((c) => {
      const email = c.email.replace(/'/g, "''");
      const name = c.name.replace(/'/g, "''");
      return `('${email}', '${name}')`;
    })
    .join(",\n  ");

  const sql = `INSERT OR IGNORE INTO enrolled (email, name) VALUES\n  ${values};`;

  console.log(`\n--- SQL ---\n${sql}\n`);

  if (execute) {
    console.log("Executing via wrangler d1...\n");
    try {
      const result = execSync(
        `npx wrangler d1 execute ${DB_NAME} --remote --command "${sql.replace(/"/g, '\\"')}"`,
        { cwd: new URL("../../worker", import.meta.url).pathname, stdio: "inherit" },
      );
      console.log("\nDone! Enrolled successfully.");
    } catch {
      console.error("\nwrangler d1 execute failed. Check output above.");
      process.exit(1);
    }
  } else {
    console.log("Dry run — pass --execute to run the wrangler command.");
    console.log(`\nManual command:\n  cd worker && npx wrangler d1 execute ${DB_NAME} --remote --command "${sql.replace(/"/g, '\\"')}"\n`);
  }
}

main();
