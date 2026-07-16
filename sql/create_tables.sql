create table if not exists collection_tasks (
    task_id varchar primary key,
    method varchar not null,
    query varchar not null,
    region integer not null,
    status varchar not null default 'pending',
    attempts integer not null default 0,
    cost_estimate double,
    created_at timestamp not null default current_timestamp,
    started_at timestamp,
    finished_at timestamp,
    error_message varchar,
    raw_file_path varchar
);

create table if not exists queries (
    query_id varchar primary key,
    query varchar not null,
    normalized_query varchar,
    category varchar,
    intent varchar,
    super_intent varchar,
    product_type varchar,
    source varchar not null,
    first_seen_at timestamp not null default current_timestamp
);

alter table queries add column if not exists super_intent varchar;

create table if not exists frequency_monthly (
    query_id varchar not null,
    query varchar not null,
    region integer not null,
    month date not null,
    impressions integer,
    source varchar not null,
    fetched_at timestamp not null default current_timestamp
);

create table if not exists query_relations (
    source_query_id varchar not null,
    target_query_id varchar not null,
    relation_type varchar not null,
    weight double,
    source varchar not null,
    created_at timestamp not null default current_timestamp
);

create table if not exists clusters (
    cluster_id varchar primary key,
    cluster_name varchar not null,
    parent_cluster_id varchar,
    description varchar,
    created_at timestamp not null default current_timestamp
);

create table if not exists search_snapshots (
    task_id varchar primary key,
    query varchar not null,
    region integer not null,
    fetched_at timestamp not null,
    found_all bigint,
    found_phrase bigint,
    found_docs_all bigint,
    found_docs_phrase bigint,
    top_domain varchar,
    top_url varchar,
    source_file varchar not null,
    parsed_at timestamp not null default current_timestamp
);

create table if not exists search_results (
    task_id varchar not null,
    query varchar not null,
    region integer not null,
    fetched_at timestamp not null,
    position integer not null,
    domain varchar,
    url varchar,
    title varchar,
    snippet varchar,
    source_file varchar not null,
    parsed_at timestamp not null default current_timestamp,
    primary key (task_id, position)
);
