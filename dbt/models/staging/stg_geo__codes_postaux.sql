select distinct
    code_insee,
    lpad(code_postal, 5, '0') as code_postal
from {{ source('raw', 'communes_codes_postaux') }}
