"""Focused provenance-classification tests for the SVG asset audit."""

import validation.svg.asset_audit as asset_audit


def test_servier_parser_excludes_other_source_rows() -> None:
	"""Only explicit category/Servier paths receive Servier provenance."""
	rows = """| Our Filename | Source | Notes |
| --- | --- | --- |
| `centrifuge.svg` | `Lab_apparatus/Servier/centrifuge.svg` | Servier |
| `tube_rack.svg` | `cc-by-4.0/Lab_apparatus/DBCLS/tube-rack.svg` | DBCLS |
| `power_supply.svg` | Repository-authored | Local |
""".splitlines()

	assert asset_audit.parse_servier_source_rows(rows) == {
		"centrifuge": (
			"OTHER_REPOS/bioicons/static/icons/cc-by-3.0/"
			"Lab_apparatus/Servier/centrifuge.svg",
			"Lab_apparatus",
		),
	}
