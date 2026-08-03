"""One recursive registry for logical SVG asset names and source provenance."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


class SvgAssetRegistryError(ValueError):
	"""Raised when recursive SVG discovery cannot produce unique logical names."""


@dataclass(frozen=True)
class SvgAssetEntry:
	"""One stable logical asset name and its current source-tree location."""

	asset_name: str
	source_path: Path
	source_relative_path: Path

	@property
	def public_relative_path(self) -> Path:
		"""Return the stable flattened URL path below the built SVG root.

		Source behavior directories are authoring organization. The public tree
		retains its top-level category and logical filename so source moves do not
		leak into YAML or published URLs.
		"""
		if len(self.source_relative_path.parts) < 2:
			raise SvgAssetRegistryError(
				f"SVG source must live below a top-level asset category: {self.source_path}"
			)
		return Path(self.source_relative_path.parts[0]) / f"{self.asset_name}.svg"


@dataclass(frozen=True)
class SvgAssetRegistry:
	"""Immutable globally unique recursive SVG registry."""

	assets_dir: Path
	entries: tuple[SvgAssetEntry, ...]

	@property
	def asset_names(self) -> frozenset[str]:
		"""Return every registered logical name."""
		return frozenset(entry.asset_name for entry in self.entries)

	def entry(self, asset_name: str) -> SvgAssetEntry:
		"""Resolve one logical name to its source and provenance."""
		for entry in self.entries:
			if entry.asset_name == asset_name:
				return entry
		raise KeyError(asset_name)

	def asset_path(self, asset_name: str) -> Path:
		"""Resolve one logical name to its current source path."""
		return self.entry(asset_name).source_path


def build_svg_asset_registry(assets_dir: Path) -> SvgAssetRegistry:
	"""Discover all SVGs recursively and reject ambiguous logical basenames."""
	assets_dir = assets_dir.resolve()
	by_name: dict[str, SvgAssetEntry] = {}
	for source_path in sorted(assets_dir.rglob("*.svg")):
		asset_name = source_path.stem
		entry = SvgAssetEntry(asset_name, source_path, source_path.relative_to(assets_dir))
		previous = by_name.get(asset_name)
		if previous is not None:
			raise SvgAssetRegistryError(
				f"duplicate logical SVG basename '{asset_name}': "
				f"{previous.source_path} and {source_path}"
			)
		by_name[asset_name] = entry
	return SvgAssetRegistry(assets_dir, tuple(by_name[name] for name in sorted(by_name)))
