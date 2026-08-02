# Roadmap

Living plan for Shadowing Player. Order can change based on real user issues.

## Now (maintenance)

- [x] Public MIT release, README, CONTRIBUTING
- [x] Version flag, About dialog, file logs
- [x] Unit-test CI on Windows
- [x] First-run / on-demand **环境检查** checklist
- [x] Packaging script supports slim zip (`-SkipModel -Zip`)
- [ ] Keep responding to GitHub Issues within a few days
- [ ] One small real-user polish pass every week (docs or bugfix)
- [ ] Publish at least one portable zip on GitHub Releases

## Next (high user value)

1. **ASR language options** beyond fixed English (at least auto / en / zh if model supports)
2. **Export starred sentences** to SRT / Anki-friendly CSV
3. **WebM / more containers** if mpv handles them cleanly
4. Code-signed installer (optional, cost)

## Later

- Optional recording / self-compare (out of scope for v2 core)
- Child lock / learning stats
- Non-Windows ports (not planned until Windows is rock-solid)

## How we prioritize

1. Crash / data loss / wrong sentence timing  
2. Install friction on a clean Windows PC  
3. Practice workflow speed  
4. Nice-to-have UI  

## How to help

Open an issue with the templates under `.github/ISSUE_TEMPLATE/`, or a focused PR with tests.
