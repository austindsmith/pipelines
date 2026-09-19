{% macro parse_currency(column) %}
    cast(
        nullif(replace(replace(trim({{ column }}), '$', ''), ',', ''), '') as numeric(
            12, 2
        )
    )
{% endmacro %}
