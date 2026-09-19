with

    source as (select * from {{ source("bills", "water") }}),

    renamed as (

        select
            trim(provider) as provider,
            trim(item_name) as item_name,
            trim(account_number) as account_number,

            trim(service_address) as service_address,

            {{ parse_currency("amount_due") }} as amount_due,
            {{ parse_currency("payment_amount") }} as payment_amount,

            {{ parse_date("bill_date", "MM/DD/YYYY") }} as bill_date,
            {{ parse_date("due_date", "MM/DD/YYYY") }} as due_date,

            _source,
            _loaded_at

        from source

    )

select *
from renamed
