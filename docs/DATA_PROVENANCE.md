# Data provenance and release checklist

The repository does **not** ship Wikipedia text or the generated database. The separately
hosted dataset must not be treated as verified merely because a license label is present.
Before publishing or replacing a dataset revision, fill in every field below from primary
records and keep the completed document with that revision.

## Source record

- Upstream project: Turkish Wikipedia
- Exact dump URL: `TODO`
- Dump filename: `TODO`
- Dump publication date: `TODO`
- Upstream SHA-256: `TODO`
- Downloaded-at UTC: `TODO`
- Applicable upstream license and terms URL: `TODO — verify against the exact dump`
- Required attribution text or URL: `TODO`

## Transformation record

- Source-code repository commit: `TODO`
- Command and options: `TODO`
- Python and SQLite versions: `TODO`
- Output schema version: `2`
- Output row count: `TODO`
- Output SHA-256: `TODO`
- Output byte size: `TODO`

## Release gate

- [ ] A second person or independent script verified both checksums.
- [ ] Attribution and share-alike obligations were reviewed for the exact source.
- [ ] The dataset card links this completed record and documents known limitations.
- [ ] The generated database can be reproduced from the recorded source and command.

Example checksum command:

```bash
sha256sum wiki_fts.db
```

Until the `TODO` fields are completed, the dataset's provenance and license status should
be described as **unverified**, not asserted as complete.
