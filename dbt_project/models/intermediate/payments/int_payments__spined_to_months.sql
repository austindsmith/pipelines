with

    recurring_costs as (select * from {{ ref("stg_bills__seed") }}),

    months as (

        {{
            dbt_utils.date_spine(
                datepart="month",
                start_date="cast('2023-01-01' as date)",
                end_date=dbt.dateadd(
                    "month", 1, dbt.date_trunc("month", dbt.current_timestamp())
                ),
            )
        }}

    ),

    spined as (

        select
            recurring_costs.item_name,
            recurring_costs.provider,
            recurring_costs.payer,
            recurring_costs.amount,
            cast(months.date_month as date) as payment_month,
            recurring_costs._source
        from recurring_costs
        inner join
            months
            on months.date_month
            >= {{ dbt.date_trunc("month", "recurring_costs.start_date") }}
            and (
                recurring_costs.end_date is null
                or months.date_month <= recurring_costs.end_date
            )
        where
            recurring_costs.frequency = 'monthly'
            or (
                recurring_costs.frequency = 'yearly'
                and extract(month from months.date_month)
                = extract(month from recurring_costs.start_date)
            )

    )

select *
from spined
