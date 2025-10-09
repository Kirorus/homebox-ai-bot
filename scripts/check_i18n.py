#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Set

LOCALES_DIR = Path(__file__).resolve().parents[1] / 'src' / 'i18n' / 'locales'


def flatten(d: Dict[str, Any], prefix: str = '') -> Dict[str, Any]:
	result: Dict[str, Any] = {}
	for k, v in d.items():
		key = f"{prefix}.{k}" if prefix else k
		if isinstance(v, dict):
			result.update(flatten(v, key))
		else:
			result[key] = v
	return result


def set_nested(d: Dict[str, Any], dotted_key: str, value: Any) -> None:
	parts = dotted_key.split('.')
	cur = d
	for p in parts[:-1]:
		if p not in cur or not isinstance(cur[p], dict):
			cur[p] = {}
		cur = cur[p]
	cur[parts[-1]] = value


def read_locale(path: Path) -> Dict[str, Any]:
	with path.open('r', encoding='utf-8') as f:
		return json.load(f)


def write_locale(path: Path, data: Dict[str, Any]) -> None:
	with path.open('w', encoding='utf-8') as f:
		json.dump(data, f, ensure_ascii=False, indent=2)
		f.write('\n')


def run_check(reference_lang: str, fix: bool, placeholder_mode: str) -> int:
	if not LOCALES_DIR.exists():
		print(f"Locales dir not found: {LOCALES_DIR}", file=sys.stderr)
		return 2
	files = sorted(p for p in LOCALES_DIR.glob('*.json'))
	if not files:
		print("No locale files found", file=sys.stderr)
		return 2

	locales: Dict[str, Dict[str, Any]] = {}
	flat: Dict[str, Dict[str, Any]] = {}
	for p in files:
		lang = p.stem
		try:
			data = read_locale(p)
		except Exception as e:
			print(f"Failed to read {p}: {e}", file=sys.stderr)
			return 2
		locales[lang] = data
		flat[lang] = flatten(data)

	if reference_lang not in flat:
		print(f"Reference language '{reference_lang}' not found in {LOCALES_DIR}", file=sys.stderr)
		return 2

	ref = flat[reference_lang]

	errors: List[str] = []
	for lang, d in flat.items():
		missing = sorted(k for k in ref.keys() if k not in d)
		if missing:
			errors.append(f"[{lang}] missing vs '{reference_lang}': {len(missing)}\n  " + "\n  ".join(missing[:50]) + ("\n  ..." if len(missing) > 50 else ""))
			if fix and lang != reference_lang:
				added = 0
				for key in missing:
					val = ref.get(key, "")
					if placeholder_mode == 'todo' and isinstance(val, str):
						val = f"TODO: {val}"
					elif placeholder_mode == 'key':
						val = key
					set_nested(locales[lang], key, val)
					added += 1
				# write back file
				write_locale(LOCALES_DIR / f"{lang}.json", locales[lang])
				print(f"[{lang}] auto-added {added} missing keys")

	# Also detect extras (keys absent in reference)
	for lang, d in flat.items():
		extra = sorted(k for k in d.keys() if k not in ref)
		if extra:
			errors.append(f"[{lang}] keys not in '{reference_lang}': {len(extra)}\n  " + "\n  ".join(extra[:50]) + ("\n  ..." if len(extra) > 50 else ""))

	if errors and not fix:
		print("i18n key sync check failed:\n" + "\n\n".join(errors))
		return 1
	elif errors and fix:
		print("i18n key sync: issues were found; missing keys have been added. Please translate placeholders.")
		return 0

	print(f"i18n key sync OK vs '{reference_lang}' across {len(files)} locales; {len(ref)} reference keys")
	return 0


def main() -> int:
	parser = argparse.ArgumentParser(description="Check (and optionally fix) i18n locale key sync")
	parser.add_argument('--ref', default='en', help="Reference language code (default: en)")
	parser.add_argument('--fix', action='store_true', help="Auto-add missing keys to other locales")
	parser.add_argument('--placeholder', choices=['copy', 'todo', 'key'], default='todo', help="How to fill values when fixing: copy=en value, todo=prefix 'TODO: ', key=use dotted key")
	args = parser.parse_args()
	return run_check(args.ref, args.fix, args.placeholder)


if __name__ == '__main__':
	sys.exit(main())
