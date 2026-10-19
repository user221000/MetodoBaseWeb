-- Frozen model test fixture only; production uses reviewed migrations.

CREATE TABLE usuarios (
	id VARCHAR(36) NOT NULL,
	email VARCHAR(255) NOT NULL,
	password_hash VARCHAR(255) NOT NULL,
	nombre VARCHAR(150) NOT NULL,
	apellido VARCHAR(150) NOT NULL,
	tipo VARCHAR(20) NOT NULL,
	role VARCHAR(20) NOT NULL,
	team_gym_id VARCHAR(36),
	invited_by VARCHAR(36),
	invitation_token VARCHAR(64),
	invitation_expires DATETIME,
	invitation_role VARCHAR(20),
	activo BOOLEAN NOT NULL,
	session_version INTEGER DEFAULT '0' NOT NULL,
	password_reset_hash VARCHAR(64),
	password_reset_expires_at DATETIME,
	password_reset_session_version INTEGER,
	deleted_at DATETIME,
	fecha_registro DATETIME NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT ck_usuario_tipo CHECK (tipo IN ('gym', 'usuario', 'admin')),
	CONSTRAINT uq_usuario_password_reset_hash UNIQUE (password_reset_hash),
	CONSTRAINT ck_usuario_reset_state CHECK ((password_reset_hash IS NULL AND password_reset_expires_at IS NULL AND password_reset_session_version IS NULL) OR (password_reset_hash IS NOT NULL AND length(password_reset_hash) = 64 AND password_reset_expires_at IS NOT NULL AND password_reset_session_version IS NOT NULL AND password_reset_session_version >= 0)),
	FOREIGN KEY(team_gym_id) REFERENCES usuarios (id) ON DELETE CASCADE,
	FOREIGN KEY(invited_by) REFERENCES usuarios (id) ON DELETE SET NULL,
	UNIQUE (invitation_token)
);

CREATE UNIQUE INDEX ix_usuarios_email ON usuarios (email);

CREATE INDEX ix_usuarios_deleted ON usuarios (deleted_at) WHERE deleted_at IS NULL;

CREATE INDEX ix_usuarios_team_gym_id ON usuarios (team_gym_id);

CREATE TABLE stripe_webhook_events (
	event_id VARCHAR(255) NOT NULL,
	event_type VARCHAR(100) NOT NULL,
	processed_at DATETIME NOT NULL,
	result VARCHAR(255),
	PRIMARY KEY (event_id)
);

CREATE INDEX ix_stripe_webhook_events_processed_at ON stripe_webhook_events (processed_at);

CREATE TABLE refresh_tokens (
	jti VARCHAR(36) NOT NULL,
	user_id VARCHAR(36) NOT NULL,
	expires_at FLOAT NOT NULL,
	revoked BOOLEAN NOT NULL,
	created_at FLOAT NOT NULL,
	PRIMARY KEY (jti),
	FOREIGN KEY(user_id) REFERENCES usuarios (id) ON DELETE CASCADE
);

CREATE INDEX ix_refresh_tokens_user_id ON refresh_tokens (user_id);

CREATE TABLE clientes (
	id INTEGER NOT NULL,
	id_cliente VARCHAR(36) NOT NULL,
	gym_id VARCHAR(36) NOT NULL,
	nombre VARCHAR(200) NOT NULL,
	telefono VARCHAR(50),
	email VARCHAR(255),
	edad INTEGER,
	sexo VARCHAR(10),
	peso_kg FLOAT,
	estatura_cm FLOAT,
	grasa_corporal_pct FLOAT,
	masa_magra_kg FLOAT,
	nivel_actividad VARCHAR(30),
	objetivo VARCHAR(30),
	fecha_registro DATETIME,
	ultimo_plan DATETIME,
	total_planes_generados INTEGER,
	activo BOOLEAN,
	deleted_at DATETIME,
	notas TEXT,
	plantilla_tipo VARCHAR(30),
	alimentos_excluidos TEXT,
	fecha_suscripcion DATETIME,
	fecha_fin_suscripcion DATETIME,
	PRIMARY KEY (id),
	CONSTRAINT ck_cliente_sexo CHECK (sexo IN ('M', 'F', 'Otro') OR sexo IS NULL),
	UNIQUE (id_cliente),
	FOREIGN KEY(gym_id) REFERENCES usuarios (id) ON DELETE CASCADE
);

