import { auditEmail } from "@emailens/engine";

let input = "";
for await (const chunk of process.stdin) input += chunk;
const payload = JSON.parse(input || "{}");
const report = await auditEmail(payload.email || "");
process.stdout.write(JSON.stringify(report));
