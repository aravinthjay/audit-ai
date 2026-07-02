import { apiRequest } from "@/services/api";
import type { FlaggedRow, IntakeRuleStat, IntakeSummary } from "@/types/domain";

type ApiIntakeRuleStat = {
  rule: string;
  count: number;
  tone: IntakeRuleStat["tone"];
};

type ApiFlaggedRow = {
  txn_id: string;
  vendor: string;
  account: string;
  amount: string;
  rules: string[];
};

type ApiIntakeSummary = {
  file_name: string;
  rows_ingested: number;
  flagged: number;
  cleared: number;
  parse_errors: number;
  est_cost_usd: number;
  columns: string[];
  rule_stats: ApiIntakeRuleStat[];
  flagged_rows: ApiFlaggedRow[];
};

export type IntakeParseOptions = {
  materialityThreshold: number;
  estimatedAgentRunCostUsd: number;
  displayCurrency: string;
  segregationOfDutiesTokens: string[];
};

export const defaultIntakeParseOptions: IntakeParseOptions = {
  materialityThreshold: 50_000,
  estimatedAgentRunCostUsd: 0.21,
  displayCurrency: "USD",
  segregationOfDutiesTokens: ["admin", "system", "rkumar"],
};

type LedgerRow = Record<string, string>;

function mapIntakeSummary(payload: ApiIntakeSummary): IntakeSummary {
  return {
    fileName: payload.file_name,
    rowsIngested: payload.rows_ingested,
    flagged: payload.flagged,
    cleared: payload.cleared,
    parseErrors: payload.parse_errors,
    estCostUsd: payload.est_cost_usd,
    columns: payload.columns,
    ruleStats: payload.rule_stats,
    flaggedRows: payload.flagged_rows.map((row) => ({
      txnId: row.txn_id,
      vendor: row.vendor,
      account: row.account,
      amount: row.amount,
      rules: row.rules,
    })),
  };
}

export async function getIntakeSummary(): Promise<IntakeSummary | null> {
  const summary = await apiRequest<ApiIntakeSummary | null>("/intake/summary");
  return summary ? mapIntakeSummary(summary) : null;
}

function normalizeOptions(options: Partial<IntakeParseOptions>): IntakeParseOptions {
  const materialityThreshold =
    Number.isFinite(options.materialityThreshold) && Number(options.materialityThreshold) > 0
      ? Number(options.materialityThreshold)
      : defaultIntakeParseOptions.materialityThreshold;
  const estimatedAgentRunCostUsd =
    Number.isFinite(options.estimatedAgentRunCostUsd) && Number(options.estimatedAgentRunCostUsd) >= 0
      ? Number(options.estimatedAgentRunCostUsd)
      : defaultIntakeParseOptions.estimatedAgentRunCostUsd;
  const displayCurrency =
    options.displayCurrency?.trim().toUpperCase() || defaultIntakeParseOptions.displayCurrency;
  const segregationOfDutiesTokens =
    options.segregationOfDutiesTokens?.filter(Boolean).map((token) => token.toLowerCase()) ??
    defaultIntakeParseOptions.segregationOfDutiesTokens;

  return {
    materialityThreshold,
    estimatedAgentRunCostUsd,
    displayCurrency,
    segregationOfDutiesTokens,
  };
}

function ruleDefinitions(config: IntakeParseOptions): Array<{ flag: string; rule: string; tone: IntakeRuleStat["tone"] }> {
  return [
    { flag: "materiality", rule: `Materiality >= ${formatAmount(config.materialityThreshold, config.displayCurrency)}`, tone: "danger" },
    { flag: "fx outlier", rule: "FX outlier", tone: "warning" },
    { flag: "round-number", rule: "Round-number", tone: "warning" },
    { flag: "segregation of duties", rule: "Segregation of duties", tone: "danger" },
    { flag: "duplicate", rule: "Duplicate", tone: "info" },
    { flag: "unknown vendor", rule: "Unknown vendor", tone: "danger" },
    { flag: "off-hours", rule: "Off-hours posting", tone: "info" },
  ];
}

function parseDelimitedRows(text: string, delimiter: "," | "\t") {
  const rows: string[][] = [];
  let current = "";
  let row: string[] = [];
  let inQuotes = false;

  for (let index = 0; index < text.length; index += 1) {
    const char = text[index];
    const next = text[index + 1];

    if (char === '"' && next === '"' && inQuotes) {
      current += '"';
      index += 1;
      continue;
    }

    if (char === '"') {
      inQuotes = !inQuotes;
      continue;
    }

    if (char === delimiter && !inQuotes) {
      row.push(current.trim());
      current = "";
      continue;
    }

    if ((char === "\n" || char === "\r") && !inQuotes) {
      if (char === "\r" && next === "\n") {
        index += 1;
      }
      row.push(current.trim());
      if (row.some(Boolean)) {
        rows.push(row);
      }
      row = [];
      current = "";
      continue;
    }

    current += char;
  }

  row.push(current.trim());
  if (row.some(Boolean)) {
    rows.push(row);
  }

  return rows;
}

function normalizeHeader(value: string) {
  return value.trim().toLowerCase().replace(/\s+/g, "_");
}

function getValue(row: LedgerRow, keys: string[]) {
  return keys.map((key) => row[key]).find((value) => value && value.trim().length > 0) ?? "";
}

function parseAmount(value: string) {
  const cleaned = value.replace(/[^0-9.-]/g, "");
  const parsed = Number(cleaned);

  return Number.isFinite(parsed) ? parsed : 0;
}

