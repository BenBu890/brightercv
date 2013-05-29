brightercv
==========

Brighter CV, for brighter job, brighter day.

Tables:

create table users (
    id varchar(50) not null,
    email varchar(100) not null,
    passwd varchar(100) not null,
    name varchar(100) not null,
    version bigint not null,
    primary key(id),
    unique key uk_email(email)
);

create table shortcuts (
    id varchar(50) not null,
    user_id varchar(50) not null,
    path varchar(100) not null,
    version bigint not null,
    primary key(id),
    unique key uk_path(path),
    unique key uk_user_id(user_id)
);

create table resumes (
    id varchar(50) not null,
    user_id varchar(50) not null,
    title varchar(100) not null,
    version bigint not null,
    primary key(id)
);

create table sections (
    id varchar(50) not null,
    user_id varchar(50) not null,
    resume_id varchar(50) not null,
    display_order bigint not null,
    kind varchar(50) not null,
    title varchar(100) not null,
    description varchar(2000) not null,
    version bigint not null,
    primary key(id),
    index idx_resume_id(resume_id)
);

create table entries (
    id varchar(50) not null,
    user_id varchar(50) not null,
    resume_id varchar(50) not null,
    section_id varchar(50) not null,
    display_order bigint not null,
    title varchar(100) not null,
    subtitle varchar(100) not null,
    picture varchar(1000) not null,
    description varchar(2000) not null,
    version bigint not null,
    primary key(id),
    index idx_section_id(section_id)
);
