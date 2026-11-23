{# Portable surrogate key (md5 of the natural key) - works on DuckDB and Snowflake. #}
{% macro surrogate_key(column) -%}
    md5(cast({{ column }} as varchar))
{%- endmacro %}
