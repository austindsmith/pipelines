with

    source as (select * from {{ source("bills", "gas") }}),

    renamed as (

        select
            trim(provider) as provider,
            trim(item_name) as item_name,
            {{ parse_currency("payment_amount") }} as payment_amount,

            case
                when payment_date like '%/%'
                then {{ parse_date("split_part(payment_date, ' ', 1)", "MM/DD/YYYY") }}
                else {{ parse_date("payment_date", "Mon DD, YYYY") }}
            end as payment_date,

            _source,
            _loaded_at

        from source

    )

select *
from renamed
