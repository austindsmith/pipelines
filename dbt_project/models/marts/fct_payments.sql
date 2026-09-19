with

    bills as (

        select item_name, provider, payer, amount, payment_month, _source
        from {{ ref("int_payments__bills_unioned") }}

    ),

    spined as (

        select item_name, provider, payer, amount, payment_month, _source
        from {{ ref("int_payments__spined_to_months") }}

    )

select *
from bills
union all
select *
from spined
