{% macro date_reference() -%}
    {%- if var('date_reference') -%}DATE '{{ var("date_reference") }}'{%- else -%}current_date{%- endif -%}
{%- endmacro %}
