with
    source as (select * from {{ source("bills", "electricity") }}),

    renamed as (

        select
            trim(provider) as provider,
            trim(item_name) as item_name,
            customer_code,
            premise_code,
            trim(last_name) as last_name,
            trim(first_name) as first_name,
            trim(address1) as address_line_1,
            nullif(trim(address2), '') as address_line_2,
            trim(city) as city,
            trim(state) as state,
            trim(mail_zip) as zip_code,

            {{ parse_currency("amount") }} as payment_amount,

            {{ parse_date("payment_date", "MM/DD/YYYY") }} as payment_date,

            _source,
            _loaded_at

        from source

    )

select *
from renamed
