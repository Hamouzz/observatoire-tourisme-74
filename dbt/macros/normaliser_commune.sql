{#
  Normalise un nom de commune pour le rapprochement :
  'St-Gervais-les-Bains' / 'ST GERVAIS LES BAINS' -> 'SAINT GERVAIS LES BAINS'
#}
{% macro normaliser_commune(colonne) -%}
    trim(regexp_replace(
        regexp_replace(
            regexp_replace(upper(strip_accents({{ colonne }})), '[^A-Z0-9]+', ' ', 'g'),
        '(^| )STE( |$)', '\1SAINTE\2', 'g'),
    '(^| )ST( |$)', '\1SAINT\2', 'g'))
{%- endmacro %}
