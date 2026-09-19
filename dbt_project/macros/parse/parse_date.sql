{% macro parse_date(column, format) %}
    {{ return(adapter.dispatch("parse_date")(column, format)) }}
{% endmacro %}

{% macro default__parse_date(column, format) %}
    to_date(nullif(trim({{ column }}), ''), '{{ format }}')
{% endmacro %}

{% macro duckdb__parse_date(column, format) %}
    {%- set duckdb_format = (
        format
        | replace("YYYY", "%Y")
        | replace("Mon", "%b")
        | replace("MM", "%m")
        | replace("DD", "%d")
    ) -%}
    cast(strptime(nullif(trim({{ column }}), ''), '{{ duckdb_format }}') as date)
{% endmacro %}
