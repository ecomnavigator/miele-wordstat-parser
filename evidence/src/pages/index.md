---
title: Miele SERP Report
---

```sql overview
select
  (select count(*) from bi.queries) as queries,
  (select count(*) from bi.organic_positions) as organic_positions,
  (select count(distinct normalized_domain) from bi.organic_positions) as domains,
  (select count(*) from bi.search_snapshots) as snapshots
```

<Grid cols=4>
  <BigValue data={overview} value=queries title="Queries" />
  <BigValue data={overview} value=organic_positions title="Organic Positions" />
  <BigValue data={overview} value=domains title="Domains" />
  <BigValue data={overview} value=snapshots title="Snapshots" />
</Grid>

## Domain Visibility

```sql domain_visibility
select
  normalized_domain,
  competitor_type,
  appearances_top_10,
  appearances_top_3,
  appearances_position_1,
  avg_position,
  best_position
from bi.domain_visibility
order by appearances_top_10 desc, appearances_top_3 desc
limit 30
```

<BarChart
  data={domain_visibility}
  x=normalized_domain
  y=appearances_top_10
  series=competitor_type
  title="Top domains in organic top 10"
/>

<DataTable data={domain_visibility} rows=30 />

## Commercial vs Informational

```sql competitors_by_super_intent
select
  super_intent,
  normalized_domain,
  competitor_type,
  appearances_top_10,
  appearances_top_3,
  appearances_position_1,
  avg_position
from bi.competitors_by_super_intent
order by super_intent, appearances_top_10 desc
limit 60
```

<BarChart
  data={competitors_by_super_intent}
  x=normalized_domain
  y=appearances_top_10
  series=super_intent
  title="Competitors by super intent"
/>

<DataTable data={competitors_by_super_intent} rows=30 />

## Query Demand Proxy

```sql top_queries
select
  query,
  category,
  intent,
  super_intent,
  total_found
from bi.search_snapshots
order by total_found desc
limit 50
```

<BarChart
  data={top_queries}
  x=query
  y=total_found
  series=super_intent
  title="Top queries by Yandex result count"
/>

<DataTable data={top_queries} rows=30 />

## Organic Positions

```sql organic_positions
select
  query,
  position,
  normalized_domain,
  competitor_type,
  title,
  url
from bi.organic_positions
order by query, position
limit 500
```

<DataTable data={organic_positions} rows=25 />

