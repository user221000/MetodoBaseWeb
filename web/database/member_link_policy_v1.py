"""Revision29 custom RLS/guards, independent of the twenty historical policies.

Invoker functions have fixed names/search_path; importing never executes DDL.
Source-bound projection helpers precede these policies during installation.
"""

MEMBER_LINK_TABLES = frozenset({'client_account_links', 'client_link_invitations', 'client_plan_publications'})


def member_link_sql():
    return r"""
CREATE FUNCTION public.r12_actor_valid() RETURNS boolean LANGUAGE sql STABLE SECURITY INVOKER
 SET search_path=pg_catalog AS $$
 SELECT EXISTS(SELECT 1 FROM public.usuarios u WHERE u.id=NULLIF(current_setting('app.current_tenant',true),'')
   AND u.activo AND u.deleted_at IS NULL AND u.invitation_token IS NULL
   AND ((u.tipo='gym' AND u.role='OWNER' AND u.team_gym_id IS NULL)
     OR (u.role IN ('ADMIN','NUTRIOLOGO','VIEWER') AND (u.tipo='usuario' OR u.team_gym_id IS NOT NULL)
       AND (u.team_gym_id IS NULL OR EXISTS(SELECT 1 FROM public.usuarios parent WHERE parent.id=u.team_gym_id
         AND parent.tipo='gym' AND parent.role='OWNER' AND parent.team_gym_id IS NULL
         AND parent.activo AND parent.deleted_at IS NULL AND parent.invitation_token IS NULL)))))
 $$;
CREATE FUNCTION public.r12_gym_scope(identity text) RETURNS boolean LANGUAGE sql STABLE SECURITY INVOKER
 SET search_path=pg_catalog AS $$
 SELECT COALESCE(identity=NULLIF(current_setting('app.current_tenant',true),''),false)
 $$;
CREATE FUNCTION public.r12_canonical_gym(identity text) RETURNS boolean LANGUAGE sql STABLE SECURITY INVOKER
 SET search_path=pg_catalog AS $$
 SELECT EXISTS(SELECT 1 FROM public.usuarios u
  WHERE u.id=identity AND u.tipo='gym' AND u.role='OWNER' AND u.team_gym_id IS NULL
    AND u.activo AND u.deleted_at IS NULL AND u.invitation_token IS NULL)
 $$;
CREATE FUNCTION public.r12_lock_canonical_gym(identity text) RETURNS boolean LANGUAGE plpgsql VOLATILE SECURITY INVOKER
 SET search_path=pg_catalog AS $$
 BEGIN
  PERFORM 1 FROM public.usuarios u WHERE u.id=identity AND u.tipo='gym' AND u.role='OWNER'
    AND u.team_gym_id IS NULL AND u.activo AND u.deleted_at IS NULL AND u.invitation_token IS NULL FOR SHARE NOWAIT;
  RETURN FOUND;
 END $$;
CREATE FUNCTION public.r12_proof(i public.client_link_invitations) RETURNS boolean LANGUAGE sql STABLE SECURITY INVOKER
 SET search_path=pg_catalog AS $$
 SELECT COALESCE(public.r12_actor_valid() AND i.token_hash=NULLIF(current_setting('app.client_invitation_digest',true),'')
 AND EXISTS(SELECT 1 FROM public.usuarios u WHERE u.id=NULLIF(current_setting('app.current_tenant',true),'')
   AND u.email=i.recipient_email AND u.email=lower(btrim(u.email)))
 AND (i.status<>'consumed' OR i.consumed_by=NULLIF(current_setting('app.current_tenant',true),'')),false)
 $$;
CREATE FUNCTION public.r12_pending_proof(l public.client_account_links) RETURNS boolean LANGUAGE sql STABLE SECURITY INVOKER
 SET search_path=pg_catalog AS $$
 SELECT COALESCE(l.status='pending' AND EXISTS(SELECT 1 FROM public.client_link_invitations i WHERE i.link_id=l.id
  AND i.gym_id=l.gym_id AND i.client_id=l.client_id AND i.status IN ('pending','consumed') AND public.r12_proof(i)),false)
 $$;
CREATE FUNCTION public.r12_consumed_proof(l public.client_account_links) RETURNS boolean LANGUAGE sql STABLE SECURITY INVOKER
 SET search_path=pg_catalog AS $$
 SELECT COALESCE(l.user_id=NULLIF(current_setting('app.current_tenant',true),'') AND EXISTS(
 SELECT 1 FROM public.client_link_invitations i WHERE i.link_id=l.id AND i.gym_id=l.gym_id AND i.client_id=l.client_id
 AND i.status='consumed' AND i.consumed_by=l.user_id AND i.consumed_at=l.accepted_at AND public.r12_proof(i)),false)
 $$;
CREATE FUNCTION public.r12_recipient(p public.client_plan_publications) RETURNS boolean LANGUAGE sql STABLE SECURITY INVOKER
 SET search_path=pg_catalog AS $$
 SELECT COALESCE(p.status='published' AND public.r12_actor_valid() AND EXISTS(
 SELECT 1 FROM public.client_account_links l WHERE l.id=p.link_id AND l.gym_id=p.gym_id AND l.client_id=p.client_id
  AND l.user_id=NULLIF(current_setting('app.current_tenant',true),'') AND l.status='active'
  AND public.r12_canonical_gym(l.gym_id)),false)
 $$;
ALTER TABLE public.client_account_links ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.client_account_links FORCE ROW LEVEL SECURITY;
ALTER TABLE public.client_link_invitations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.client_link_invitations FORCE ROW LEVEL SECURITY;
ALTER TABLE public.client_plan_publications ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.client_plan_publications FORCE ROW LEVEL SECURITY;
CREATE POLICY r12_link_select ON public.client_account_links FOR SELECT USING(public.r12_gym_scope(gym_id)
 OR (user_id=NULLIF(current_setting('app.current_tenant',true),'') AND public.r12_actor_valid()) OR public.r12_pending_proof(client_account_links));
CREATE POLICY r12_link_insert ON public.client_account_links FOR INSERT WITH CHECK(public.r12_gym_scope(gym_id) AND status='pending' AND user_id IS NULL);
CREATE POLICY r12_link_update ON public.client_account_links FOR UPDATE USING(public.r12_gym_scope(gym_id)
 OR (user_id=NULLIF(current_setting('app.current_tenant',true),'') AND public.r12_actor_valid()) OR public.r12_pending_proof(client_account_links))
 WITH CHECK((public.r12_gym_scope(gym_id) AND status IN ('pending','revoked'))
 OR (status='active' AND public.r12_consumed_proof(client_account_links))
 OR (status='revoked' AND user_id=NULLIF(current_setting('app.current_tenant',true),'') AND public.r12_actor_valid()));
CREATE POLICY r12_invitation_select ON public.client_link_invitations FOR SELECT USING(public.r12_gym_scope(gym_id) OR public.r12_proof(client_link_invitations));
CREATE POLICY r12_invitation_insert ON public.client_link_invitations FOR INSERT WITH CHECK(public.r12_gym_scope(gym_id) AND status='pending' AND consumed_by IS NULL AND consumed_at IS NULL);
CREATE POLICY r12_invitation_update ON public.client_link_invitations FOR UPDATE USING(public.r12_gym_scope(gym_id) OR public.r12_proof(client_link_invitations))
 WITH CHECK((public.r12_gym_scope(gym_id) AND status IN ('pending','revoked') AND consumed_by IS NULL AND consumed_at IS NULL)
 OR (public.r12_proof(client_link_invitations) AND status='consumed' AND consumed_by=NULLIF(current_setting('app.current_tenant',true),'') AND consumed_at<expires_at));
CREATE POLICY r12_publication_select ON public.client_plan_publications FOR SELECT USING(public.r12_gym_scope(gym_id) OR public.r12_recipient(client_plan_publications));
CREATE POLICY r12_publication_insert ON public.client_plan_publications FOR INSERT WITH CHECK(public.r12_gym_scope(gym_id));
CREATE POLICY r12_publication_gym_update ON public.client_plan_publications FOR UPDATE USING(public.r12_gym_scope(gym_id)) WITH CHECK(public.r12_gym_scope(gym_id));
CREATE POLICY r12_publication_reader_lock ON public.client_plan_publications FOR UPDATE USING(public.r12_recipient(client_plan_publications)) WITH CHECK(false);

CREATE FUNCTION public.r12_require_rc() RETURNS void LANGUAGE plpgsql VOLATILE SECURITY INVOKER SET search_path=pg_catalog AS $$
 BEGIN IF current_setting('transaction_isolation') IS DISTINCT FROM 'read committed' THEN RAISE EXCEPTION USING ERRCODE='25000',MESSAGE='R12 requires READ COMMITTED'; END IF; END $$;
CREATE FUNCTION public.r12_guard_link() RETURNS trigger LANGUAGE plpgsql VOLATILE SECURITY INVOKER SET search_path=pg_catalog AS $$
 BEGIN
  PERFORM public.r12_require_rc();
  IF TG_OP='INSERT' THEN
   IF NEW.status<>'pending' OR NEW.user_id IS NOT NULL OR NEW.version<>1 OR public.r12_gym_scope(NEW.gym_id) IS NOT TRUE OR public.r12_lock_canonical_gym(NEW.gym_id) IS NOT TRUE THEN RAISE EXCEPTION USING ERRCODE='42501',MESSAGE='R12 link denied'; END IF;
   PERFORM 1 FROM public.clientes WHERE gym_id=NEW.gym_id AND id_cliente=NEW.client_id AND activo AND deleted_at IS NULL FOR SHARE;
   IF NOT FOUND THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='R12 client unavailable'; END IF;
   NEW.created_at=clock_timestamp() AT TIME ZONE 'UTC';
   NEW.updated_at=NEW.created_at;
   NEW.accepted_at=NULL;
   NEW.revoked_at=NULL;
  ELSE
   IF (NEW.id,NEW.gym_id,NEW.client_id,NEW.gym_name,NEW.client_display_name,NEW.created_at) IS DISTINCT FROM (OLD.id,OLD.gym_id,OLD.client_id,OLD.gym_name,OLD.client_display_name,OLD.created_at) THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='R12 immutable link'; END IF;
   IF OLD.status='pending' AND NEW.status='active' THEN
    IF public.r12_consumed_proof(NEW) IS NOT TRUE OR public.r12_lock_canonical_gym(NEW.gym_id) IS NOT TRUE THEN RAISE EXCEPTION USING ERRCODE='42501',MESSAGE='R12 consumption proof required'; END IF;
   ELSIF OLD.status IN ('pending','active') AND NEW.status='revoked' THEN
    IF (NEW.user_id,NEW.accepted_at) IS DISTINCT FROM (OLD.user_id,OLD.accepted_at) THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='R12 immutable recipient'; END IF;
    NEW.revoked_at=clock_timestamp() AT TIME ZONE 'UTC';
   ELSE RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='R12 link transition denied'; END IF;
   IF NEW.version<>OLD.version+1 THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='R12 version denied'; END IF;
   NEW.updated_at=clock_timestamp() AT TIME ZONE 'UTC';
  END IF;
  RETURN NEW;
 END $$;
CREATE TRIGGER r12_guard_link BEFORE INSERT OR UPDATE ON public.client_account_links FOR EACH ROW EXECUTE FUNCTION public.r12_guard_link();
CREATE FUNCTION public.r12_guard_invitation() RETURNS trigger LANGUAGE plpgsql VOLATILE SECURITY INVOKER SET search_path=pg_catalog AS $$
 DECLARE decision timestamp;
 BEGIN
  PERFORM public.r12_require_rc();
  IF TG_OP='INSERT' THEN
   IF NEW.status<>'pending' OR NEW.consumed_by IS NOT NULL OR NEW.version<>1 OR public.r12_lock_canonical_gym(NEW.gym_id) IS NOT TRUE THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='R12 invitation denied'; END IF;
   NEW.created_at=clock_timestamp() AT TIME ZONE 'UTC';
   NEW.updated_at=NEW.created_at;
   NEW.consumed_at=NULL;
   NEW.revoked_at=NULL;
   IF NEW.token_hash!~'^[a-f0-9]{64}$' OR NEW.payload_hash!~'^[a-f0-9]{64}$' THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='R12 invitation digest denied'; END IF;
   RETURN NEW;
  END IF;
  IF (NEW.id,NEW.link_id,NEW.gym_id,NEW.client_id,NEW.recipient_email,NEW.issued_by,NEW.request_key,NEW.payload_hash,NEW.created_at) IS DISTINCT FROM (OLD.id,OLD.link_id,OLD.gym_id,OLD.client_id,OLD.recipient_email,OLD.issued_by,OLD.request_key,OLD.payload_hash,OLD.created_at)
   OR NEW.version<>OLD.version+1 OR OLD.status<>'pending' THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='R12 immutable invitation'; END IF;
  IF NEW.status='consumed' THEN
   decision=clock_timestamp() AT TIME ZONE 'UTC';
   IF public.r12_proof(OLD) IS NOT TRUE OR public.r12_lock_canonical_gym(NEW.gym_id) IS NOT TRUE OR NEW.consumed_by IS DISTINCT FROM NULLIF(current_setting('app.current_tenant',true),'')
    OR NEW.token_hash IS DISTINCT FROM OLD.token_hash OR NEW.expires_at IS DISTINCT FROM OLD.expires_at OR decision>=OLD.expires_at
    THEN RAISE EXCEPTION USING ERRCODE='42501',MESSAGE='R12 consumption denied'; END IF;
   NEW.consumed_at=decision;
  ELSIF public.r12_gym_scope(NEW.gym_id) IS NOT TRUE OR NEW.status NOT IN ('pending','revoked')
   OR (NEW.status='pending' AND public.r12_lock_canonical_gym(NEW.gym_id) IS NOT TRUE) THEN RAISE EXCEPTION USING ERRCODE='42501',MESSAGE='R12 invitation transition denied'; END IF;
  IF NEW.status='revoked' THEN
   IF (NEW.token_hash,NEW.expires_at) IS DISTINCT FROM (OLD.token_hash,OLD.expires_at) THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='R12 immutable invitation'; END IF;
   NEW.revoked_at=clock_timestamp() AT TIME ZONE 'UTC';
  ELSIF NEW.status='pending' THEN
   IF NEW.token_hash!~'^[a-f0-9]{64}$' OR NEW.token_hash=OLD.token_hash OR NEW.expires_at<=clock_timestamp() AT TIME ZONE 'UTC' THEN
    RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='R12 rotation denied'; END IF;
  END IF;
  NEW.updated_at=clock_timestamp() AT TIME ZONE 'UTC';
  RETURN NEW;
 END $$;
CREATE TRIGGER r12_guard_invitation BEFORE INSERT OR UPDATE ON public.client_link_invitations FOR EACH ROW EXECUTE FUNCTION public.r12_guard_invitation();
CREATE FUNCTION public.r12_check_pair() RETURNS trigger LANGUAGE plpgsql VOLATILE SECURITY INVOKER SET search_path=pg_catalog AS $$
 DECLARE invitation public.client_link_invitations; linked public.client_account_links; target text;
 BEGIN
  IF TG_TABLE_NAME='client_link_invitations' THEN
   IF OLD.status<>'pending' OR NEW.status<>'consumed' THEN RETURN NEW; END IF;
   target=NEW.link_id;
  ELSE
   IF OLD.status<>'pending' OR NEW.status<>'active' THEN RETURN NEW; END IF;
   target=NEW.id;
  END IF;
  SELECT * INTO invitation FROM public.client_link_invitations WHERE link_id=target;
  IF NOT FOUND OR invitation.status<>'consumed' OR public.r12_proof(invitation) IS NOT TRUE THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='R12 commit proof unavailable'; END IF;
  SELECT * INTO linked FROM public.client_account_links WHERE id=target;
  IF NOT FOUND OR linked.status NOT IN ('active','revoked') OR linked.user_id IS DISTINCT FROM invitation.consumed_by OR linked.accepted_at IS DISTINCT FROM invitation.consumed_at
   THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='R12 acceptance incomplete'; END IF;
  RETURN NEW;
 END $$;
CREATE CONSTRAINT TRIGGER r12_invitation_pair AFTER UPDATE ON public.client_link_invitations DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.r12_check_pair();
CREATE CONSTRAINT TRIGGER r12_link_pair AFTER UPDATE ON public.client_account_links DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.r12_check_pair();

CREATE FUNCTION public.r12_guard_publication() RETURNS trigger LANGUAGE plpgsql VOLATILE SECURITY INVOKER SET search_path=pg_catalog AS $$
 DECLARE source public.planes_generados; object public.stored_objects; projected jsonb;
 BEGIN
  PERFORM public.r12_require_rc();
  IF TG_OP='UPDATE' THEN
   IF (NEW.id,NEW.gym_id,NEW.client_id,NEW.link_id,NEW.source_plan_id,NEW.source_object_id,NEW.object_key,NEW.content_type,NEW.byte_size,NEW.sha256,NEW.storage_backend,NEW.plan_json)
    IS DISTINCT FROM (OLD.id,OLD.gym_id,OLD.client_id,OLD.link_id,OLD.source_plan_id,OLD.source_object_id,OLD.object_key,OLD.content_type,OLD.byte_size,OLD.sha256,OLD.storage_backend,OLD.plan_json)
    OR (NEW.schema_version,NEW.published_by,NEW.published_at,NEW.plan_sha256) IS DISTINCT FROM (OLD.schema_version,OLD.published_by,OLD.published_at,OLD.plan_sha256)
    OR OLD.status<>'published' OR NEW.status<>'withdrawn' OR NEW.publication_version<>OLD.publication_version+1
    THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='R12 immutable publication'; END IF;
   NEW.withdrawn_at=clock_timestamp() AT TIME ZONE 'UTC';
   RETURN NEW;
  END IF;
  IF NEW.status<>'published' OR NEW.publication_version<>1 OR NEW.schema_version<>1 OR public.r12_lock_canonical_gym(NEW.gym_id) IS NOT TRUE THEN RAISE EXCEPTION USING ERRCODE='42501',MESSAGE='R12 publication owner unavailable'; END IF;
  IF NEW.plan_json IS NULL OR octet_length(NEW.plan_json)>262144 THEN
   RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='R12 projection volume unavailable'; END IF;
  PERFORM 1 FROM public.clientes WHERE gym_id=NEW.gym_id AND id_cliente=NEW.client_id AND activo AND deleted_at IS NULL FOR SHARE;
  IF NOT FOUND THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='R12 publication client unavailable'; END IF;
  PERFORM 1 FROM public.client_account_links WHERE id=NEW.link_id AND gym_id=NEW.gym_id AND client_id=NEW.client_id AND status IN ('pending','active') FOR SHARE;
  IF NOT FOUND THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='R12 publication link unavailable'; END IF;
  SELECT * INTO source FROM public.planes_generados WHERE id=NEW.source_plan_id AND gym_id=NEW.gym_id AND id_cliente=NEW.client_id AND deleted_at IS NULL FOR SHARE;
  IF NOT FOUND OR NEW.source_object_id IS DISTINCT FROM source.pdf_object_id THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='R12 publication source unavailable'; END IF;
  IF source.pdf_object_id IS NOT NULL THEN
   SELECT * INTO object FROM public.stored_objects WHERE id=source.pdf_object_id AND gym_id=NEW.gym_id FOR SHARE;
   IF NOT FOUND OR object.status<>'ready' OR object.kind<>'plan_pdf' OR object.storage_backend NOT IN ('local','s3')
    OR (NEW.source_object_id,NEW.object_key,NEW.content_type,NEW.byte_size,NEW.sha256,NEW.storage_backend)
     IS DISTINCT FROM (object.id,object.key,object.content_type,object.byte_size,object.sha256,object.storage_backend)
    THEN RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='R12 publication object unavailable'; END IF;
  END IF;
  projected=public.r12_project_plan(source);
  IF public.r12_unique_json(NEW.plan_json::json) IS NOT TRUE OR NEW.plan_json::jsonb IS DISTINCT FROM projected
    OR NEW.plan_sha256 IS DISTINCT FROM encode(sha256(convert_to(NEW.plan_json,'UTF8')),'hex') THEN
   RAISE EXCEPTION USING ERRCODE='23514',MESSAGE='R12 projection source mismatch'; END IF;
  NEW.plan_json=projected::text;
  NEW.plan_sha256=encode(sha256(convert_to(NEW.plan_json,'UTF8')),'hex');
  NEW.published_at=clock_timestamp() AT TIME ZONE 'UTC';
  NEW.withdrawn_at=NULL;
  RETURN NEW;
 END $$;
CREATE TRIGGER r12_guard_publication BEFORE INSERT OR UPDATE ON public.client_plan_publications FOR EACH ROW EXECUTE FUNCTION public.r12_guard_publication();
CREATE FUNCTION public.r12_invalidate_source() RETURNS trigger LANGUAGE plpgsql VOLATILE SECURITY INVOKER SET search_path=pg_catalog AS $$
 BEGIN
  IF TG_TABLE_NAME='clientes' THEN
   IF NOT ((NEW.activo IS FALSE AND OLD.activo IS DISTINCT FROM NEW.activo) OR (NEW.deleted_at IS NOT NULL AND OLD.deleted_at IS DISTINCT FROM NEW.deleted_at)
      OR (NEW.gym_id,NEW.id_cliente) IS DISTINCT FROM (OLD.gym_id,OLD.id_cliente)) THEN RETURN NEW; END IF;
   PERFORM public.r12_require_rc();
   PERFORM 1 FROM public.client_account_links WHERE gym_id=OLD.gym_id AND client_id=OLD.id_cliente ORDER BY id FOR UPDATE;
   UPDATE public.client_account_links SET status='revoked',version=version+1,revoked_at=clock_timestamp() AT TIME ZONE 'UTC'
     WHERE gym_id=OLD.gym_id AND client_id=OLD.id_cliente AND status IN ('pending','active');
   UPDATE public.client_link_invitations SET status='revoked',version=version+1 WHERE gym_id=OLD.gym_id AND client_id=OLD.id_cliente AND status='pending';
   UPDATE public.client_plan_publications SET status='withdrawn',publication_version=publication_version+1 WHERE gym_id=OLD.gym_id AND client_id=OLD.id_cliente AND status='published';
  ELSIF TG_TABLE_NAME='planes_generados' THEN
   IF NEW IS NOT DISTINCT FROM OLD THEN RETURN NEW; END IF;
   PERFORM public.r12_require_rc();
   UPDATE public.client_plan_publications SET status='withdrawn',publication_version=publication_version+1 WHERE source_plan_id=OLD.id AND gym_id=OLD.gym_id AND status='published';
  ELSE
   IF (NEW.id,NEW.gym_id,NEW.kind,NEW.key,NEW.content_type,NEW.byte_size,NEW.sha256,NEW.storage_backend,NEW.status)
    IS NOT DISTINCT FROM (OLD.id,OLD.gym_id,OLD.kind,OLD.key,OLD.content_type,OLD.byte_size,OLD.sha256,OLD.storage_backend,OLD.status) THEN RETURN NEW; END IF;
   PERFORM public.r12_require_rc();
   UPDATE public.client_plan_publications SET status='withdrawn',publication_version=publication_version+1 WHERE source_object_id=OLD.id AND gym_id=OLD.gym_id AND status='published';
  END IF;
  RETURN NEW;
 END $$;
CREATE TRIGGER r12_client_invalidation AFTER UPDATE ON public.clientes FOR EACH ROW EXECUTE FUNCTION public.r12_invalidate_source();
CREATE TRIGGER r12_plan_invalidation AFTER UPDATE ON public.planes_generados FOR EACH ROW EXECUTE FUNCTION public.r12_invalidate_source();
CREATE TRIGGER r12_object_invalidation AFTER UPDATE ON public.stored_objects FOR EACH ROW EXECUTE FUNCTION public.r12_invalidate_source();
"""
