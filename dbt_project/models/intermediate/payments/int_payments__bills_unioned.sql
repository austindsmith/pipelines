with

    electricity as (

        select item_name, provider, payment_amount as amount, payment_date, _source
        from {{ ref("stg_bills__electricity") }}

    ),

    gas as (

        select item_name, provider, payment_amount as amount, payment_date, _source
        from {{ ref("stg_bills__gas") }}

    ),

    water as (

        select
            item_name,
            provider,
            payment_amount as amount,
            due_date as payment_date,
            _source
        from {{ ref("stg_bills__water") }}

    ),

    unioned as (

        select *
        from electricity
        union all
        select *
        from gas
        union all
        select *
        from water

    )

select
    item_name,
    provider,
    'Austin' as payer,
    amount,
    payment_date,
    {{ dbt.date_trunc("month", "payment_date") }} as payment_month,
    _source
from unioned
