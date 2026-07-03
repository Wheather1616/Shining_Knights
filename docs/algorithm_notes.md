# Algorithm and design notes

## Why the app sorts in SQLite rather than manually in Python

The Browse screen delegates sorting to SQLite using `ORDER BY` instead of loading every receipt into memory and sorting in the UI. This is intentional.

For a small dataset, either approach works. For a larger receipt database, database-side sorting is more scalable because SQLite can use indexes on columns such as `transaction_date`, `name`, `amount`, `receipt_no` and `member_no`. This avoids unnecessary Python-side work and keeps the GUI responsive.

## Search strategy

The app uses two search paths:

1. **SQLite FTS5 full-text search**, when available, for token-based search across receipt number, date, name, amount, payment type, member number, notes, custom fields and source.
2. **Fallback `LIKE` search** on a denormalised `search_text` column if the local SQLite build does not support FTS5.

This gives the project a more meaningful technical explanation than a simple string filter. The search feature is designed around the idea that receipt users may not know which exact field they are searching. A single query box therefore searches across all relevant fields.

## Grouping by date

Grouping is performed after the sorted search result is returned. This keeps grouping as a presentation concern: the underlying query still controls which records are returned and how they are ordered, while the UI decides whether to display them as a flat table or grouped by transaction date.

## Configurable fields

Custom receipt fields are stored in a JSON column rather than creating new database columns every time the settings change. This keeps the schema stable while still allowing the popup form and importer to change dynamically.

Core fields remain real columns because they are searched, sorted and indexed frequently:

- receipt number
- transaction date
- name
- amount
- payment type
- member number
- notes

## Import mapping

The importer uses header normalisation and alias matching. For example, `Receipt No`, `receipt_no`, `Receipt Number` and `receipt` can all map to the same internal `receipt_no` field.

That gives the app tolerance for messy historical spreadsheets while still keeping the database model consistent.
