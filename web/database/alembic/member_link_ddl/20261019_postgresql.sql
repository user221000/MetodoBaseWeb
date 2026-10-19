-- R12 statement
CREATE TABLE client_account_links (
	id VARCHAR(36) NOT NULL, 
	gym_id VARCHAR(36) NOT NULL, 
	client_id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36), 
	status VARCHAR(10) NOT NULL, 
	version INTEGER DEFAULT '1' NOT NULL, 
	gym_name VARCHAR(255) NOT NULL, 
	client_display_name VARCHAR(200) NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	accepted_at TIMESTAMP WITHOUT TIME ZONE, 
	revoked_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	CONSTRAINT fk_client_link_owner FOREIGN KEY(gym_id, client_id) REFERENCES clientes (gym_id, id_cliente) ON DELETE RESTRICT, 
	CONSTRAINT uq_client_link_resource UNIQUE (gym_id, client_id, id), 
	CONSTRAINT uq_client_link_acceptance UNIQUE (id, gym_id, client_id, user_id), 
	CONSTRAINT ck_client_link_id CHECK (length(id) = 36), 
	CONSTRAINT ck_client_link_status CHECK (status IN ('pending','active','revoked')), 
	CONSTRAINT ck_client_link_version CHECK (version BETWEEN 1 AND 2147483647), 
	CONSTRAINT ck_client_link_labels CHECK (length(gym_name) BETWEEN 1 AND 255 AND length(client_display_name) BETWEEN 1 AND 200), 
	CONSTRAINT ck_client_link_state CHECK ((status='pending' AND user_id IS NULL AND accepted_at IS NULL AND revoked_at IS NULL) OR (status='active' AND user_id IS NOT NULL AND accepted_at IS NOT NULL AND revoked_at IS NULL) OR (status='revoked' AND revoked_at IS NOT NULL AND ((user_id IS NULL AND accepted_at IS NULL) OR (user_id IS NOT NULL AND accepted_at IS NOT NULL)))), 
	FOREIGN KEY(gym_id) REFERENCES usuarios (id) ON DELETE RESTRICT, 
	FOREIGN KEY(user_id) REFERENCES usuarios (id) ON DELETE RESTRICT
);
-- R12 statement
CREATE INDEX ix_client_account_links_gym_id ON client_account_links (gym_id);
-- R12 statement
CREATE INDEX ix_client_account_links_user_id ON client_account_links (user_id);
-- R12 statement
CREATE UNIQUE INDEX uq_client_link_current ON client_account_links (gym_id, client_id) WHERE status::text IN ('pending'::text,'active'::text);
-- R12 statement
CREATE UNIQUE INDEX uq_client_link_recipient ON client_account_links (gym_id, user_id) WHERE status='active';
-- R12 statement
CREATE TABLE client_link_invitations (
	id VARCHAR(36) NOT NULL, 
	link_id VARCHAR(36) NOT NULL, 
	gym_id VARCHAR(36) NOT NULL, 
	client_id VARCHAR(36) NOT NULL, 
	recipient_email VARCHAR(255) NOT NULL, 
	token_hash VARCHAR(64) NOT NULL, 
	expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	status VARCHAR(10) NOT NULL, 
	issued_by VARCHAR(36) NOT NULL, 
	consumed_by VARCHAR(36), 
	consumed_at TIMESTAMP WITHOUT TIME ZONE, 
	revoked_at TIMESTAMP WITHOUT TIME ZONE, 
	version INTEGER DEFAULT '1' NOT NULL, 
	request_key VARCHAR(128) NOT NULL, 
	payload_hash VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT fk_client_invitation_link FOREIGN KEY(gym_id, client_id, link_id) REFERENCES client_account_links (gym_id, client_id, id) ON DELETE RESTRICT, 
	CONSTRAINT fk_client_invitation_consumption FOREIGN KEY(link_id, gym_id, client_id, consumed_by) REFERENCES client_account_links (id, gym_id, client_id, user_id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED, 
	CONSTRAINT uq_client_invitation_request UNIQUE (gym_id, request_key), 
	CONSTRAINT ck_client_invitation_id CHECK (length(id) = 36), 
	CONSTRAINT ck_client_invitation_hashes CHECK (length(token_hash) = 64 AND length(payload_hash) = 64), 
	CONSTRAINT ck_client_invitation_request CHECK (length(request_key) BETWEEN 1 AND 128), 
	CONSTRAINT ck_client_invitation_email CHECK (length(recipient_email) BETWEEN 3 AND 255 AND recipient_email=lower(trim(recipient_email))), 
	CONSTRAINT ck_client_invitation_status CHECK (status IN ('pending','consumed','revoked')), 
	CONSTRAINT ck_client_invitation_version CHECK (version BETWEEN 1 AND 2147483647), 
	CONSTRAINT ck_client_invitation_state CHECK ((status='consumed' AND consumed_by IS NOT NULL AND consumed_at IS NOT NULL AND consumed_at<expires_at AND revoked_at IS NULL) OR (status='pending' AND consumed_by IS NULL AND consumed_at IS NULL AND revoked_at IS NULL) OR (status='revoked' AND consumed_by IS NULL AND consumed_at IS NULL AND revoked_at IS NOT NULL)), 
	UNIQUE (link_id), 
	UNIQUE (token_hash), 
	FOREIGN KEY(issued_by) REFERENCES usuarios (id) ON DELETE RESTRICT, 
	FOREIGN KEY(consumed_by) REFERENCES usuarios (id) ON DELETE RESTRICT
);
-- R12 statement
CREATE INDEX ix_client_link_invitations_gym_id ON client_link_invitations (gym_id);
-- R12 statement
CREATE TABLE client_plan_publications (
	id VARCHAR(36) NOT NULL, 
	gym_id VARCHAR(36) NOT NULL, 
	client_id VARCHAR(36) NOT NULL, 
	link_id VARCHAR(36) NOT NULL, 
	source_plan_id INTEGER NOT NULL, 
	schema_version INTEGER DEFAULT '1' NOT NULL, 
	publication_version INTEGER DEFAULT '1' NOT NULL, 
	status VARCHAR(10) NOT NULL, 
	published_by VARCHAR(36) NOT NULL, 
	published_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	withdrawn_at TIMESTAMP WITHOUT TIME ZONE, 
	plan_json TEXT NOT NULL, 
	plan_sha256 VARCHAR(64) NOT NULL, 
	source_object_id VARCHAR(32), 
	object_key VARCHAR(512), 
	content_type VARCHAR(128), 
	byte_size INTEGER, 
	sha256 VARCHAR(64), 
	storage_backend VARCHAR(10), 
	PRIMARY KEY (id), 
	CONSTRAINT fk_client_publication_link FOREIGN KEY(gym_id, client_id, link_id) REFERENCES client_account_links (gym_id, client_id, id) ON DELETE RESTRICT, 
	CONSTRAINT fk_client_publication_source FOREIGN KEY(gym_id, client_id, source_plan_id) REFERENCES planes_generados (gym_id, id_cliente, id) ON DELETE RESTRICT, 
	CONSTRAINT fk_client_publication_object FOREIGN KEY(gym_id, source_object_id) REFERENCES stored_objects (gym_id, id) ON DELETE RESTRICT, 
	CONSTRAINT ck_client_publication_id CHECK (length(id) = 36), 
	CONSTRAINT ck_client_publication_schema CHECK (schema_version = 1), 
	CONSTRAINT ck_client_publication_version CHECK (publication_version BETWEEN 1 AND 2147483647), 
	CONSTRAINT ck_client_publication_status CHECK (status IN ('published','withdrawn')), 
	CONSTRAINT ck_client_publication_state CHECK ((status='published' AND withdrawn_at IS NULL) OR (status='withdrawn' AND withdrawn_at IS NOT NULL)), 
	CONSTRAINT ck_client_publication_content CHECK (length(plan_json) BETWEEN 2 AND 262144 AND length(plan_sha256) = 64), 
	CONSTRAINT ck_client_publication_pdf CHECK ((source_object_id IS NULL AND object_key IS NULL AND content_type IS NULL AND byte_size IS NULL AND sha256 IS NULL AND storage_backend IS NULL) OR (source_object_id IS NOT NULL AND length(source_object_id)=32 AND object_key IS NOT NULL AND length(object_key) BETWEEN 1 AND 512 AND content_type IS NOT NULL AND content_type='application/pdf' AND byte_size IS NOT NULL AND byte_size BETWEEN 1 AND 67108864 AND sha256 IS NOT NULL AND length(sha256)=64 AND storage_backend IS NOT NULL AND storage_backend::text IN ('local'::text,'s3'::text))), 
	FOREIGN KEY(published_by) REFERENCES usuarios (id) ON DELETE RESTRICT
);
-- R12 statement
CREATE INDEX ix_client_plan_publications_gym_id ON client_plan_publications (gym_id);
-- R12 statement
CREATE INDEX ix_client_plan_publications_link_id ON client_plan_publications (link_id);
-- R12 statement
CREATE UNIQUE INDEX uq_client_publication_current ON client_plan_publications (link_id) WHERE status='published';
