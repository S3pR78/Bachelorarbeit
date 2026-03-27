#!/usr/bin/env python3
"""
prompt_loader.py

Load the correct prompt for a canonical dataset entry by using:
- paths.json
- prompt_profiles.json
- the entry's family field

This loader is designed to work with the generated prompt files:
- rendered prompts:  ..._latest.txt
- optional artifacts: ..._latest.json

Path resolution rules:
- paths are resolved relative to the repository root unless already absolute
- repository root is inferred from this file location

Supported prompt profile styles:
1. Preferred:
	- paths.json defines prompts.rendered_dir
	- prompt_profiles.json defines output_base_name
	- final rendered path is built as:
		<rendered_dir>/<output_base_name>_latest.txt

2. Backward-compatible:
	- prompt_profiles.json defines latest_rendered_path directly
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


def get_repo_root() -> Path:
	"""
	Resolve the repository root from this file location.

	Expected file location:
		code/src/prompting/prompt_loader.py
	"""
	return Path(__file__).resolve().parents[3]


def resolve_path(repo_root: Path, raw_path: str) -> Path:
	"""
	Resolve a path relative to the repository root unless it is already absolute.
	"""
	path = Path(raw_path)
	if path.is_absolute():
		return path
	return repo_root / path


def load_json_object(path: Path) -> Dict[str, Any]:
	"""
	Load a JSON file and return its parsed object.
	"""
	with path.open("r", encoding="utf-8") as f:
		data = json.load(f)

	if not isinstance(data, dict):
		raise ValueError(f"Expected a JSON object in {path}, got {type(data).__name__}")

	return data


def load_text_file(path: Path) -> str:
	"""
	Load a UTF-8 text file.
	"""
	with path.open("r", encoding="utf-8") as f:
		return f.read()


def get_default_paths_config_path() -> Path:
	"""
	Return the default paths.json location.
	"""
	repo_root = get_repo_root()
	return repo_root / "code/config/paths.json"


def load_paths_config(paths_config_path: Path | None = None) -> Dict[str, Any]:
	"""
	Load paths.json.
	"""
	if paths_config_path is None:
		paths_config_path = get_default_paths_config_path()

	return load_json_object(paths_config_path)


def load_prompt_profiles_config(paths_config: Dict[str, Any]) -> Dict[str, Any]:
	"""
	Load prompt_profiles.json using the path from paths.json.
	"""
	repo_root = get_repo_root()

	config_section = paths_config.get("config")
	if not isinstance(config_section, dict):
		raise ValueError("paths.json must contain a 'config' object.")

	prompt_profiles_raw = config_section.get("prompt_profiles")
	if not isinstance(prompt_profiles_raw, str) or not prompt_profiles_raw.strip():
		raise ValueError("paths.json must define config.prompt_profiles as a non-empty string.")

	prompt_profiles_path = resolve_path(repo_root, prompt_profiles_raw)
	return load_json_object(prompt_profiles_path)


def get_profile_name_for_family(
	family: str,
	prompt_profiles_config: Dict[str, Any],
) -> str:
	"""
	Resolve the prompt profile name for a given family.
	"""
	if not isinstance(family, str) or not family.strip():
		raise ValueError("Entry 'family' must be a non-empty string.")

	family_to_profile = prompt_profiles_config.get("family_to_profile")
	if not isinstance(family_to_profile, dict):
		raise ValueError("prompt_profiles.json must contain a 'family_to_profile' object.")

	profile_name = family_to_profile.get(family)
	if not isinstance(profile_name, str) or not profile_name.strip():
		available = ", ".join(sorted(family_to_profile.keys()))
		raise ValueError(
			f"No prompt profile mapping found for family '{family}'. "
			f"Available families: {available}"
		)

	return profile_name


def get_profile_config(
	profile_name: str,
	prompt_profiles_config: Dict[str, Any],
) -> Dict[str, Any]:
	"""
	Return the profile configuration object for a given profile name.
	"""
	profiles = prompt_profiles_config.get("profiles")
	if not isinstance(profiles, dict):
		raise ValueError("prompt_profiles.json must contain a 'profiles' object.")

	profile = profiles.get(profile_name)
	if not isinstance(profile, dict):
		raise ValueError(f"Profile '{profile_name}' does not exist in prompt_profiles.json.")

	if profile.get("enabled") is False:
		raise ValueError(f"Profile '{profile_name}' is disabled.")

	return profile


def build_latest_rendered_prompt_path(
	profile_name: str,
	profile: Dict[str, Any],
	paths_config: Dict[str, Any],
) -> Path:
	"""
	Build the latest rendered prompt path.

	Preferred method:
	- use paths.json -> prompts.rendered_dir
	- use prompt_profiles.json -> profile.output_base_name

	Backward-compatible fallback:
	- use profile.latest_rendered_path directly if present
	"""
	repo_root = get_repo_root()

	latest_rendered_path = profile.get("latest_rendered_path")
	if isinstance(latest_rendered_path, str) and latest_rendered_path.strip():
		return resolve_path(repo_root, latest_rendered_path)

	output_base_name = profile.get("output_base_name")
	if not isinstance(output_base_name, str) or not output_base_name.strip():
		raise ValueError(
			f"Profile '{profile_name}' must define a non-empty 'output_base_name' "
			f"if 'latest_rendered_path' is not present."
		)

	prompts_section = paths_config.get("prompts")
	if not isinstance(prompts_section, dict):
		raise ValueError("paths.json must contain a 'prompts' object.")

	rendered_dir_raw = prompts_section.get("rendered_dir")
	if not isinstance(rendered_dir_raw, str) or not rendered_dir_raw.strip():
		raise ValueError("paths.json must define prompts.rendered_dir as a non-empty string.")

	rendered_dir = resolve_path(repo_root, rendered_dir_raw)
	return rendered_dir / f"{output_base_name}_latest.txt"


def load_prompt_text_by_family(
	family: str,
	paths_config_path: Path | None = None,
) -> str:
	"""
	Load the latest rendered prompt text for a given family.
	"""
	paths_config = load_paths_config(paths_config_path)
	prompt_profiles_config = load_prompt_profiles_config(paths_config)

	profile_name = get_profile_name_for_family(family, prompt_profiles_config)
	profile = get_profile_config(profile_name, prompt_profiles_config)

	prompt_path = build_latest_rendered_prompt_path(
		profile_name=profile_name,
		profile=profile,
		paths_config=paths_config,
	)

	if not prompt_path.exists():
		raise FileNotFoundError(
			f"Rendered prompt file not found for family '{family}' "
			f"(profile '{profile_name}'): {prompt_path}"
		)

	return load_text_file(prompt_path)


def inject_question(prompt_text: str, question: str) -> str:
	"""
	Inject the research question into the loaded prompt.

	Supported placeholders:
	- {{QUESTION}}
	- [Research Question]

	If no placeholder is found, append a final question section.
	"""
	if not isinstance(prompt_text, str) or not prompt_text.strip():
		raise ValueError("Prompt text must be a non-empty string.")

	if not isinstance(question, str) or not question.strip():
		raise ValueError("Question must be a non-empty string.")

	final_question = question.strip()

	if "{{QUESTION}}" in prompt_text:
		return prompt_text.replace("{{QUESTION}}", final_question)

	if "[Research Question]" in prompt_text:
		return prompt_text.replace("[Research Question]", final_question)

	return (
		prompt_text.rstrip()
		+ "\n\n## Input\n"
		+ f"**Research Question:** {final_question}\n"
	)


def build_prompt_for_entry(
	entry: Dict[str, Any],
	paths_config_path: Path | None = None,
) -> str:
	"""
	Load the correct prompt for a canonical dataset entry and inject the question.
	"""
	if not isinstance(entry, dict):
		raise ValueError("Entry must be a dictionary.")

	family = entry.get("family")
	question = entry.get("question")

	if not isinstance(family, str) or not family.strip():
		raise ValueError("Entry is missing a valid 'family' field.")

	if not isinstance(question, str) or not question.strip():
		raise ValueError("Entry is missing a valid 'question' field.")

	prompt_text = load_prompt_text_by_family(
		family=family,
		paths_config_path=paths_config_path,
	)

	return inject_question(prompt_text, question)


def get_prompt_metadata_for_family(
	family: str,
	paths_config_path: Path | None = None,
) -> Dict[str, Any]:
	"""
	Return useful prompt metadata for logging or debugging.
	"""
	paths_config = load_paths_config(paths_config_path)
	prompt_profiles_config = load_prompt_profiles_config(paths_config)

	profile_name = get_profile_name_for_family(family, prompt_profiles_config)
	profile = get_profile_config(profile_name, prompt_profiles_config)

	prompt_path = build_latest_rendered_prompt_path(
		profile_name=profile_name,
		profile=profile,
		paths_config=paths_config,
	)

	return {
		"family": family,
		"prompt_profile": profile_name,
		"template_id": profile.get("template_id"),
		"template_label": profile.get("template_label"),
		"target_class_id": profile.get("target_class_id"),
		"contribution_class": profile.get("contribution_class"),
		"prompt_path": str(prompt_path),
		"output_base_name": profile.get("output_base_name"),
	}