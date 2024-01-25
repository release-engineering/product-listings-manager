SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'SQL_ASCII';
SET standard_conforming_strings = off;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET escape_string_warning = off;
SET row_security = off;

CREATE OR REPLACE PROCEDURAL LANGUAGE plpgsql;

CREATE ROLE compose;

SET default_tablespace = '';

CREATE TABLE public.capability (
    id integer NOT NULL,
    name character varying NOT NULL,
    version character varying(32)
);

CREATE SEQUENCE public.capability_id_seq
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

CREATE TABLE public.changelogs (
    packages_id integer NOT NULL,
    date date NOT NULL,
    author character varying NOT NULL,
    text text,
    id integer DEFAULT nextval(('changelogs_id_seq'::text)::regclass)
);

CREATE SEQUENCE public.changelogs_id_seq
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

CREATE SEQUENCE public.file_id_seq
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

CREATE TABLE public.filename (
    id integer NOT NULL,
    file character varying NOT NULL
);

CREATE SEQUENCE public.filename_id_seq
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

CREATE TABLE public.fileowner (
    id integer NOT NULL,
    username character varying NOT NULL,
    groupname character varying NOT NULL
);

CREATE SEQUENCE public.fileowner_id_seq
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

CREATE TABLE public.files (
    id integer NOT NULL,
    name_id integer NOT NULL,
    type_id integer NOT NULL,
    owner_id integer NOT NULL,
    mode integer NOT NULL,
    size integer NOT NULL,
    flags integer NOT NULL,
    mtime timestamp without time zone NOT NULL,
    vflags integer NOT NULL,
    md5sum character varying,
    statinfo integer NOT NULL,
    linksto character varying
);

CREATE TABLE public.filetype (
    id integer NOT NULL,
    name character varying(10) NOT NULL,
    description character varying NOT NULL
);

CREATE VIEW public.files_view AS
SELECT f.id AS file_id, f."mode" AS file_mode, fo.username AS file_user, fo.groupname AS file_group, f.size AS file_size, ft.name AS file_type, CASE WHEN (f.linksto IS NULL) THEN (fn.file)::text WHEN ((f.linksto)::text = ''::text) THEN (fn.file)::text ELSE (((fn.file)::text || ' -> '::text) || (f.linksto)::text) END AS file_path, f.md5sum AS file_md5 FROM public.files f, public.filename fn, public.filetype ft, public.fileowner fo WHERE (((f.name_id = fn.id) AND (f.type_id = ft.id)) AND (f.owner_id = fo.id));

CREATE TABLE public.match_versions (
    name character varying,
    product character varying(100)
);

CREATE SEQUENCE public.module_id_seq
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

CREATE TABLE public.module_overrides (
    name character varying NOT NULL,
    stream character varying NOT NULL,
    product integer NOT NULL,
    product_arch character varying(32) NOT NULL
);

CREATE TABLE public.modules (
    id integer NOT NULL,
    name character varying NOT NULL,
    stream character varying NOT NULL,
    version character varying NOT NULL
);

CREATE TABLE public.overrides (
    name character varying NOT NULL,
    pkg_arch character varying(32) NOT NULL,
    product_arch character varying(32) NOT NULL,
    product integer NOT NULL,
    include boolean DEFAULT true
);

CREATE TABLE public.package_caps (
    package_id integer NOT NULL,
    cap_id integer NOT NULL,
    sense integer DEFAULT 0 NOT NULL,
    cap_type character(1) NOT NULL,
    CONSTRAINT package_caps_type_check CHECK (((((cap_type = 'P'::bpchar) OR (cap_type = 'R'::bpchar)) OR (cap_type = 'O'::bpchar)) OR (cap_type = 'C'::bpchar)))
);

CREATE VIEW public.package_capabilities AS
SELECT pcaps.package_id, pcaps.cap_type, CASE WHEN (pcaps.cap_type = 'R'::bpchar) THEN 'requires'::text WHEN (pcaps.cap_type = 'P'::bpchar) THEN 'provides'::text WHEN (pcaps.cap_type = 'O'::bpchar) THEN 'obsoletes'::text WHEN (pcaps.cap_type = 'C'::bpchar) THEN 'conflicts'::text ELSE 'do not know'::text END AS dep_type, pcaps.cap_id, caps.name, caps.version, pcaps.sense FROM public.package_caps pcaps, public.capability caps WHERE (pcaps.cap_id = caps.id);

