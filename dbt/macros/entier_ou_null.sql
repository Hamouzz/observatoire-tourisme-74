{# Convertit '-', '', '12.0' ou une valeur non numérique en entier ou NULL #}
{% macro entier_ou_null(colonne) -%}
    cast(try_cast(replace(nullif(nullif(trim({{ colonne }}), '-'), ''), ',', '.') as double) as integer)
{%- endmacro %}
