import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import projectLicense from "../../generated/license.json";
import thirdParty from "../../generated/third-party.json";

interface Library {
  name: string;
  version: string;
  license: string;
  url: string;
  side: "client" | "server";
}

const LIBRARIES = thirdParty as Library[];

type Tab = "guide" | "license" | "libraries";

const TABS: { name: Tab; label: string }[] = [
  { name: "guide", label: "ABOUT_TAB_GUIDE" },
  { name: "license", label: "ABOUT_TAB_LICENSE" },
  { name: "libraries", label: "ABOUT_TAB_LIBRARIES" },
];

const GUIDE_SECTIONS = ["PAIRING", "LIGHTS", "FX", "SENSORS", "BUTTONS", "ZONES", "SCENES", "AUTOMATIONS", "SETTINGS"] as const;

function Guide() {
  const { t } = useTranslation();
  return (
    <section className="space-y-2">
      <p className="text-sm text-gray-500">{t("GUIDE_INTRO")}</p>
      {GUIDE_SECTIONS.map((section) => (
        <details
          key={section}
          className="border-2 border-gray-500 rounded-lg px-4 py-3 bg-gradient-to-r dark:from-gray-700 dark:to-gray-900"
        >
          <summary className="cursor-pointer font-semibold">{t(`GUIDE_${section}_TITLE`)}</summary>
          <p className="mt-2 text-sm whitespace-pre-line">{t(`GUIDE_${section}_BODY`)}</p>
        </details>
      ))}
    </section>
  );
}

function License() {
  const { t } = useTranslation();
  return (
    <section className="space-y-3">
      <p className="text-sm text-gray-500">{t("LICENSE_INTRO")}</p>
      <pre className="whitespace-pre-wrap break-words text-xs border-2 border-gray-500 rounded-lg p-4 bg-gray-200 dark:bg-gray-800">
        {projectLicense.text}
      </pre>
    </section>
  );
}

function Libraries() {
  const { t } = useTranslation();
  const [query, setQuery] = useState("");

  const groups = useMemo(() => {
    const needle = query.trim().toLowerCase();
    const matching = LIBRARIES.filter(
      (lib) => !needle || `${lib.name} ${lib.license}`.toLowerCase().includes(needle)
    );
    return (["client", "server"] as const).map((side) => ({
      side,
      title: t(side === "client" ? "CLIENT_SIDE" : "SERVER_SIDE"),
      libraries: matching.filter((lib) => lib.side === side),
    }));
  }, [query, t]);

  return (
    <section className="space-y-3">
      <p className="text-sm text-gray-500">{t("OPEN_SOURCE_INTRO")}</p>
      <input
        type="search"
        aria-label={t("SEARCH")}
        placeholder={t("SEARCH")}
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        className="bg-gray-200 dark:bg-gray-700 rounded p-2 w-full max-w-md"
      />

      {groups.every((g) => g.libraries.length === 0) && (
        <p className="p-4 text-center text-gray-500">{t("NO_RESULTS")}</p>
      )}

      {groups.map(
        (group) =>
          group.libraries.length > 0 && (
            <div key={group.side} className="space-y-2">
              <h4 className="text-lg">
                {group.title} <span className="text-sm text-gray-500">({group.libraries.length})</span>
              </h4>
              <ul className="flex flex-col space-y-2">
                {group.libraries.map((lib) => (
                  <li
                    key={`${lib.side}-${lib.name}`}
                    className="flex items-center justify-between gap-2 border-2 border-gray-500 rounded-lg px-4 py-3 bg-gradient-to-r dark:from-gray-700 dark:to-gray-900"
                  >
                    <span className="min-w-0">
                      <span className="block font-semibold truncate">
                        {lib.url ? (
                          <a href={lib.url} target="_blank" rel="noreferrer noopener" className="hover:underline">
                            {lib.name}
                          </a>
                        ) : (
                          lib.name
                        )}
                      </span>
                      <span className="block text-sm text-gray-500">{lib.version}</span>
                    </span>
                    <span className="flex-shrink-0 text-xs border-2 border-gray-400 rounded-full px-3 py-1" title={t("LICENSE")}>
                      {lib.license}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )
      )}
    </section>
  );
}

export function VAbout() {
  const { t } = useTranslation();
  const [tab, setTab] = useState<Tab>("guide");

  return (
    <div className="page-card !overflow-hidden">
      <div className="flex flex-wrap justify-between items-center gap-2 px-4 md:px-6 py-2">
        <h2 className="text-2xl">{t("ABOUT")}</h2>
      </div>

      <p className="px-4 md:px-6 pb-2 text-sm text-gray-500">{t("ABOUT_INTRO")}</p>

      <div role="tablist" className="flex flex-wrap gap-2 px-4 md:px-6 pb-2 text-sm">
        {TABS.map(({ name, label }) => (
          <button
            key={name}
            role="tab"
            aria-selected={tab === name}
            onClick={() => setTab(name)}
            className={`px-4 py-1 rounded-full border-2 ${tab === name ? "bg-gray-500 text-white border-gray-500" : "border-gray-400"}`}
          >
            {t(label)}
          </button>
        ))}
      </div>

      <div className="flex flex-col gap-4 p-4 flex-1 min-h-0 overflow-y-auto">
        {tab === "guide" && <Guide />}
        {tab === "license" && <License />}
        {tab === "libraries" && <Libraries />}
      </div>
    </div>
  );
}

export default VAbout;
