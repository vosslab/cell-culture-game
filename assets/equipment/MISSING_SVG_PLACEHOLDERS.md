# Missing SVG Placeholders

This document lists every object currently using a placeholder SVG. Each placeholder is a standard dashed-border rectangle template with the object name displayed as text.

## Objects with Placeholder SVGs

| Placeholder Filename                | Object Name                                        | Reason                                                                                  | Status                            |
| ----------------------------------- | -------------------------------------------------- | --------------------------------------------------------------------------------------- | --------------------------------- |
| `power_supply_on.svg`               | `power_supply`                                     | No Servier candidate in Lab_apparatus / Chemistry / General_items / Microbiology search | Replace when suitable SVG sourced |
| `power_supply_off.svg`              | `power_supply`                                     | No Servier candidate in Lab_apparatus / Chemistry / General_items / Microbiology search | Replace when suitable SVG sourced |
| `heat_block_closed.svg`             | `heat_block`                                       | No Servier candidate in Lab_apparatus / Chemistry / General_items / Microbiology search | Replace when suitable SVG sourced |
| `heat_block_open.svg`               | `heat_block`                                       | No Servier candidate in Lab_apparatus / Chemistry / General_items / Microbiology search | Replace when suitable SVG sourced |
| `microwave_open.svg`                | `microwave`                                        | No Servier candidate in Lab_apparatus / Chemistry / General_items / Microbiology search | Replace when suitable SVG sourced |
| `lightbox_off.svg`                  | `lightbox`                                         | No Servier candidate in Lab_apparatus / Chemistry / General_items / Microbiology search | Replace when suitable SVG sourced |
| `gel_opening_tool.svg`              | `gel_opening_tool`                                 | No Servier candidate in Lab_apparatus / Chemistry / General_items / Microbiology search | Replace when suitable SVG sourced |
| `microtube_rack_24_placeholder.svg` | `microtube_rack_24` (formerly `eppendorf_rack_24`) | No Servier candidate in Lab_apparatus / Chemistry / General_items / Microbiology search | Replace when suitable SVG sourced |
| `electrode_module.svg`              | `electrode_module`                                 | No Servier candidate in Lab_apparatus / Chemistry / General_items / Microbiology search | Replace when suitable SVG sourced |

## Placeholder Template

All placeholder SVGs use a standard 100x100 viewBox with:

- Dashed border (4,2 stroke-dasharray) in color #999
- Center text displaying the object name in color #666
- Optional secondary line for state variants (e.g., "(off)", "(on)", "(closed)", "(open)")

When a suitable SVG is sourced, replace the placeholder file content with the new SVG while keeping the same filename so object YAML references continue to work. The tissue assets `kimwipe_pad.svg`, `lens_tissue.svg`, and `paper_towel_pad.svg` are now hand-authored scientific silhouettes and are not placeholder assets.
