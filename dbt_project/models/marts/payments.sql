with

    payments as (select * from {{ ref("fct_payments") }}),

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

    shares as (

        select
            payment_month,
            payer,
            amount_paid,
            total_paid,
            round(total_paid / payer_count, 2) as fair_share,
            round(amount_paid - total_paid / payer_count, 2) as balance
        from balances

    )

select
    payment_month,
    max(total_paid) as total_paid,
    max(case when balance < 0 then payer end) as owed_by,
    max(case when balance > 0 then payer end) as owed_to,
    max(balance) as amount_owed
from shares
group by payment_month
order by payment_month desc
