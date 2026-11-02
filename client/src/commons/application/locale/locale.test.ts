import i18n from "i18next";
import { beforeAll, expect, test } from "vitest";
import ar from "./ar.json";
import en from "./en.json";
import fr from "./fr.json";
import { initTranslator } from "./locale";
import nl from "./nl.json";

const PLURAL_SUFFIX = /_(zero|one|two|few|many|other)$/;
const baseKeys = (locale: Record<string, string>) =>
  [...new Set(Object.keys(locale).map((key) => key.replace(PLURAL_SUFFIX, "")))].sort();

beforeAll(async () => {
  await initTranslator();
});

test("every language has the same keys as English (plural forms aside)", () => {
  const reference = baseKeys(en);
  expect(baseKeys(fr)).toEqual(reference);
  expect(baseKeys(nl)).toEqual(reference);
  expect(baseKeys(ar)).toEqual(reference);
});

test("every language provides at least one/other for plural keys", () => {
  for (const locale of [en, fr, nl]) {
    expect(locale).toHaveProperty("DEVICES_COUNT_one");
    expect(locale).toHaveProperty("DEVICES_COUNT_other");
  }
  expect(ar).toHaveProperty("DEVICES_COUNT_other");
});

test("plurals follow each language's rules", async () => {
  await i18n.changeLanguage("en");
  expect(i18n.t("DEVICES_COUNT", { count: 1 })).toBe("1 device");
  expect(i18n.t("DEVICES_COUNT", { count: 3 })).toBe("3 devices");

  await i18n.changeLanguage("fr");
  expect(i18n.t("DEVICES_COUNT", { count: 0 })).toBe("0 appareil"); // French: 0 is singular
  expect(i18n.t("DEVICES_COUNT", { count: 2 })).toBe("2 appareils");

  await i18n.changeLanguage("ar");
  expect(i18n.t("DEVICES_COUNT", { count: 2 })).toBe("جهازان");
  expect(i18n.t("DEVICES_COUNT", { count: 11 })).toBe("11 جهازًا");
});

test("interpolation", async () => {
  await i18n.changeLanguage("en");
  expect(i18n.t("SCENE_APPLIED", { ok: 2, total: 3 })).toBe("2/3 devices answered");
});
