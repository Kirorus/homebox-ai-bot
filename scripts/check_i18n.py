#!/usr/bin/env python3
import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Set, Tuple

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


def read_locale(path: Path) -> Dict[str, Any]:
	with path.open('r', encoding='utf-8') as f:
		return json.load(f)


def main() -> int:
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

	# Take union and compare presence across languages
	all_keys: Set[str] = set()
	for d in flat.values():
		all_keys.update(d.keys())

	errors: List[str] = []
	for lang, d in flat.items():
		missing = sorted(k for k in all_keys if k not in d)
		if missing:
			errors.append(f"[{lang}] missing keys: {len(missing)}\n  " + "\n  ".join(missing[:50]) + ("\n  ..." if len(missing) > 50 else ""))

	# Also detect extra keys unique to a language (prone to typos)
	for lang, d in flat.items():
		extra = sorted(k for k in d.keys() if any(k not in flat[l] for l in flat if l != lang))
		# 'extra' here means keys present only in this lang and absent in at least one other
		# (we already reported missing on others, but calling out helps)
		if extra:
			errors.append(f"[{lang}] keys not present in some locales: {len(extra)}\n  " + "\n  ".join(extra[:50]) + ("\n  ..." if len(extra) > 50 else ""))

	if errors:
		print("i18n key sync check failed:\n" + "\n\n".join(errors))
		return 1

	print(f"i18n key sync check passed for {len(files)} locales, {len(all_keys)} keys")
	return 0


if __name__ == '__main__':
	sys.exit(main())