function formatAmount(value: number, currency: string) {
  try {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency,
      maximumFractionDigits: 0,
    }).format(value);
  } catch {
    return `${currency} ${new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 }).format(value)}`;
  }
}

function isWeekendOrOffHours(value: string) {
  if (!value) {
    return false;
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return false;
  }

  const day = date.getDay();
  const hour = date.getHours();

  return day === 0 || day === 6 || hour < 6 || hour > 20;
}

function ruleLabelsForRow(row: LedgerRow, duplicateKeys: Set<string>, config: IntakeParseOptions) {
  const amount = Math.abs(parseAmount(getValue(row, ["amount_usd", "amount", "debit", "credit"])));
  const vendor = getValue(row, ["vendor", "vendor_name", "supplier"]);
  const currency = getValue(row, ["currency", "ccy"]).toUpperCase();
  const fxRate = parseAmount(getValue(row, ["fx_rate_used", "fx_rate", "rate"]));
  const postedBy = getValue(row, ["posted_by", "created_by", "user"]).toLowerCase();
  const date = getValue(row, ["date", "posted_at", "posting_date", "timestamp"]);
  const duplicateKey = `${vendor.toLowerCase()}|${amount}`;
  const rules: string[] = [];

  if (amount >= config.materialityThreshold) {
    rules.push("materiality");
  }

  if (amount >= 1_000 && amount % 1_000 === 0) {
    rules.push("round-number");
  }

  if (
    (currency && currency !== config.displayCurrency && fxRate === 0) ||
    fxRate > 2 ||
    (fxRate > 0 && fxRate < 0.2)
  ) {
    rules.push("fx outlier");
  }

  if (config.segregationOfDutiesTokens.some((token) => postedBy.includes(token))) {
    rules.push("segregation of duties");
  }

  if (duplicateKeys.has(duplicateKey)) {
    rules.push("duplicate");
  }

  if (!vendor || /unknown|test|family holdings|adreach/i.test(vendor)) {
    rules.push("unknown vendor");
  }

  if (isWeekendOrOffHours(date)) {
    rules.push("off-hours");
  }

  return rules;
}

function toRuleStats(flaggedRows: FlaggedRow[], config: IntakeParseOptions) {
  const counts = new Map<string, number>();
  const definitions = ruleDefinitions(config);
  const ruleNameByFlag = Object.fromEntries(definitions.map((definition) => [definition.flag, definition.rule]));

  flaggedRows.forEach((row) => {
    row.rules.forEach((rule) => {
      const label = ruleNameByFlag[rule] ?? rule;
      counts.set(label, (counts.get(label) ?? 0) + 1);
    });
  });

  return definitions.map(({ rule, tone }) => ({
    rule,
    tone,
    count: counts.get(rule) ?? 0,
  }));
}

function readFileText(file: File) {
  const textReader = (file as File & { text?: () => Promise<string> }).text;

  if (typeof textReader === "function") {
    return textReader.call(file);
  }

  return new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result ?? ""));
    reader.onerror = () => reject(new Error("Unable to read the uploaded file."));
    reader.readAsText(file);
  });
}

export async function parseLedgerFile(
  file: File,
  options: Partial<IntakeParseOptions> = {},
): Promise<IntakeSummary> {
  const config = normalizeOptions(options);
  const text = await readFileText(file);
  const delimiter = file.name.toLowerCase().endsWith(".tsv") ? "\t" : ",";
  const parsedRows = parseDelimitedRows(text, delimiter);
  const [rawHeaders, ...rawDataRows] = parsedRows;

  if (!rawHeaders || rawHeaders.length === 0) {
    throw new Error("The uploaded file does not contain a header row.");
  }

  const headers = rawHeaders.map(normalizeHeader);
  let parseErrors = 0;
  const rows: LedgerRow[] = [];

  rawDataRows.forEach((rawRow) => {
    if (rawRow.length !== headers.length) {
      parseErrors += 1;
      return;
    }

    rows.push(
      headers.reduce<LedgerRow>((acc, header, index) => {
        acc[header] = rawRow[index] ?? "";
        return acc;
      }, {}),
    );
  });

  const seen = new Set<string>();
  const duplicates = new Set<string>();
  rows.forEach((row) => {
    const vendor = getValue(row, ["vendor", "vendor_name", "supplier"]).toLowerCase();
    const amount = Math.abs(parseAmount(getValue(row, ["amount_usd", "amount", "debit", "credit"])));
    const key = `${vendor}|${amount}`;

    if (seen.has(key)) {
      duplicates.add(key);
    }
    seen.add(key);
  });

  const flaggedRows = rows
    .map((row): FlaggedRow => {
      const amount = Math.abs(parseAmount(getValue(row, ["amount_usd", "amount", "debit", "credit"])));

      return {
        txnId: getValue(row, ["txn_id", "transaction_id", "id"]) || "UNMAPPED",
        vendor: getValue(row, ["vendor", "vendor_name", "supplier"]) || "Unknown vendor",
        account: getValue(row, ["account", "category", "gl_account"]) || "Unmapped account",
        amount: formatAmount(amount, config.displayCurrency),
        rules: ruleLabelsForRow(row, duplicates, config),
      };
    })
    .filter((row) => row.rules.length > 0);

  return {
    fileName: file.name,
    rowsIngested: rows.length,
    flagged: flaggedRows.length,
    cleared: Math.max(rows.length - flaggedRows.length, 0),
    parseErrors,
    estCostUsd: Number((flaggedRows.length * config.estimatedAgentRunCostUsd).toFixed(2)),
    columns: headers,
    ruleStats: toRuleStats(flaggedRows, config),
    flaggedRows,
  };
}
