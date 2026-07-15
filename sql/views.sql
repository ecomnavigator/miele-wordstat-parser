create or replace view monthly_category_demand as
select
    q.category,
    f.region,
    f.month,
    sum(f.impressions) as impressions
from frequency_monthly f
left join queries q on q.query_id = f.query_id
group by 1, 2, 3;

create or replace view top_queries_latest_month as
with latest as (
    select max(month) as month
    from frequency_monthly
)
select
    f.query,
    q.category,
    q.intent,
    f.region,
    f.month,
    f.impressions
from frequency_monthly f
join latest l on l.month = f.month
left join queries q on q.query_id = f.query_id
order by f.impressions desc;
