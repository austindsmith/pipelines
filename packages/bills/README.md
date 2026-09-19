# Bills

This is my automated billing file download tool. It works for me, it probably won't work for you, but it's not for you. It's for me.

Basically, I really hate doing tedious manual things. Even opening all of my billing sites once a month. With the time saved there, now I can horse around with `dbt`. Because this is automated, I can theoretically load my entire billing history and start looking for patterns and trends and get real insights. Mogged.

## Download

All sites

```bash
uv run -m bills
```

Just one

```bash
uv run -m bills water
```

## Loading into DuckDB

Drop every table and re-load every csv

```bash
uv run -m bills.load --rebuild
```

Load only csvs not already in the database

```bash
uv run -m bills.load
```

Just load one site's csvs

```bash
uv run -m bills.load gas
```

Loading Google Sheet seed

```bash
uv run -m bills.seed
```
