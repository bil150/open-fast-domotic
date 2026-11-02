/** Helpers to edit cron schedules without writing cron: "at HH:MM on these days". */

export interface SimpleSchedule {
  time: string; // "HH:MM"
  days: number[]; // 0 = Sunday .. 6 = Saturday; all 7 days = every day
}

const ALL_DAYS = [0, 1, 2, 3, 4, 5, 6];

export function buildCron({ time, days }: SimpleSchedule): string {
  const [hour = 0, minute = 0] = time.split(":").map((v) => parseInt(v, 10));
  const unique = Array.from(new Set(days)).sort((a, b) => a - b);
  const dayField = unique.length === 0 || unique.length === 7 ? "*" : unique.join(",");
  return `${minute} ${hour} * * ${dayField}`;
}

/** Returns null when the expression is not of the "at a time, on some days" kind. */
export function parseCron(cron: string): SimpleSchedule | null {
  const fields = cron.trim().split(/\s+/);
  if (fields.length !== 5) return null;
  const [minute = "", hour = "", dayOfMonth = "", month = "", dayOfWeek = ""] = fields;
  if (!/^\d{1,2}$/.test(minute) || !/^\d{1,2}$/.test(hour)) return null;
  if (dayOfMonth !== "*" || month !== "*") return null;
  if (Number(minute) > 59 || Number(hour) > 23) return null;

  let days = ALL_DAYS;
  if (dayOfWeek !== "*") {
    if (!/^[0-7](,[0-7])*$/.test(dayOfWeek)) return null;
    days = Array.from(new Set(dayOfWeek.split(",").map((d) => Number(d) % 7))).sort((a, b) => a - b);
  }
  return {
    time: `${hour.padStart(2, "0")}:${minute.padStart(2, "0")}`,
    days,
  };
}

/** "07:30 · Mon Tue Wed" — or the raw expression when it is not a simple schedule. */
export function describeCron(cron: string, dayNames: string[], everyDay: string): string {
  const parsed = parseCron(cron);
  if (!parsed) return cron;
  const days = parsed.days.length === 7 ? everyDay : parsed.days.map((d) => dayNames[d]).join(" ");
  return `${parsed.time} · ${days}`;
}
