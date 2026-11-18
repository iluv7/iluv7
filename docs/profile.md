# Profile layout and artwork

The profile is light-only: a short intro with a full-body Misa Amane sticker floated
right, the original tech-stack icons at a smaller size, and the whale-maid
contribution calendar.

## Files

| File | Purpose |
| --- | --- |
| `assets/misa.png` | Cut-out portrait floated beside the intro (196px wide). |
| `assets/whale-maid.svg` | Contribution calendar with the whale maid, 844×160, self-contained. |

## Portrait

Built from the artwork supplied by the profile owner (736×981 JPEG):

1. Foreground cut with BiRefNet (`birefnet-general` via rembg).
2. Background patches on the left of the hip trimmed along the body outline.
3. 8px white sticker outline plus a soft drop shadow, exported at 400px wide.

The source artwork carries watermarks and typography baked into the pixels, so a few
marks remain on the character. Replacing `assets/misa.png` with a clean cut-out PNG
removes that limitation.

## Notes

- Tech Stack keeps the original devicon/Gopher icons at 32px; the AI Agent badge was
  dropped.
- GitHub Stats renders `assets/whale-maid.svg` (copied from `main`). Regenerating it is
  handled outside this repository.