CREATE INDEX ix_clientes_fecha_fin_suscripcion ON clientes (fecha_fin_suscripcion);

CREATE INDEX ix_clientes_gym_activo ON clientes (gym_id, activo);

CREATE INDEX ix_clientes_deleted ON clientes (deleted_at) WHERE deleted_at IS NULL;

CREATE INDEX ix_clientes_gym_nombre ON clientes (gym_id, nombre);

CREATE INDEX ix_clientes_gym_id ON clientes (gym_id);

CREATE TABLE stripe_customers (
	id INTEGER NOT NULL,
	gym_id VARCHAR(36) NOT NULL,
	stripe_customer_id VARCHAR(255) NOT NULL,
	email VARCHAR(255),
	name VARCHAR(255),
	default_payment_method VARCHAR(255),
	currency VARCHAR(3),
	tax_exempt VARCHAR(20),
	created_at DATETIME,
	updated_at DATETIME,
	PRIMARY KEY (id),
	FOREIGN KEY(gym_id) REFERENCES usuarios (id) ON DELETE CASCADE,
	UNIQUE (stripe_customer_id)
);

CREATE UNIQUE INDEX ix_stripe_customers_gym_id ON stripe_customers (gym_id);

CREATE TABLE subscriptions (
	id INTEGER NOT NULL,
	gym_id VARCHAR(36) NOT NULL,
	"plan" VARCHAR(30) NOT NULL,
	stripe_price_id VARCHAR(255),
	status VARCHAR(30) NOT NULL,
	stripe_customer_id VARCHAR(255),
	stripe_subscription_id VARCHAR(255),
	provider VARCHAR(20),
	provider_payment_id VARCHAR(255),
	current_period_start DATETIME,
	current_period_end DATETIME,
	trial_start DATETIME,
	trial_end DATETIME,
	canceled_at DATETIME,
	ended_at DATETIME,
	cancel_at_period_end BOOLEAN,
	max_clientes INTEGER NOT NULL,
	created_at DATETIME,
	updated_at DATETIME,
	PRIMARY KEY (id),
	CONSTRAINT ck_subscription_plan CHECK (plan IN ('free', 'standard', 'gym_comercial', 'clinica', 'pro_usuario')),
	CONSTRAINT ck_subscription_status CHECK (status IN ('active', 'canceled', 'past_due', 'trialing', 'unpaid', 'incomplete', 'incomplete_expired', 'paused')),
	FOREIGN KEY(gym_id) REFERENCES usuarios (id) ON DELETE CASCADE,
	UNIQUE (stripe_subscription_id),
	UNIQUE (provider_payment_id)
);

CREATE UNIQUE INDEX ix_subscriptions_gym_id ON subscriptions (gym_id);

CREATE TABLE invoices (
	id INTEGER NOT NULL,
	gym_id VARCHAR(36) NOT NULL,
	stripe_invoice_id VARCHAR(255) NOT NULL,
	stripe_subscription_id VARCHAR(255),
	amount_due INTEGER NOT NULL,
	amount_paid INTEGER NOT NULL,
	amount_remaining INTEGER NOT NULL,
	subtotal INTEGER,
	tax INTEGER,
	total INTEGER NOT NULL,
	currency VARCHAR(3) NOT NULL,
	status VARCHAR(30) NOT NULL,
	paid BOOLEAN,
	hosted_invoice_url VARCHAR(500),
	invoice_pdf VARCHAR(500),
	period_start DATETIME,
	period_end DATETIME,
	due_date DATETIME,
	paid_at DATETIME,
	created_at DATETIME,
	PRIMARY KEY (id),
	FOREIGN KEY(gym_id) REFERENCES usuarios (id) ON DELETE CASCADE,
	UNIQUE (stripe_invoice_id)
);

CREATE INDEX ix_invoices_gym_id ON invoices (gym_id);

CREATE INDEX ix_invoices_gym_created ON invoices (gym_id, created_at);

CREATE INDEX ix_invoices_stripe_subscription_id ON invoices (stripe_subscription_id);