CREATE VIEW public.package_conflicts AS
SELECT package_capabilities.package_id, package_capabilities.cap_type, package_capabilities.dep_type, package_capabilities.cap_id, package_capabilities.name, package_capabilities.version, package_capabilities.sense FROM public.package_capabilities WHERE (package_capabilities.cap_type = 'C'::bpchar);

CREATE TABLE public.package_files (
    package_id integer NOT NULL,
    file_id integer NOT NULL
);

CREATE SEQUENCE public.package_id_seq
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

CREATE VIEW public.package_obsoletes AS
SELECT package_capabilities.package_id, package_capabilities.cap_type, package_capabilities.dep_type, package_capabilities.cap_id, package_capabilities.name, package_capabilities.version, package_capabilities.sense FROM public.package_capabilities WHERE (package_capabilities.cap_type = 'O'::bpchar);

CREATE VIEW public.package_provides AS
SELECT package_capabilities.package_id, package_capabilities.cap_type, package_capabilities.dep_type, package_capabilities.cap_id, package_capabilities.name, package_capabilities.version, package_capabilities.sense FROM public.package_capabilities WHERE (package_capabilities.cap_type = 'P'::bpchar);

CREATE VIEW public.package_requires AS
SELECT package_capabilities.package_id, package_capabilities.cap_type, package_capabilities.dep_type, package_capabilities.cap_id, package_capabilities.name, package_capabilities.version, package_capabilities.sense FROM public.package_capabilities WHERE (package_capabilities.cap_type = 'R'::bpchar);

CREATE TABLE public.packages (
    id integer NOT NULL,
    name character varying NOT NULL,
    epoch integer,
    version character varying NOT NULL,
    release character varying NOT NULL,
    arch character varying(32) NOT NULL,
    payload_md5 character varying NOT NULL,
    build_time timestamp without time zone NOT NULL,
    build_host character varying NOT NULL,
    size bigint NOT NULL,
    sourcerpm character varying,
    rpm_group character varying NOT NULL,
    license character varying NOT NULL,
    summary character varying NOT NULL,
    description text NOT NULL,
    distribution character varying NOT NULL,
    url character varying,
    vendor character varying,
    script_pre text,
    script_post text,
    script_preun text,
    script_postun text,
    script_verify text
);

CREATE TABLE public.products (
    id integer NOT NULL,
    label character varying(100) NOT NULL,
    version character varying(100) NOT NULL,
    variant character varying(200),
    allow_source_only boolean DEFAULT false
);

CREATE SEQUENCE public.products_id_seq
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

CREATE SEQUENCE public.tree_id_seq
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

CREATE TABLE public.tree_modules (
    trees_id integer NOT NULL,
    modules_id integer NOT NULL
);

CREATE TABLE public.tree_packages (
    trees_id integer NOT NULL,
    packages_id integer NOT NULL
);

CREATE TABLE public.tree_product_map (
    tree_id integer NOT NULL,
    product_id integer NOT NULL
);

CREATE TABLE public.trees (
    id integer NOT NULL,
    name character varying NOT NULL,
    buildname character varying NOT NULL,
    date date NOT NULL,
    arch character varying(10) NOT NULL,
    treetype character varying,
    treeinfo character varying,
    imported integer DEFAULT 0 NOT NULL,
    product integer,
    compatlayer boolean DEFAULT false
);

ALTER TABLE ONLY public.capability
    ADD CONSTRAINT capability_id_pk PRIMARY KEY (id);

ALTER TABLE ONLY public.capability
    ADD CONSTRAINT capability_name_version_uq UNIQUE (name, version);

ALTER TABLE ONLY public.changelogs
    ADD CONSTRAINT changelogs_id_un UNIQUE (id);

ALTER TABLE ONLY public.filename
    ADD CONSTRAINT filename_file_uq UNIQUE (file);

ALTER TABLE ONLY public.filename
    ADD CONSTRAINT filename_id_pk PRIMARY KEY (id);

ALTER TABLE ONLY public.fileowner
    ADD CONSTRAINT fileowner_id_pk PRIMARY KEY (id);

ALTER TABLE ONLY public.fileowner
    ADD CONSTRAINT fileowner_user_group_uq UNIQUE (username, groupname);

ALTER TABLE ONLY public.files
    ADD CONSTRAINT files_id_pk PRIMARY KEY (id);

ALTER TABLE ONLY public.filetype
    ADD CONSTRAINT filetype_id_pk PRIMARY KEY (id);

ALTER TABLE ONLY public.filetype
    ADD CONSTRAINT filetype_name_uq UNIQUE (name);

ALTER TABLE ONLY public.match_versions
    ADD CONSTRAINT match_versions_un UNIQUE (name, product);

