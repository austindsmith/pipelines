# dbt

## Packages to try

- dbt-project-evaluator
- dbt-checkpoint
- dbt-osmosis
- elementary
- codegen

## Commands

Creating yaml files with codegen

```bash
dbt --quiet run-operation codegen.generate_source \
  --args '{schema_name: main, database_name: bills, name: bills, table_names: [electricity, gas, seed, water], generate_columns: true, include_descriptions: true}' \
  > models/staging/bills/_bills__sources.yml
```

Generating the staging models

```bash
for t in electricity gas seed water; do
  dbt --quiet run-operation codegen.generate_base_model \
    --args "{source_name: bills, table_name: $t}" \
    > "models/staging/bills/stg_bills__${t}.sql"
done
```

Running dbt-osmosis

```bash
dbt-osmosis yaml refactor
```
