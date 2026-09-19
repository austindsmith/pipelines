with

    source as (select * from {{ source("bills", "seed") }}),

    renamed as (

        select
            trim(item_name) as item_name,
            trim(provider) as provider,
            trim(payer) as payer,
            lower(trim(frequency)) as frequency,
            nullif(trim(notes), '') as notes,

            {{ parse_currency("amount") }} as amount,

            {{ parse_date("start_date", "YYYY-MM-DD") }} as start_date,
            {{ parse_date("end_date", "YYYY-MM-DD") }} as end_date,

            _source,
            _loaded_at

        from source

    )

select *
from renamed