CREATE TABLE payments (
	id INTEGER NOT NULL,
	gym_id VARCHAR(36) NOT NULL,
	stripe_payment_intent_id VARCHAR(255),
	stripe_invoice_id VARCHAR(255),
	amount_cents INTEGER NOT NULL,
	currency VARCHAR(3) NOT NULL,
	status VARCHAR(30) NOT NULL,
	"plan" VARCHAR(30),
	created_at DATETIME,
	PRIMARY KEY (id),
	FOREIGN KEY(gym_id) REFERENCES usuarios (id) ON DELETE CASCADE,
	UNIQUE (stripe_payment_intent_id)
);

CREATE INDEX ix_payments_gym_id ON payments (gym_id);

CREATE TABLE planes_suscripcion (
	id INTEGER NOT NULL,
	gym_id VARCHAR(36) NOT NULL,
	template_key VARCHAR(40),
	nombre VARCHAR(100) NOT NULL,
	duracion_dias INTEGER NOT NULL,
	precio FLOAT NOT NULL,
	moneda VARCHAR(10) NOT NULL,
	activo BOOLEAN NOT NULL,
	created_at DATETIME,
	updated_at DATETIME,
	PRIMARY KEY (id),
	CONSTRAINT uq_membership_gym_template UNIQUE (gym_id, template_key),
	FOREIGN KEY(gym_id) REFERENCES usuarios (id) ON DELETE CASCADE
);

CREATE INDEX ix_planes_sub_gym ON planes_suscripcion (gym_id, activo);

CREATE INDEX ix_planes_suscripcion_gym_id ON planes_suscripcion (gym_id);

CREATE TABLE audit_log (
	id INTEGER NOT NULL,
	gym_id VARCHAR(36),
	accion VARCHAR(50) NOT NULL,
	entidad VARCHAR(50),
	entidad_id VARCHAR(36),
	detalle TEXT,
	ip VARCHAR(45),
	timestamp DATETIME,
	PRIMARY KEY (id),
	FOREIGN KEY(gym_id) REFERENCES usuarios (id) ON DELETE SET NULL
);

CREATE INDEX ix_audit_log_timestamp ON audit_log (timestamp);

CREATE INDEX ix_audit_log_gym_id ON audit_log (gym_id);