ALTER TABLE ONLY public.module_overrides
    ADD CONSTRAINT module_overrides_un UNIQUE (name, stream, product, product_arch);

ALTER TABLE ONLY public.modules
    ADD CONSTRAINT modules_id_pk PRIMARY KEY (id);

ALTER TABLE ONLY public.modules
    ADD CONSTRAINT modules_nsv_uq UNIQUE (name, stream, version);

ALTER TABLE ONLY public.overrides
    ADD CONSTRAINT overrides_un UNIQUE (name, pkg_arch, product_arch, product);

ALTER TABLE ONLY public.package_caps
    ADD CONSTRAINT package_caps_pid_cid_sense_uq UNIQUE (package_id, cap_id, sense, cap_type);

ALTER TABLE ONLY public.package_files
    ADD CONSTRAINT package_files_pid_fid_uq UNIQUE (package_id, file_id);

ALTER TABLE ONLY public.packages
    ADD CONSTRAINT packages_id_pk PRIMARY KEY (id);

ALTER TABLE ONLY public.packages
    ADD CONSTRAINT packages_nvra_sum_uq UNIQUE (name, version, release, arch, payload_md5);

ALTER TABLE ONLY public.products
    ADD CONSTRAINT products_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.tree_modules
    ADD CONSTRAINT tree_modules_tid_mid_uq UNIQUE (trees_id, modules_id);

ALTER TABLE ONLY public.tree_packages
    ADD CONSTRAINT tree_packages_tid_pid_uq UNIQUE (trees_id, packages_id);

ALTER TABLE ONLY public.tree_product_map
    ADD CONSTRAINT tree_product_map_tree_id_key UNIQUE (tree_id, product_id);

ALTER TABLE ONLY public.trees
    ADD CONSTRAINT trees_buildname_arch_uq UNIQUE (buildname, arch);

ALTER TABLE ONLY public.trees
    ADD CONSTRAINT trees_id_pk PRIMARY KEY (id);

ALTER TABLE ONLY public.trees
    ADD CONSTRAINT trees_name_arch_uq UNIQUE (name, arch);

CREATE INDEX changelogs_pid_idx ON public.changelogs USING btree (packages_id);

CREATE INDEX files_name_id_idx ON public.files USING btree (name_id, mtime);

CREATE INDEX package_files_file_idx ON public.package_files USING btree (file_id);

CREATE INDEX packages_name_arch ON public.packages USING btree (name, arch);

CREATE INDEX products_label_idx ON public.products USING btree (label);

CREATE INDEX tree_packages_package_idx ON public.tree_packages USING btree (packages_id);

CREATE INDEX tree_product_map_product_id_idx ON public.tree_product_map USING btree (product_id);

CREATE INDEX tree_product_map_tree_id_idx ON public.tree_product_map USING btree (tree_id);

CREATE INDEX trees_compatlayer_idx ON public.trees USING btree (compatlayer);

CREATE INDEX trees_imported_idx ON public.trees USING btree (imported);

CREATE INDEX trees_product_idx ON public.trees USING btree (product);

ALTER TABLE ONLY public.trees
    ADD CONSTRAINT "$1" FOREIGN KEY (product) REFERENCES public.products(id);

ALTER TABLE ONLY public.overrides
    ADD CONSTRAINT "$1" FOREIGN KEY (product) REFERENCES public.products(id);

ALTER TABLE ONLY public.tree_product_map
    ADD CONSTRAINT "$1" FOREIGN KEY (tree_id) REFERENCES public.trees(id);

ALTER TABLE ONLY public.module_overrides
    ADD CONSTRAINT "$1" FOREIGN KEY (product) REFERENCES public.products(id);

ALTER TABLE ONLY public.tree_product_map
    ADD CONSTRAINT "$2" FOREIGN KEY (product_id) REFERENCES public.products(id);

