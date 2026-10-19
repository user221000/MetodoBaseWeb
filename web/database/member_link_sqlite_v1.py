"""SQLite association/immutability compatibility, not PostgreSQL RLS authority.

SQLite production remains prohibited. Auth/proof and full projection validation
belong to the shared service; these triggers additionally preserve associations.
"""


def sqlite_statements():
    return [
        """CREATE TRIGGER r12_link_insert BEFORE INSERT ON client_account_links
        BEGIN
          SELECT RAISE(ABORT,'R12 link denied') WHERE NEW.status<>'pending' OR NEW.user_id IS NOT NULL OR NEW.version<>1;
          SELECT RAISE(ABORT,'R12 client unavailable') WHERE NOT EXISTS(SELECT 1 FROM clientes c WHERE c.gym_id=NEW.gym_id AND c.id_cliente=NEW.client_id AND c.activo=1 AND c.deleted_at IS NULL);
        END""",
        """CREATE TRIGGER r12_link_update BEFORE UPDATE ON client_account_links
        BEGIN
          SELECT RAISE(ABORT,'R12 immutable link') WHERE NEW.id IS NOT OLD.id OR NEW.gym_id IS NOT OLD.gym_id OR NEW.client_id IS NOT OLD.client_id OR NEW.gym_name IS NOT OLD.gym_name OR NEW.client_display_name IS NOT OLD.client_display_name OR NEW.created_at IS NOT OLD.created_at OR NEW.version<>OLD.version+1;
          SELECT RAISE(ABORT,'R12 link transition denied') WHERE NOT ((OLD.status='pending' AND NEW.status='active') OR (OLD.status IN ('pending','active') AND NEW.status='revoked'));
          SELECT RAISE(ABORT,'R12 immutable recipient') WHERE NEW.status='revoked' AND (NEW.user_id IS NOT OLD.user_id OR NEW.accepted_at IS NOT OLD.accepted_at);
          SELECT RAISE(ABORT,'R12 consumption witness required') WHERE NEW.status='active' AND NOT EXISTS(SELECT 1 FROM client_link_invitations i WHERE i.link_id=NEW.id AND i.gym_id=NEW.gym_id AND i.client_id=NEW.client_id AND i.status='consumed' AND i.consumed_by=NEW.user_id AND i.consumed_at=NEW.accepted_at);
        END""",
        """CREATE TRIGGER r12_invitation_update BEFORE UPDATE ON client_link_invitations
        BEGIN
          SELECT RAISE(ABORT,'R12 immutable invitation') WHERE OLD.status<>'pending' OR NEW.version<>OLD.version+1 OR NEW.id IS NOT OLD.id OR NEW.link_id IS NOT OLD.link_id OR NEW.gym_id IS NOT OLD.gym_id OR NEW.client_id IS NOT OLD.client_id OR NEW.recipient_email IS NOT OLD.recipient_email OR NEW.issued_by IS NOT OLD.issued_by OR NEW.request_key IS NOT OLD.request_key OR NEW.payload_hash IS NOT OLD.payload_hash OR NEW.created_at IS NOT OLD.created_at;
          SELECT RAISE(ABORT,'R12 immutable consumption') WHERE NEW.status IN ('consumed','revoked') AND (NEW.token_hash IS NOT OLD.token_hash OR NEW.expires_at IS NOT OLD.expires_at);
        END""",
        """CREATE TRIGGER r12_link_delete BEFORE DELETE ON client_account_links BEGIN SELECT RAISE(ABORT,'R12 link removal requires reviewed workflow'); END""",
        """CREATE TRIGGER r12_invitation_delete BEFORE DELETE ON client_link_invitations BEGIN SELECT RAISE(ABORT,'R12 invitation removal requires reviewed workflow'); END""",
        """CREATE TRIGGER r12_publication_insert BEFORE INSERT ON client_plan_publications
        BEGIN
          SELECT RAISE(ABORT,'R12 publication unavailable') WHERE NEW.status<>'published' OR NEW.publication_version<>1 OR NEW.schema_version<>1 OR NOT EXISTS(SELECT 1 FROM clientes c JOIN client_account_links l ON l.gym_id=c.gym_id AND l.client_id=c.id_cliente WHERE c.gym_id=NEW.gym_id AND c.id_cliente=NEW.client_id AND c.activo=1 AND c.deleted_at IS NULL AND l.id=NEW.link_id AND l.status IN ('pending','active'));
          SELECT RAISE(ABORT,'R12 publication source unavailable') WHERE NOT EXISTS(SELECT 1 FROM planes_generados p WHERE p.id=NEW.source_plan_id AND p.gym_id=NEW.gym_id AND p.id_cliente=NEW.client_id AND p.deleted_at IS NULL AND p.pdf_object_id IS NEW.source_object_id);
          SELECT RAISE(ABORT,'R12 publication object unavailable') WHERE NEW.source_object_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM stored_objects o WHERE o.id=NEW.source_object_id AND o.gym_id=NEW.gym_id AND o.status='ready' AND o.kind='plan_pdf' AND o.key=NEW.object_key AND o.content_type=NEW.content_type AND o.byte_size=NEW.byte_size AND o.sha256=NEW.sha256 AND o.storage_backend=NEW.storage_backend);
          SELECT RAISE(ABORT,'R12 projection content unavailable') WHERE NOT json_valid(NEW.plan_json);
          SELECT RAISE(ABORT,'R12 projection source mismatch') WHERE EXISTS(SELECT '$'||substr(fullkey,7),type,atom FROM json_tree(NEW.plan_json,'$.plan') EXCEPT SELECT fullkey,type,atom FROM json_tree((SELECT plan_json FROM planes_generados WHERE id=NEW.source_plan_id))) OR EXISTS(SELECT fullkey,type,atom FROM json_tree((SELECT plan_json FROM planes_generados WHERE id=NEW.source_plan_id)) EXCEPT SELECT '$'||substr(fullkey,7),type,atom FROM json_tree(NEW.plan_json,'$.plan'));
        END""",
        """CREATE TRIGGER r12_publication_update BEFORE UPDATE ON client_plan_publications
        BEGIN
          SELECT RAISE(ABORT,'R12 immutable publication') WHERE OLD.status<>'published' OR NEW.status<>'withdrawn' OR NEW.publication_version<>OLD.publication_version+1 OR NEW.id IS NOT OLD.id OR NEW.gym_id IS NOT OLD.gym_id OR NEW.client_id IS NOT OLD.client_id OR NEW.link_id IS NOT OLD.link_id OR NEW.source_plan_id IS NOT OLD.source_plan_id OR NEW.schema_version IS NOT OLD.schema_version OR NEW.published_by IS NOT OLD.published_by OR NEW.published_at IS NOT OLD.published_at OR NEW.plan_json IS NOT OLD.plan_json OR NEW.plan_sha256 IS NOT OLD.plan_sha256 OR NEW.source_object_id IS NOT OLD.source_object_id OR NEW.object_key IS NOT OLD.object_key OR NEW.content_type IS NOT OLD.content_type OR NEW.byte_size IS NOT OLD.byte_size OR NEW.sha256 IS NOT OLD.sha256 OR NEW.storage_backend IS NOT OLD.storage_backend;
        END""",
        """CREATE TRIGGER r12_publication_delete BEFORE DELETE ON client_plan_publications BEGIN SELECT RAISE(ABORT,'R12 publication removal requires reviewed workflow'); END""",
        """CREATE TRIGGER r12_client_invalidation AFTER UPDATE ON clientes
        WHEN (NEW.activo=0 AND NEW.activo IS NOT OLD.activo) OR (NEW.deleted_at IS NOT NULL AND NEW.deleted_at IS NOT OLD.deleted_at)
        BEGIN
          UPDATE client_account_links SET status='revoked',version=version+1,revoked_at=strftime('%Y-%m-%d %H:%M:%f','now'),updated_at=strftime('%Y-%m-%d %H:%M:%f','now') WHERE gym_id=OLD.gym_id AND client_id=OLD.id_cliente AND status IN ('pending','active');
          UPDATE client_link_invitations SET status='revoked',version=version+1,revoked_at=strftime('%Y-%m-%d %H:%M:%f','now'),updated_at=strftime('%Y-%m-%d %H:%M:%f','now') WHERE gym_id=OLD.gym_id AND client_id=OLD.id_cliente AND status='pending';
          UPDATE client_plan_publications SET status='withdrawn',publication_version=publication_version+1,withdrawn_at=strftime('%Y-%m-%d %H:%M:%f','now') WHERE gym_id=OLD.gym_id AND client_id=OLD.id_cliente AND status='published';
        END""",
        """CREATE TRIGGER r12_plan_invalidation AFTER UPDATE ON planes_generados
        WHEN NEW.id IS NOT OLD.id OR NEW.gym_id IS NOT OLD.gym_id OR NEW.id_cliente IS NOT OLD.id_cliente OR NEW.fecha_generacion IS NOT OLD.fecha_generacion OR NEW.tmb IS NOT OLD.tmb OR NEW.get_total IS NOT OLD.get_total OR NEW.kcal_objetivo IS NOT OLD.kcal_objetivo OR NEW.kcal_real IS NOT OLD.kcal_real OR NEW.proteina_g IS NOT OLD.proteina_g OR NEW.carbs_g IS NOT OLD.carbs_g OR NEW.grasa_g IS NOT OLD.grasa_g OR NEW.objetivo IS NOT OLD.objetivo OR NEW.nivel_actividad IS NOT OLD.nivel_actividad OR NEW.ruta_pdf IS NOT OLD.ruta_pdf OR NEW.pdf_object_id IS NOT OLD.pdf_object_id OR NEW.plan_json IS NOT OLD.plan_json OR NEW.deleted_at IS NOT OLD.deleted_at OR NEW.peso_en_momento IS NOT OLD.peso_en_momento OR NEW.grasa_en_momento IS NOT OLD.grasa_en_momento OR NEW.desviacion_maxima_pct IS NOT OLD.desviacion_maxima_pct OR NEW.plantilla_tipo IS NOT OLD.plantilla_tipo OR NEW.tipo_plan IS NOT OLD.tipo_plan
        BEGIN UPDATE client_plan_publications SET status='withdrawn',publication_version=publication_version+1,withdrawn_at=strftime('%Y-%m-%d %H:%M:%f','now') WHERE gym_id=OLD.gym_id AND source_plan_id=OLD.id AND status='published'; END""",
        """CREATE TRIGGER r12_object_invalidation AFTER UPDATE ON stored_objects
        WHEN NEW.id IS NOT OLD.id OR NEW.gym_id IS NOT OLD.gym_id OR NEW.kind IS NOT OLD.kind OR NEW.key IS NOT OLD.key OR NEW.content_type IS NOT OLD.content_type OR NEW.byte_size IS NOT OLD.byte_size OR NEW.sha256 IS NOT OLD.sha256 OR NEW.storage_backend IS NOT OLD.storage_backend OR NEW.status IS NOT OLD.status
        BEGIN UPDATE client_plan_publications SET status='withdrawn',publication_version=publication_version+1,withdrawn_at=strftime('%Y-%m-%d %H:%M:%f','now') WHERE gym_id=OLD.gym_id AND source_object_id=OLD.id AND status='published'; END""",
    ]