CREATE TABLE gym_branding (
	id VARCHAR(36) NOT NULL,
	gym_id VARCHAR(36) NOT NULL,
	nombre_gym VARCHAR(255) NOT NULL,
	nombre_corto VARCHAR(100) NOT NULL,
	tagline VARCHAR(255) NOT NULL,
	telefono VARCHAR(30) NOT NULL,
	email VARCHAR(255) NOT NULL,
	whatsapp VARCHAR(30) NOT NULL,
	direccion_linea1 VARCHAR(255) NOT NULL,
	direccion_linea2 VARCHAR(255) NOT NULL,
	direccion_linea3 VARCHAR(255) NOT NULL,
	instagram VARCHAR(100) NOT NULL,
	facebook VARCHAR(255) NOT NULL,
	tiktok VARCHAR(100) NOT NULL,
	cuota_mensual FLOAT NOT NULL,
	logo_path VARCHAR(500) NOT NULL,
	color_primario VARCHAR(7) NOT NULL,
	color_secundario VARCHAR(7) NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(gym_id) REFERENCES usuarios (id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX ix_gym_branding_gym_id ON gym_branding (gym_id);

CREATE TABLE checkout_sessions (
	id VARCHAR(64) NOT NULL,
	gym_id VARCHAR(36) NOT NULL,
	stripe_session_id VARCHAR(255),
	"plan" VARCHAR(30) NOT NULL,
	email VARCHAR(120) NOT NULL,
	status VARCHAR(30),
	created_at DATETIME,
	completed_at DATETIME,
	PRIMARY KEY (id),
	FOREIGN KEY(gym_id) REFERENCES usuarios (id),
	UNIQUE (stripe_session_id)
);

CREATE INDEX ix_checkout_sessions_gym_id ON checkout_sessions (gym_id);

CREATE TABLE auth_audit_log (
	id VARCHAR(36) NOT NULL,
	gym_id VARCHAR(36),
	user_id VARCHAR(36),
	event_type VARCHAR(50) NOT NULL,
	ip_address VARCHAR(45),
	user_agent TEXT,
	request_id VARCHAR(36),
	event_metadata JSON,
	created_at DATETIME,
	PRIMARY KEY (id),
	FOREIGN KEY(gym_id) REFERENCES usuarios (id) ON DELETE SET NULL,
	FOREIGN KEY(user_id) REFERENCES usuarios (id) ON DELETE SET NULL
);

CREATE INDEX ix_auth_audit_log_event_type ON auth_audit_log (event_type);

CREATE INDEX ix_auth_audit_log_user_id ON auth_audit_log (user_id);

CREATE INDEX ix_auth_audit_log_created_at ON auth_audit_log (created_at);

CREATE INDEX ix_auth_audit_gym ON auth_audit_log (gym_id, created_at);

CREATE INDEX ix_auth_audit_user ON auth_audit_log (user_id, created_at);

CREATE INDEX ix_auth_audit_type ON auth_audit_log (event_type, created_at);

CREATE INDEX ix_auth_audit_gym_event ON auth_audit_log (gym_id, event_type);

CREATE INDEX ix_auth_audit_log_gym_id ON auth_audit_log (gym_id);

CREATE TABLE gym_settings (
	id INTEGER NOT NULL,
	legacy_id VARCHAR(36),
	gym_id VARCHAR(36) NOT NULL,
	trial_days INTEGER,
	trial_max_clients INTEGER,
	strict_mode BOOLEAN,
	timezone VARCHAR(64),
	locale VARCHAR(10),
	created_at DATETIME,
	updated_at DATETIME,
	PRIMARY KEY (id),
	UNIQUE (legacy_id),
	FOREIGN KEY(gym_id) REFERENCES usuarios (id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX ix_gym_settings_gym_id ON gym_settings (gym_id);

CREATE TABLE gym_licenses (
	id INTEGER NOT NULL,
	legacy_id VARCHAR(36),
	gym_id VARCHAR(36) NOT NULL,
	license_key VARCHAR(255) NOT NULL,
	plan_tier VARCHAR(30) NOT NULL,
	max_clients INTEGER NOT NULL,
	is_active BOOLEAN,
	expires_at DATETIME,
	revoked_at DATETIME,
	payment_provider VARCHAR(30),
	payment_reference VARCHAR(255),
	created_at DATETIME,
	updated_at DATETIME,
	PRIMARY KEY (id),
	UNIQUE (legacy_id),
	FOREIGN KEY(gym_id) REFERENCES usuarios (id) ON DELETE CASCADE,
	UNIQUE (license_key)
);

CREATE INDEX ix_gym_licenses_gym_id ON gym_licenses (gym_id);

CREATE TABLE user_subscriptions (
	id INTEGER NOT NULL,
	user_id VARCHAR(36) NOT NULL,
	"plan" VARCHAR(20) NOT NULL,
	max_planes_mes INTEGER NOT NULL,
	planes_usados_mes INTEGER NOT NULL,
	mes_actual VARCHAR(7) NOT NULL,
	status VARCHAR(20) NOT NULL,
	created_at DATETIME,
	updated_at DATETIME,
	PRIMARY KEY (id),
	CONSTRAINT ck_user_sub_plan CHECK (plan IN ('starter', 'pro')),
	CONSTRAINT ck_user_sub_status CHECK (status IN ('active', 'canceled')),
	FOREIGN KEY(user_id) REFERENCES usuarios (id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX ix_user_subscriptions_user_id ON user_subscriptions (user_id);

CREATE TABLE purchase_intents (
	id VARCHAR(36) NOT NULL,
	subject_id VARCHAR(36) NOT NULL,
	provider VARCHAR(20) NOT NULL,
	operation VARCHAR(30) NOT NULL,
	request_key VARCHAR(128) NOT NULL,
	"plan" VARCHAR(30) NOT NULL,
	amount_cents INTEGER NOT NULL,
	currency VARCHAR(3) NOT NULL,
	status VARCHAR(30) NOT NULL,
	provider_customer_id VARCHAR(255),
	provider_reference_id VARCHAR(255),
	created_at DATETIME NOT NULL,
	updated_at DATETIME NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_purchase_operation_key UNIQUE (subject_id, provider, operation, request_key),
	CONSTRAINT ck_purchase_positive_amount CHECK (amount_cents > 0),
	FOREIGN KEY(subject_id) REFERENCES usuarios (id) ON DELETE CASCADE
);

CREATE INDEX ix_purchase_intents_subject_id ON purchase_intents (subject_id);

CREATE INDEX ix_purchase_intents_provider_reference_id ON purchase_intents (provider_reference_id);

CREATE TABLE provider_subject_associations (
	provider VARCHAR(20) NOT NULL,
	resource_type VARCHAR(30) NOT NULL,
	resource_id VARCHAR(255) NOT NULL,
	subject_id VARCHAR(36) NOT NULL,
	provenance VARCHAR(30) NOT NULL,
	source_ref VARCHAR(255) NOT NULL,
	created_at DATETIME NOT NULL,
	PRIMARY KEY (provider, resource_type, resource_id),
	CONSTRAINT ck_provider_subject_provider CHECK (provider IN ('stripe','mercadopago')),
	CONSTRAINT ck_provider_subject_resource CHECK (resource_type IN ('customer','subscription','payment','preference')),
	CONSTRAINT ck_provider_subject_provenance CHECK (provenance IN ('legacy_subscription','legacy_customer','verified_purchase')),
	FOREIGN KEY(subject_id) REFERENCES usuarios (id) ON DELETE CASCADE
);

CREATE INDEX ix_provider_subject_associations_subject_id ON provider_subject_associations (subject_id);

CREATE TABLE stored_objects (
	id VARCHAR(32) NOT NULL,
	gym_id VARCHAR(36) NOT NULL,
	kind VARCHAR(20) NOT NULL,
	"key" VARCHAR(512) NOT NULL,
	content_type VARCHAR(128) NOT NULL,
	byte_size INTEGER NOT NULL,
	sha256 VARCHAR(64) NOT NULL,
	storage_backend VARCHAR(10) NOT NULL,
	status VARCHAR(10) NOT NULL,
	created_at DATETIME NOT NULL,
	updated_at DATETIME NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_stored_object_owner_id UNIQUE (gym_id, id),
	CONSTRAINT ck_stored_object_id CHECK (length(id) = 32),
	CONSTRAINT ck_stored_object_kind CHECK (kind IN ('plan_pdf', 'gym_logo')),
	CONSTRAINT ck_stored_object_key CHECK (length(key) BETWEEN 1 AND 512),
	CONSTRAINT ck_stored_object_content_type CHECK (length(content_type) BETWEEN 1 AND 128),
	CONSTRAINT ck_stored_object_size CHECK (byte_size BETWEEN 1 AND 67108864),
	CONSTRAINT ck_stored_object_sha256 CHECK (length(sha256) = 64),
	CONSTRAINT ck_stored_object_backend CHECK (storage_backend IN ('local', 's3')),
	CONSTRAINT ck_stored_object_status CHECK (status IN ('pending', 'ready')),
	FOREIGN KEY(gym_id) REFERENCES usuarios (id) ON DELETE RESTRICT,
	UNIQUE ("key")
);

CREATE INDEX ix_stored_objects_gym_id ON stored_objects (gym_id);

CREATE TABLE personal_diary_days (
	id VARCHAR(36) NOT NULL,
	user_id VARCHAR(36) NOT NULL,
	local_date DATE NOT NULL,
	timezone VARCHAR(64) DEFAULT 'America/Mexico_City' NOT NULL,
	water_ml INTEGER DEFAULT '0' NOT NULL,
	version INTEGER DEFAULT '1' NOT NULL,
	meals_json TEXT DEFAULT '{}' NOT NULL,
	created_at DATETIME NOT NULL,
	updated_at DATETIME NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_personal_diary_user_date UNIQUE (user_id, local_date),
	CONSTRAINT ck_personal_diary_timezone CHECK (timezone = 'America/Mexico_City'),
	CONSTRAINT ck_personal_diary_water CHECK (water_ml BETWEEN 0 AND 20000),
	CONSTRAINT ck_personal_diary_version CHECK (version BETWEEN 1 AND 2147483647),
	CONSTRAINT ck_personal_diary_content_size CHECK (length(meals_json) BETWEEN 2 AND 65536),
	FOREIGN KEY(user_id) REFERENCES usuarios (id) ON DELETE RESTRICT
);

CREATE INDEX ix_personal_diary_days_user_id ON personal_diary_days (user_id);

CREATE TABLE planes_generados (
	id INTEGER NOT NULL,
	id_cliente VARCHAR(36) NOT NULL,
	gym_id VARCHAR(36) NOT NULL,
	fecha_generacion DATETIME,
	tmb FLOAT,
	get_total FLOAT,
	kcal_objetivo FLOAT,
	kcal_real FLOAT,
	proteina_g FLOAT,
	carbs_g FLOAT,
	grasa_g FLOAT,
	objetivo VARCHAR(30),
	nivel_actividad VARCHAR(30),
	ruta_pdf VARCHAR(500),
	pdf_object_id VARCHAR(32),
	plan_json TEXT,
	deleted_at DATETIME,
	peso_en_momento FLOAT,
	grasa_en_momento FLOAT,
	desviacion_maxima_pct FLOAT,
	plantilla_tipo VARCHAR(30),
	tipo_plan VARCHAR(30),
	PRIMARY KEY (id),
	CONSTRAINT fk_plan_pdf_object_owner FOREIGN KEY(gym_id, pdf_object_id) REFERENCES stored_objects (gym_id, id) ON DELETE RESTRICT,
	FOREIGN KEY(id_cliente) REFERENCES clientes (id_cliente) ON DELETE CASCADE,
	FOREIGN KEY(gym_id) REFERENCES usuarios (id) ON DELETE CASCADE
);

CREATE INDEX ix_planes_generados_deleted ON planes_generados (deleted_at) WHERE deleted_at IS NULL;

CREATE INDEX ix_planes_gym_fecha ON planes_generados (gym_id, fecha_generacion);

CREATE INDEX ix_planes_generados_gym_id ON planes_generados (gym_id);

CREATE INDEX ix_planes_generados_id_cliente ON planes_generados (id_cliente);

CREATE TABLE gym_profiles (
	id INTEGER NOT NULL,
	gym_id VARCHAR(36) NOT NULL,
	nombre_negocio VARCHAR(255),
	telefono VARCHAR(50),
	direccion TEXT,
	ciudad VARCHAR(150),
	estado VARCHAR(100),
	pais VARCHAR(100),
	logo_url VARCHAR(500),
	logo_object_id VARCHAR(32),
	color_primario VARCHAR(7),
	color_secundario VARCHAR(7),
	sitio_web VARCHAR(500),
	rfc VARCHAR(20),
	razon_social VARCHAR(255),
	regimen_fiscal VARCHAR(10),
	codigo_postal_fiscal VARCHAR(5),
	uso_cfdi VARCHAR(10),
	instagram VARCHAR(255),
	facebook VARCHAR(255),
	tiktok VARCHAR(255),
	created_at DATETIME,
	updated_at DATETIME,
	horarios_comidas JSON,
	PRIMARY KEY (id),
	CONSTRAINT fk_gym_logo_object_owner FOREIGN KEY(gym_id, logo_object_id) REFERENCES stored_objects (gym_id, id) ON DELETE RESTRICT,
	FOREIGN KEY(gym_id) REFERENCES usuarios (id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX ix_gym_profiles_gym_id ON gym_profiles (gym_id);

CREATE TABLE client_progress (
	id INTEGER NOT NULL,
	id_cliente VARCHAR(36) NOT NULL,
	gym_id VARCHAR(36) NOT NULL,
	fecha DATETIME,
	peso_kg FLOAT,
	grasa_corporal_pct FLOAT,
	masa_magra_kg FLOAT,
	notas TEXT,
	PRIMARY KEY (id),
	FOREIGN KEY(id_cliente) REFERENCES clientes (id_cliente) ON DELETE CASCADE,
	FOREIGN KEY(gym_id) REFERENCES usuarios (id) ON DELETE CASCADE
);

CREATE INDEX ix_client_progress_gym_id ON client_progress (gym_id);

CREATE INDEX ix_client_progress_id_cliente ON client_progress (id_cliente);

CREATE INDEX ix_progress_cliente_fecha ON client_progress (id_cliente, fecha);

CREATE TABLE license_activations (
	id INTEGER NOT NULL,
	gym_id VARCHAR(36),
	issued_license_id INTEGER,
	hardware_id VARCHAR(128) NOT NULL,
	clave_hash VARCHAR(64) NOT NULL,
	email VARCHAR(120) NOT NULL,
	"plan" VARCHAR(30) NOT NULL,
	activa BOOLEAN,
	revocada BOOLEAN,
	expira DATETIME,
	created_at DATETIME,
	PRIMARY KEY (id),
	FOREIGN KEY(gym_id) REFERENCES usuarios (id) ON DELETE SET NULL,
	FOREIGN KEY(issued_license_id) REFERENCES gym_licenses (id) ON DELETE SET NULL
);

CREATE INDEX ix_license_activations_gym_id ON license_activations (gym_id);

CREATE INDEX ix_license_activations_email ON license_activations (email);

CREATE UNIQUE INDEX ix_license_activations_hardware_id ON license_activations (hardware_id);

CREATE INDEX ix_license_activations_issued_license_id ON license_activations (issued_license_id);

CREATE TABLE generation_reservations (
	id VARCHAR(36) NOT NULL,
	user_id VARCHAR(36) NOT NULL,
	request_key VARCHAR(128) NOT NULL,
	period VARCHAR(7) NOT NULL,
	status VARCHAR(20) NOT NULL,
	plan_id INTEGER,
	publication_protocol INTEGER DEFAULT '0' NOT NULL,
	persisted_at DATETIME,
	created_at DATETIME NOT NULL,
	updated_at DATETIME NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_generation_request_key UNIQUE (user_id, request_key),
	CONSTRAINT ck_generation_reservation_status CHECK (status IN ('reserved', 'completed', 'released')),
	CONSTRAINT ck_generation_publication_protocol CHECK (publication_protocol IN (0, 1)),
	CONSTRAINT ck_generation_publication_marker CHECK (persisted_at IS NULL OR (publication_protocol = 1 AND status = 'completed')),
	CONSTRAINT ck_generation_completed_publication CHECK (publication_protocol = 0 OR status <> 'completed' OR persisted_at IS NOT NULL),
	FOREIGN KEY(user_id) REFERENCES usuarios (id) ON DELETE CASCADE,
	FOREIGN KEY(plan_id) REFERENCES planes_generados (id) ON DELETE SET NULL
);

CREATE INDEX ix_generation_reservations_user_id ON generation_reservations (user_id);

CREATE TABLE gym_generation_reservations (
	id VARCHAR(36) NOT NULL,
	gym_id VARCHAR(36) NOT NULL,
	client_id VARCHAR(36),
	request_key VARCHAR(128) NOT NULL,
	request_hash VARCHAR(64) NOT NULL,
	period VARCHAR(7) NOT NULL,
	local_date DATE NOT NULL,
	timezone VARCHAR(64) NOT NULL,
	catalog_plan VARCHAR(30) NOT NULL,
	status VARCHAR(20) NOT NULL,
	plan_id INTEGER,
	persisted_at DATETIME,
	result_json TEXT,
	created_at DATETIME NOT NULL,
	updated_at DATETIME NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_gym_generation_request_key UNIQUE (gym_id, request_key),
	CONSTRAINT ck_gym_generation_status CHECK (status IN ('reserved', 'completed', 'released')),
	CONSTRAINT ck_gym_generation_request_hash CHECK (length(request_hash) = 64),
	CONSTRAINT ck_gym_generation_no_persisted_refund CHECK (status <> 'released' OR persisted_at IS NULL),
	CONSTRAINT ck_gym_generation_completed_result CHECK (status <> 'completed' OR result_json IS NOT NULL),
	FOREIGN KEY(gym_id) REFERENCES usuarios (id) ON DELETE CASCADE,
	FOREIGN KEY(client_id) REFERENCES clientes (id_cliente) ON DELETE SET NULL,
	UNIQUE (plan_id),
	FOREIGN KEY(plan_id) REFERENCES planes_generados (id) ON DELETE SET NULL
);

CREATE INDEX ix_gym_generation_reservations_client_id ON gym_generation_reservations (client_id);

CREATE INDEX ix_gym_generation_period_status ON gym_generation_reservations (gym_id, period, status);

CREATE INDEX ix_gym_generation_day_client ON gym_generation_reservations (gym_id, local_date, client_id, status);

CREATE INDEX ix_gym_generation_reservations_gym_id ON gym_generation_reservations (gym_id);