ALTER TABLE ONLY public.changelogs
    ADD CONSTRAINT changelogs_pid_fk FOREIGN KEY (packages_id) REFERENCES public.packages(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.files
    ADD CONSTRAINT files_name_id_fk FOREIGN KEY (name_id) REFERENCES public.filename(id);

ALTER TABLE ONLY public.files
    ADD CONSTRAINT files_owner_id_fk FOREIGN KEY (owner_id) REFERENCES public.fileowner(id);

ALTER TABLE ONLY public.files
    ADD CONSTRAINT files_type_id_fk FOREIGN KEY (type_id) REFERENCES public.filetype(id);

ALTER TABLE ONLY public.package_caps
    ADD CONSTRAINT package_caps_cid_fk FOREIGN KEY (cap_id) REFERENCES public.capability(id);

ALTER TABLE ONLY public.package_caps
    ADD CONSTRAINT package_caps_pid_fk FOREIGN KEY (package_id) REFERENCES public.packages(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.package_files
    ADD CONSTRAINT package_files_fid_fk FOREIGN KEY (file_id) REFERENCES public.files(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.package_files
    ADD CONSTRAINT package_files_pid_fk FOREIGN KEY (package_id) REFERENCES public.packages(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.tree_modules
    ADD CONSTRAINT treemodules_mid_fk FOREIGN KEY (modules_id) REFERENCES public.modules(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.tree_modules
    ADD CONSTRAINT treemodules_tid_fk FOREIGN KEY (trees_id) REFERENCES public.trees(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.tree_packages
    ADD CONSTRAINT treepkgs_pid_fk FOREIGN KEY (packages_id) REFERENCES public.packages(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.tree_packages
    ADD CONSTRAINT treepkgs_tid_fk FOREIGN KEY (trees_id) REFERENCES public.trees(id) ON DELETE CASCADE;

REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT ALL ON SCHEMA public TO PUBLIC;
GRANT USAGE ON SCHEMA public TO compose;

REVOKE ALL ON LANGUAGE plpgsql FROM PUBLIC;
GRANT ALL ON LANGUAGE plpgsql TO compose;

REVOKE ALL ON TABLE public.capability FROM PUBLIC;
GRANT SELECT ON TABLE public.capability TO compose;
GRANT INSERT,DELETE,UPDATE ON TABLE public.capability TO plm;

REVOKE ALL ON SEQUENCE public.capability_id_seq FROM PUBLIC;
GRANT SELECT,UPDATE ON SEQUENCE public.capability_id_seq TO plm;

REVOKE ALL ON TABLE public.changelogs FROM PUBLIC;
GRANT SELECT ON TABLE public.changelogs TO compose;
GRANT INSERT,DELETE,UPDATE ON TABLE public.changelogs TO plm;

REVOKE ALL ON SEQUENCE public.changelogs_id_seq FROM PUBLIC;
GRANT SELECT,USAGE ON SEQUENCE public.changelogs_id_seq TO plm;

REVOKE ALL ON SEQUENCE public.file_id_seq FROM PUBLIC;
GRANT SELECT,UPDATE ON SEQUENCE public.file_id_seq TO plm;

REVOKE ALL ON TABLE public.filename FROM PUBLIC;
GRANT SELECT ON TABLE public.filename TO compose;
GRANT INSERT,DELETE,UPDATE ON TABLE public.filename TO plm;

REVOKE ALL ON SEQUENCE public.filename_id_seq FROM PUBLIC;
GRANT SELECT,UPDATE ON SEQUENCE public.filename_id_seq TO plm;

REVOKE ALL ON TABLE public.fileowner FROM PUBLIC;
GRANT SELECT ON TABLE public.fileowner TO compose;
GRANT INSERT,DELETE,UPDATE ON TABLE public.fileowner TO plm;

REVOKE ALL ON SEQUENCE public.fileowner_id_seq FROM PUBLIC;
GRANT SELECT,UPDATE ON SEQUENCE public.fileowner_id_seq TO plm;

REVOKE ALL ON TABLE public.files FROM PUBLIC;
GRANT SELECT ON TABLE public.files TO compose;
GRANT INSERT,DELETE,UPDATE ON TABLE public.files TO plm;

REVOKE ALL ON TABLE public.filetype FROM PUBLIC;
GRANT SELECT ON TABLE public.filetype TO compose;
GRANT INSERT,DELETE,UPDATE ON TABLE public.filetype TO plm;

REVOKE ALL ON TABLE public.files_view FROM PUBLIC;
GRANT SELECT ON TABLE public.files_view TO compose;

REVOKE ALL ON TABLE public.match_versions FROM PUBLIC;
GRANT SELECT,REFERENCES,TRIGGER ON TABLE public.match_versions TO compose;
GRANT ALL ON TABLE public.match_versions TO plm;

REVOKE ALL ON SEQUENCE public.module_id_seq FROM PUBLIC;
GRANT SELECT ON SEQUENCE public.module_id_seq TO compose;
GRANT ALL ON SEQUENCE public.module_id_seq TO plm;

REVOKE ALL ON TABLE public.module_overrides FROM PUBLIC;
GRANT SELECT ON TABLE public.module_overrides TO compose;
GRANT ALL ON TABLE public.module_overrides TO plm;

REVOKE ALL ON TABLE public.modules FROM PUBLIC;
GRANT SELECT ON TABLE public.modules TO compose;
GRANT ALL ON TABLE public.modules TO plm;

REVOKE ALL ON TABLE public.overrides FROM PUBLIC;

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE public.overrides TO plm;

REVOKE ALL ON TABLE public.package_caps FROM PUBLIC;
GRANT SELECT ON TABLE public.package_caps TO compose;
GRANT INSERT,DELETE,UPDATE ON TABLE public.package_caps TO plm;

REVOKE ALL ON TABLE public.package_capabilities FROM PUBLIC;
GRANT SELECT ON TABLE public.package_capabilities TO compose;

REVOKE ALL ON TABLE public.package_conflicts FROM PUBLIC;
GRANT SELECT ON TABLE public.package_conflicts TO compose;

REVOKE ALL ON TABLE public.package_files FROM PUBLIC;
GRANT SELECT ON TABLE public.package_files TO compose;
GRANT INSERT,DELETE,UPDATE ON TABLE public.package_files TO plm;

REVOKE ALL ON SEQUENCE public.package_id_seq FROM PUBLIC;
GRANT SELECT,UPDATE ON SEQUENCE public.package_id_seq TO plm;

REVOKE ALL ON TABLE public.package_obsoletes FROM PUBLIC;
GRANT SELECT ON TABLE public.package_obsoletes TO compose;

REVOKE ALL ON TABLE public.package_provides FROM PUBLIC;
GRANT SELECT ON TABLE public.package_provides TO compose;

REVOKE ALL ON TABLE public.package_requires FROM PUBLIC;
GRANT SELECT ON TABLE public.package_requires TO compose;

REVOKE ALL ON TABLE public.packages FROM PUBLIC;
GRANT SELECT ON TABLE public.packages TO compose;
GRANT INSERT,DELETE,UPDATE ON TABLE public.packages TO plm;

REVOKE ALL ON TABLE public.products FROM PUBLIC;
GRANT SELECT ON TABLE public.products TO compose;
GRANT ALL ON TABLE public.products TO plm;

REVOKE ALL ON SEQUENCE public.products_id_seq FROM PUBLIC;
GRANT SELECT ON SEQUENCE public.products_id_seq TO compose;
GRANT SELECT,UPDATE ON SEQUENCE public.products_id_seq TO plm;

REVOKE ALL ON SEQUENCE public.tree_id_seq FROM PUBLIC;
GRANT SELECT,UPDATE ON SEQUENCE public.tree_id_seq TO plm;

REVOKE ALL ON TABLE public.tree_modules FROM PUBLIC;
GRANT SELECT ON TABLE public.tree_modules TO compose;
GRANT ALL ON TABLE public.tree_modules TO plm;

REVOKE ALL ON TABLE public.tree_packages FROM PUBLIC;
GRANT SELECT ON TABLE public.tree_packages TO compose;
GRANT INSERT,DELETE,UPDATE ON TABLE public.tree_packages TO plm;

REVOKE ALL ON TABLE public.tree_product_map FROM PUBLIC;
GRANT SELECT ON TABLE public.tree_product_map TO compose;
GRANT INSERT,DELETE,UPDATE ON TABLE public.tree_product_map TO plm;

REVOKE ALL ON TABLE public.trees FROM PUBLIC;
GRANT SELECT ON TABLE public.trees TO compose;
GRANT INSERT,DELETE,UPDATE ON TABLE public.trees TO plm;

COPY public.trees (id, name, buildname, date, arch, treetype, treeinfo, imported, product, compatlayer) FROM stdin;
51630	Placeholder	aarch64 Placeholder	2017-12-01	aarch64	\N	\N	1	\N	f
5559	Placeholder	i386 Placeholder	2008-08-12	i386	\N	\N	1	\N	f
5899	Placeholder	ia64 Placeholder	2008-10-30	ia64	\N	\N	1	\N	f
5901	Placeholder	ppc Placeholder	2008-10-30	ppc	\N	\N	1	\N	f
17097	Placeholder	ppc64 Placeholder	2011-01-06	ppc64	\N	\N	1	\N	f
46533	Placeholder	ppc64le placeholder	2014-09-10	ppc64le	\N	\N	1	\N	f
9867	Placeholder	s390 Placeholder	2008-10-30	s390	\N	\N	1	\N	f
5900	Placeholder	s390x Placeholder	2017-10-24	s390x	\N	\N	1	\N	f
5558	Placeholder	x86_64 Placeholder	2017-10-24	x86_64	\N	\N	1	\N	f
\.
