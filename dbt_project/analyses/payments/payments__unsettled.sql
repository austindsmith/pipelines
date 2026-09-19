{% set unsettled_through = var("unsettled_through", none) %}

with

    payments as (

        select *
        from {{ ref("fct_payments") }}
        where
            payment_month >= cast('{{ var("unsettled_since") }}' as date)
            {% if unsettled_through %}
                and payment_month <= cast('{{ unsettled_through }}' as date)
            {% else %}
                and payment_month
                < {{ dbt.date_trunc("month", dbt.current_timestamp()) }}
            {% endif %}

    ),

    payers as (select distinct payer from payments),

    months as (select distinct payment_month from payments),

    paid as (

        select payment_month, payer, sum(amount) as amount_paid
        from payments
        group by payment_month, payer

    ),

    balances as (

        select
            months.payment_month,
            payers.payer,
            coalesce(paid.amount_paid, 0) as amount_paid,
            sum(coalesce(paid.amount_paid, 0)) over (
                partition by months.payment_month
            ) as total_paid,
            count(*) over (partition by months.payment_month) as payer_count
        from months
        cross join payers
        left join
            paid
            on paid.payment_month = months.payment_month
            and paid.payer = payers.payer

    ),

    monthly as (

        select payment_month, payer, amount_paid - total_paid / payer_count as balance
        from balances

    ),

    running as (

        select
            payment_month,
            payer,
            balance,
            sum(balance) over (
                partition by payer
                order by payment_month
                rows between unbounded preceding and current row
            ) as running_balance
        from monthly

    )

select
    payment_month,
    max(case when balance < 0 then payer end) as owed_by_this_month,
    round(max(balance), 2) as owed_this_month,
    max(case when running_balance < 0 then payer end) as owed_by_to_date,
    round(max(running_balance), 2) as owed_to_date
from running
group by payment_month
order by payment_month
