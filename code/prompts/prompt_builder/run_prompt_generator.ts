import * as fs from "node:fs";
import * as path from "node:path";
import { generateDynamicSPARQLPrompt } from "./promptGenerator";
import { PredicatesMapping } from "./types";

type PromptConfig = {
  name: string;
  templateId: string;
  templateLabel: string;
  targetClassId: string;
  mappingPath: string;
};

type PromptArtifact = {
  prompt_profile: string;
  template_id: string;
  template_label: string;
  contribution_class: string;
  target_class_id: string;
  query_language: "sparql";
  prefix_profile: string;
  prompt_version: string;
  source_mapping_path: string;
  generated_at: string;
  template_mapping: PredicatesMapping;
  prompt_text: string;
};

const ROOT_DIR = path.resolve(__dirname, "../../..");
const OUTPUT_JSON_DIR = path.join(
  ROOT_DIR,
  "code/prompts/generated/artifacts"
);
const OUTPUT_TXT_DIR = path.join(
  ROOT_DIR,
  "code/prompts/generated/rendered"
);

const PROMPT_CONFIGS: PromptConfig[] = [
  {
    name: "nlp4re",
    templateId: "R1544125",
    templateLabel: "NLP for Requirements Engineering",
    targetClassId: "C121001",
    mappingPath: path.join(
      ROOT_DIR,
      "code/src/templates/nlp4re-template.json"
    ),
  },
  {
    name: "empirical_research",
    templateId: "R186491",
    templateLabel: "Empirical Research Practice",
    targetClassId: "C27001",
    mappingPath: path.join(
      ROOT_DIR,
      "code/src/templates/empirical_research_practice.json"
    ),
  },
];

function ensureDir(dirPath: string): void {
  fs.mkdirSync(dirPath, { recursive: true });
}

function readJsonFile<T>(filePath: string): T {
  const raw = fs.readFileSync(filePath, "utf-8");
  return JSON.parse(raw) as T;
}

function writeJsonFile(filePath: string, data: unknown): void {
  ensureDir(path.dirname(filePath));
  fs.writeFileSync(filePath, JSON.stringify(data, null, 2), "utf-8");
}

function writeTextFile(filePath: string, content: string): void {
  ensureDir(path.dirname(filePath));
  fs.writeFileSync(filePath, content, "utf-8");
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function getMaxVersionInDir(
  baseName: string,
  dirPath: string,
  extension: "json" | "txt"
): number {
  if (!fs.existsSync(dirPath)) {
    return 0;
  }

  const regex = new RegExp(
    `^${escapeRegExp(baseName)}_v(\\d+)\\.${extension}$`
  );

  let maxVersion = 0;

  for (const fileName of fs.readdirSync(dirPath)) {
    const match = fileName.match(regex);
    if (!match) {
      continue;
    }

    const version = Number.parseInt(match[1], 10);
    if (Number.isFinite(version) && version > maxVersion) {
      maxVersion = version;
    }
  }

  return maxVersion;
}

function getNextVersion(baseName: string): number {
  const maxJsonVersion = getMaxVersionInDir(baseName, OUTPUT_JSON_DIR, "json");
  const maxTxtVersion = getMaxVersionInDir(baseName, OUTPUT_TXT_DIR, "txt");
  return Math.max(maxJsonVersion, maxTxtVersion) + 1;
}

function buildBaseName(config: PromptConfig): string {
  return `${config.name}_${config.templateId}`;
}

function buildPromptArtifact(config: PromptConfig): void {
  if (!fs.existsSync(config.mappingPath)) {
    console.warn(`[SKIP] Mapping file not found: ${config.mappingPath}`);
    return;
  }

  const mapping = readJsonFile<PredicatesMapping>(config.mappingPath);

  const promptText = generateDynamicSPARQLPrompt(
    mapping,
    config.templateId,
    config.templateLabel,
    config.targetClassId
  );

  const baseName = buildBaseName(config);
  const nextVersion = getNextVersion(baseName);
  const versionTag = `v${nextVersion}`;

  const artifact: PromptArtifact = {
    prompt_profile: `${baseName}_${versionTag}`,
    template_id: config.templateId,
    template_label: config.templateLabel,
    contribution_class: `orkgc:${config.targetClassId}`,
    target_class_id: config.targetClassId,
    query_language: "sparql",
    prefix_profile: "orkg_default",
    prompt_version: versionTag,
    source_mapping_path: config.mappingPath,
    generated_at: new Date().toISOString(),
    template_mapping: mapping,
    prompt_text: promptText,
  };

  const versionedJsonPath = path.join(
    OUTPUT_JSON_DIR,
    `${baseName}_${versionTag}.json`
  );
  const versionedTxtPath = path.join(
    OUTPUT_TXT_DIR,
    `${baseName}_${versionTag}.txt`
  );
  const latestJsonPath = path.join(
    OUTPUT_JSON_DIR,
    `${baseName}_latest.json`
  );
  const latestTxtPath = path.join(
    OUTPUT_TXT_DIR,
    `${baseName}_latest.txt`
  );

  writeJsonFile(versionedJsonPath, artifact);
  writeTextFile(versionedTxtPath, promptText);

  writeJsonFile(latestJsonPath, artifact);
  writeTextFile(latestTxtPath, promptText);

  console.log(`[OK] ${config.templateLabel} -> ${versionTag}`);
  console.log(`     JSON:   ${versionedJsonPath}`);
  console.log(`     TXT:    ${versionedTxtPath}`);
  console.log(`     LATEST JSON: ${latestJsonPath}`);
  console.log(`     LATEST TXT:  ${latestTxtPath}`);
  console.log("");
}

function main(): void {
  ensureDir(OUTPUT_JSON_DIR);
  ensureDir(OUTPUT_TXT_DIR);

  console.log(`JSON output dir: ${OUTPUT_JSON_DIR}`);
  console.log(`TXT output dir:  ${OUTPUT_TXT_DIR}`);
  console.log("");

  for (const config of PROMPT_CONFIGS) {
    buildPromptArtifact(config);
  }
}

main();