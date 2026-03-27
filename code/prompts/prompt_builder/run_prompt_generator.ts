import * as fs from "node:fs";
import * as path from "node:path";
import { generateDynamicSPARQLPrompt } from "./promptGenerator";
import { PredicatesMapping } from "./types";

type PromptProfile = {
    family: string;
    template_id: string;
    template_label: string;
    target_class_id: string;
    contribution_class: string;
    query_language?: string;
    prefix_profile?: string;
    output_base_name: string;
    prompt_generator_source?: string;
    enabled?: boolean;
};

type PromptProfilesConfig = {
	version: string;
	default_query_language?: string;
	default_prefix_profile?: string;
	profiles: Record<string, PromptProfile>;
	family_to_profile?: Record<string, string>;
};

type PathsConfig = {
  config: {
    prompt_profiles: string;
    dataset_registry?: string;
  };
  prompts: {
    rendered_dir: string;
    artifacts_dir: string;
    mapping_sources: Record<string, string>;
  };
  reports?: {
    validation_dir?: string;
  };
};

type PromptArtifact = {
	prompt_profile: string;
	template_id: string;
	template_label: string;
	contribution_class: string;
	target_class_id: string;
	query_language: string;
	prefix_profile: string;
	prompt_version: string;
	source_mapping_path: string;
	generated_at: string;
	template_mapping: PredicatesMapping;
	prompt_text: string;
};

const REPO_ROOT = path.resolve(__dirname, "../../..");
const DEFAULT_PATHS_CONFIG = path.join(REPO_ROOT, "code/config/paths.json");

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

function resolvePath(rawPath: string): string {
  if (path.isAbsolute(rawPath)) {
    return rawPath;
  }
  return path.join(REPO_ROOT, rawPath);
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

function getNextVersion(
  baseName: string,
  outputJsonDir: string,
  outputTxtDir: string
): number {
  const maxJsonVersion = getMaxVersionInDir(baseName, outputJsonDir, "json");
  const maxTxtVersion = getMaxVersionInDir(baseName, outputTxtDir, "txt");
  return Math.max(maxJsonVersion, maxTxtVersion) + 1;
}

function loadPathsConfig(pathsConfigPath: string): PathsConfig {
  const config = readJsonFile<PathsConfig>(pathsConfigPath);

  if (!config.config?.prompt_profiles) {
    throw new Error("paths.json is missing config.prompt_profiles");
  }

  if (!config.prompts?.rendered_dir) {
    throw new Error("paths.json is missing prompts.rendered_dir");
  }

  if (!config.prompts?.artifacts_dir) {
    throw new Error("paths.json is missing prompts.artifacts_dir");
  }

  if (!config.prompts?.mapping_sources) {
    throw new Error("paths.json is missing prompts.mapping_sources");
  }

  return config;
}

function loadPromptProfiles(promptProfilesPath: string): PromptProfilesConfig {
  const config = readJsonFile<PromptProfilesConfig>(promptProfilesPath);

  if (!config.profiles || typeof config.profiles !== "object") {
    throw new Error("prompt_profiles.json must contain a 'profiles' object");
  }

  return config;
}

function buildPromptArtifact(
  profileName: string,
  profile: PromptProfile,
  mappingPath: string,
  outputJsonDir: string,
  outputTxtDir: string,
  defaultQueryLanguage: string,
  defaultPrefixProfile: string
): void {
  if (!fs.existsSync(mappingPath)) {
    console.warn(`[SKIP] Mapping file not found for profile '${profileName}': ${mappingPath}`);
    return;
  }

  const mapping = readJsonFile<PredicatesMapping>(mappingPath);
  const promptText = generateDynamicSPARQLPrompt(
    mapping,
    profile.template_id,
    profile.template_label,
    profile.target_class_id
  );

  const baseName = profile.output_base_name;
  const nextVersion = getNextVersion(baseName, outputJsonDir, outputTxtDir);
  const versionTag = `v${nextVersion}`;

  const artifact: PromptArtifact = {
    prompt_profile: `${profileName}`,
    template_id: profile.template_id,
    template_label: profile.template_label,
    contribution_class: profile.contribution_class,
    target_class_id: profile.target_class_id,
    query_language: profile.query_language ?? defaultQueryLanguage,
    prefix_profile: profile.prefix_profile ?? defaultPrefixProfile,
    prompt_version: versionTag,
    source_mapping_path: mappingPath,
    generated_at: new Date().toISOString(),
    template_mapping: mapping,
    prompt_text: promptText,
  };

  const versionedJsonPath = path.join(
    outputJsonDir,
    `${baseName}_${versionTag}.json`
  );
  const versionedTxtPath = path.join(
    outputTxtDir,
    `${baseName}_${versionTag}.txt`
  );
  const latestJsonPath = path.join(
    outputJsonDir,
    `${baseName}_latest.json`
  );
  const latestTxtPath = path.join(
    outputTxtDir,
    `${baseName}_latest.txt`
  );

  writeJsonFile(versionedJsonPath, artifact);
  writeTextFile(versionedTxtPath, promptText);

  writeJsonFile(latestJsonPath, artifact);
  writeTextFile(latestTxtPath, promptText);

  console.log(`[OK] ${profileName} -> ${versionTag}`);
  console.log(`     JSON:         ${versionedJsonPath}`);
  console.log(`     TXT:          ${versionedTxtPath}`);
  console.log(`     LATEST JSON:  ${latestJsonPath}`);
  console.log(`     LATEST TXT:   ${latestTxtPath}`);
  console.log("");
}

function main(): void {
  const pathsConfig = loadPathsConfig(DEFAULT_PATHS_CONFIG);

  const promptProfilesPath = resolvePath(pathsConfig.config.prompt_profiles);
  const outputJsonDir = resolvePath(pathsConfig.prompts.artifacts_dir);
  const outputTxtDir = resolvePath(pathsConfig.prompts.rendered_dir);
  const mappingSources = pathsConfig.prompts.mapping_sources;

  const promptProfilesConfig = loadPromptProfiles(promptProfilesPath);

  const defaultQueryLanguage =
    promptProfilesConfig.default_query_language ?? "sparql";
  const defaultPrefixProfile =
    promptProfilesConfig.default_prefix_profile ?? "orkg_default";

  ensureDir(outputJsonDir);
  ensureDir(outputTxtDir);

  console.log(`Prompt profiles: ${promptProfilesPath}`);
  console.log(`JSON output dir: ${outputJsonDir}`);
  console.log(`TXT output dir:  ${outputTxtDir}`);
  console.log("");

  for (const [profileName, profile] of Object.entries(promptProfilesConfig.profiles)) {
    if (profile.enabled === false) {
      console.log(`[SKIP] Profile '${profileName}' is disabled.`);
      continue;
    }

    const rawMappingPath = mappingSources[profileName];
    if (!rawMappingPath) {
      console.warn(`[SKIP] No mapping source configured for profile '${profileName}' in paths.json`);
      continue;
    }

    const mappingPath = resolvePath(rawMappingPath);

    buildPromptArtifact(
      profileName,
      profile,
      mappingPath,
      outputJsonDir,
      outputTxtDir,
      defaultQueryLanguage,
      defaultPrefixProfile
    );
  }
}

main();