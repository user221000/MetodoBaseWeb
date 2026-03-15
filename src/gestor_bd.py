"""
Gestor de base de datos SQLite para clientes y planes.

Gestiona:
- Registro de clientes con todos sus datos
- Historial de planes generados
- Búsqueda rápida de clientes
- Estadísticas del gym
- Backup automático

Base de datos: registros/clientes.db
Backups: registros/backups/clientes_YYYYMMDD_HHMMSS.db
"""

import sqlite3
import shutil
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from pathlib import Path
from utils.logger import logger
from utils.telemetria import registrar_evento
from config.constantes import CARPETA_REGISTROS


class GestorBDClientes:
    """
    Gestiona almacenamiento persistente de clientes y planes.

    Tablas:
    - clientes: datos personales y antropométricos
    - planes_generados: historial de planes con PDFs
    - estadisticas_gym: métricas agregadas por mes
    """

    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = str(Path(CARPETA_REGISTROS) / "clientes.db")
        self.db_path = Path(db_path)
        self.backup_dir = self.db_path.parent / "backups"

        # Crear directorios si no existen
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        # Crear tablas si no existen
        self._crear_tablas()

        # Backup automático cada 7 días
        self._verificar_backup_automatico()

        logger.info("[BD] Gestor inicializado: %s", self.db_path)

    def _crear_tablas(self) -> None:
        """Crea las tablas de la base de datos si no existen."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute('''
            CREATE TABLE IF NOT EXISTS clientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                id_cliente TEXT UNIQUE NOT NULL,
                nombre TEXT NOT NULL,
                telefono TEXT,
                email TEXT,
                edad INTEGER,
                sexo TEXT CHECK(sexo IN ('M', 'F', 'Otro', NULL)),
                peso_kg REAL,
                estatura_cm REAL,
                grasa_corporal_pct REAL,
                masa_magra_kg REAL,
                nivel_actividad TEXT,
                objetivo TEXT,
                fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ultimo_plan TIMESTAMP,
                total_planes_generados INTEGER DEFAULT 0,
                activo BOOLEAN DEFAULT 1,
                notas TEXT
            )
        ''')

        c.execute('CREATE INDEX IF NOT EXISTS idx_nombre ON clientes(nombre)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_telefono ON clientes(telefono)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_activo ON clientes(activo)')

        c.execute('''
            CREATE TABLE IF NOT EXISTS planes_generados (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                id_cliente TEXT NOT NULL,
                fecha_generacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                tmb REAL,
                get_total REAL,
                kcal_objetivo REAL,
                kcal_real REAL,
                proteina_g REAL,
                carbs_g REAL,
                grasa_g REAL,
                objetivo TEXT,
                nivel_actividad TEXT,
                ruta_pdf TEXT,
                peso_en_momento REAL,
                grasa_en_momento REAL,
                desviacion_maxima_pct REAL,
                FOREIGN KEY (id_cliente) REFERENCES clientes(id_cliente)
            )
        ''')

        c.execute('CREATE INDEX IF NOT EXISTS idx_cliente_planes ON planes_generados(id_cliente)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_fecha_planes ON planes_generados(fecha_generacion)')

        c.execute('''
            CREATE TABLE IF NOT EXISTS estadisticas_gym (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mes INTEGER NOT NULL,
                anio INTEGER NOT NULL,
                total_clientes_nuevos INTEGER DEFAULT 0,
                total_planes_generados INTEGER DEFAULT 0,
                promedio_kcal REAL,
                objetivo_deficit_count INTEGER DEFAULT 0,
                objetivo_superavit_count INTEGER DEFAULT 0,
                objetivo_mantenimiento_count INTEGER DEFAULT 0,
                fecha_calculo TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(mes, anio)
            )
        ''')

        self._asegurar_columna(
            c, "clientes", "plantilla_tipo TEXT DEFAULT 'general'"
        )
        self._asegurar_columna(
            c, "planes_generados", "plantilla_tipo TEXT DEFAULT 'general'"
        )
        self._asegurar_columna(
            c, "planes_generados", "tipo_plan TEXT DEFAULT 'menu_fijo'"
        )

        conn.commit()
        conn.close()
        logger.info("[BD] Tablas creadas/verificadas exitosamente")

    def _obtener_columnas_tabla(self, cursor, tabla: str) -> set[str]:
        cursor.execute(f"PRAGMA table_info({tabla})")
        return {row[1] for row in cursor.fetchall()}

    def _asegurar_columna(self, cursor, tabla: str, definicion_columna: str) -> None:
        nombre_columna = definicion_columna.split()[0].strip()
        columnas = self._obtener_columnas_tabla(cursor, tabla)
        if nombre_columna in columnas:
            return
        cursor.execute(f"ALTER TABLE {tabla} ADD COLUMN {definicion_columna}")
        logger.info("[BD] Migracion aplicada: %s.%s", tabla, nombre_columna)

    @staticmethod
    def _normalizar_tipo_plan(tipo_plan: str | None) -> str:
        valor = str(tipo_plan or "").strip().lower()
        if valor in {"con_opciones", "opciones", "con opciones"}:
            return "con_opciones"
        return "menu_fijo"

    def registrar_cliente(self, cliente) -> bool:
        """Registra o actualiza un cliente en la base de datos."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        plantilla_tipo = getattr(cliente, 'plantilla_tipo', 'general') or 'general'

        try:
            c.execute(
                'SELECT id, total_planes_generados FROM clientes WHERE id_cliente = ?',
                (cliente.id_cliente,),
            )
            resultado = c.fetchone()

            if resultado:
                c.execute('''
                    UPDATE clientes SET
                        nombre = ?,
                        telefono = ?,
                        edad = ?,
                        peso_kg = ?,
                        estatura_cm = ?,
                        grasa_corporal_pct = ?,
                        nivel_actividad = ?,
                        objetivo = ?,
                        plantilla_tipo = ?,
                        ultimo_plan = ?,
                        total_planes_generados = total_planes_generados + 1
                    WHERE id_cliente = ?
                ''', (
                    cliente.nombre,
                    getattr(cliente, 'telefono', None),
                    cliente.edad,
                    cliente.peso_kg,
                    cliente.estatura_cm,
                    cliente.grasa_corporal_pct,
                    cliente.nivel_actividad,
                    cliente.objetivo,
                    plantilla_tipo,
                    datetime.now(),
                    cliente.id_cliente,
                ))
                logger.info("[BD] Cliente actualizado: %s", cliente.id_cliente)
            else:
                c.execute('''
                    INSERT INTO clientes
                    (id_cliente, nombre, telefono, edad, peso_kg, estatura_cm,
                     grasa_corporal_pct, nivel_actividad, objetivo, plantilla_tipo, ultimo_plan,
                     total_planes_generados)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    cliente.id_cliente,
                    cliente.nombre,
                    getattr(cliente, 'telefono', None),
                    cliente.edad,
                    cliente.peso_kg,
                    cliente.estatura_cm,
                    cliente.grasa_corporal_pct,
                    cliente.nivel_actividad,
                    cliente.objetivo,
                    plantilla_tipo,
                    datetime.now(),
                    1,
                ))
                logger.info("[BD] Cliente nuevo registrado: %s", cliente.id_cliente)

            conn.commit()
            return True

        except Exception as e:
            logger.error("[BD] Error registrando cliente: %s", e, exc_info=True)
            conn.rollback()
            return False

        finally:
            conn.close()

    def registrar_plan_generado(
        self, cliente, plan: Dict, ruta_pdf: str, tipo_plan: str | None = None
    ) -> bool:
        """Registra un plan generado en el historial."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        plantilla_tipo = getattr(cliente, 'plantilla_tipo', 'general') or 'general'
        tipo_plan_normalizado = self._normalizar_tipo_plan(tipo_plan)

        if tipo_plan is None:
            metadata_tipo = str(plan.get("metadata", {}).get("tipo_plan", "")).strip().lower()
            if metadata_tipo in {"opciones", "con_opciones"}:
                tipo_plan_normalizado = "con_opciones"
            elif "_OPCIONES_" in str(ruta_pdf or "").upper():
                tipo_plan_normalizado = "con_opciones"

        try:
            comidas = ['desayuno', 'almuerzo', 'comida', 'cena']
            kcal_real = sum(
                plan.get(m, {}).get('kcal_real', 0) for m in comidas
            )
            desv_max = max(
                (plan.get(m, {}).get('desviacion_pct', 0) for m in comidas if m in plan),
                default=0,
            )

            c.execute('''
                INSERT INTO planes_generados
                (id_cliente, tmb, get_total, kcal_objetivo, kcal_real,
                 proteina_g, carbs_g, grasa_g, objetivo, nivel_actividad,
                 ruta_pdf, peso_en_momento, grasa_en_momento, desviacion_maxima_pct,
                 plantilla_tipo, tipo_plan)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                cliente.id_cliente,
                getattr(cliente, 'tmb', 0),
                getattr(cliente, 'get_total', 0),
                getattr(cliente, 'kcal_objetivo', 0),
                kcal_real,
                getattr(cliente, 'proteina_g', 0),
                getattr(cliente, 'carbs_g', 0),
                getattr(cliente, 'grasa_g', 0),
                cliente.objetivo,
                cliente.nivel_actividad,
                ruta_pdf,
                cliente.peso_kg,
                cliente.grasa_corporal_pct,
                desv_max,
                plantilla_tipo,
                tipo_plan_normalizado,
            ))

            conn.commit()
            logger.info("[BD] Plan registrado para cliente: %s", cliente.id_cliente)
            registrar_evento("planes", "plan_generado", {
                "objetivo": cliente.objetivo,
                "tipo_plan": tipo_plan_normalizado,
                "plantilla": plantilla_tipo,
                "kcal_objetivo": getattr(cliente, 'kcal_objetivo', 0),
            })
            return True

        except Exception as e:
            logger.error("[BD] Error registrando plan: %s", e, exc_info=True)
            registrar_evento("planes", "plan_error", {"error": str(e)})
            conn.rollback()
            return False

        finally:
            conn.close()

    def buscar_clientes(self, termino: str,
                        solo_activos: bool = True,
                        limite: int = 50) -> List[Dict]:
        """Busca clientes por nombre, teléfono o ID."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        try:
            query = '''
                SELECT
                    id_cliente, nombre, telefono, email, edad,
                    peso_kg, grasa_corporal_pct, objetivo, nivel_actividad,
                    plantilla_tipo, fecha_registro, ultimo_plan,
                    total_planes_generados, activo
                FROM clientes
                WHERE (
                    nombre LIKE ? OR
                    telefono LIKE ? OR
                    id_cliente LIKE ?
                )
            '''
            params = [f'%{termino}%', f'%{termino}%', f'%{termino}%']

            if solo_activos:
                query += ' AND activo = 1'

            query += ' ORDER BY ultimo_plan DESC, nombre ASC LIMIT ?'
            params.append(limite)

            c.execute(query, params)

            resultados = []
            for row in c.fetchall():
                resultados.append({
                    'id_cliente': row['id_cliente'],
                    'nombre': row['nombre'],
                    'telefono': row['telefono'],
                    'email': row['email'],
                    'edad': row['edad'],
                    'peso_kg': row['peso_kg'],
                    'grasa_corporal_pct': row['grasa_corporal_pct'],
                    'objetivo': row['objetivo'],
                    'nivel_actividad': row['nivel_actividad'],
                    'plantilla_tipo': row['plantilla_tipo'],
                    'fecha_registro': row['fecha_registro'],
                    'ultimo_plan': row['ultimo_plan'],
                    'total_planes_generados': row['total_planes_generados'],
                    'total_planes': row['total_planes_generados'],
                    'activo': bool(row['activo']),
                })

            logger.info("[BD] Búsqueda '%s': %s resultados", termino, len(resultados))
            return resultados

        except Exception as e:
            logger.error("[BD] Error en búsqueda: %s", e, exc_info=True)
            return []

        finally:
            conn.close()

    def obtener_cliente_por_id(self, id_cliente: str) -> Optional[Dict]:
        """Obtiene todos los datos de un cliente por su ID."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        try:
            c.execute('SELECT * FROM clientes WHERE id_cliente = ?', (id_cliente,))
            row = c.fetchone()
            return dict(row) if row else None

        except Exception as e:
            logger.error("[BD] Error obteniendo cliente: %s", e, exc_info=True)
            return None

        finally:
            conn.close()

    def obtener_historial_planes(self, id_cliente: str,
                                 limite: int = 20) -> List[Dict]:
        """Obtiene el historial de planes generados para un cliente."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        try:
            c.execute('''
                SELECT
                    fecha_generacion, kcal_objetivo, kcal_real,
                    proteina_g, carbs_g, grasa_g, objetivo,
                    ruta_pdf, peso_en_momento, grasa_en_momento,
                    desviacion_maxima_pct, plantilla_tipo, tipo_plan
                FROM planes_generados
                WHERE id_cliente = ?
                ORDER BY fecha_generacion DESC
                LIMIT ?
            ''', (id_cliente, limite))

            return [dict(row) for row in c.fetchall()]

        except Exception as e:
            logger.error("[BD] Error obteniendo historial: %s", e, exc_info=True)
            return []

        finally:
            conn.close()

    def obtener_progreso_cliente(self, id_cliente: str) -> Dict:
        """Calcula progreso de peso y grasa a partir del historial de planes."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        try:
            c.execute('''
                SELECT fecha_generacion, peso_en_momento, grasa_en_momento
                FROM planes_generados
                WHERE id_cliente = ?
                ORDER BY fecha_generacion ASC
            ''', (id_cliente,))
            registros = [dict(row) for row in c.fetchall()]

            if not registros:
                return {
                    'planes_registrados': 0,
                    'peso_inicial': None,
                    'peso_actual': None,
                    'delta_peso': None,
                    'grasa_inicial': None,
                    'grasa_actual': None,
                    'delta_grasa': None,
                    'fecha_inicio': None,
                    'fecha_fin': None,
                }

            peso_inicial = None
            peso_actual = None
            grasa_inicial = None
            grasa_actual = None

            for item in registros:
                peso = item.get('peso_en_momento')
                grasa = item.get('grasa_en_momento')

                if peso is not None:
                    if peso_inicial is None:
                        peso_inicial = float(peso)
                    peso_actual = float(peso)
                if grasa is not None:
                    if grasa_inicial is None:
                        grasa_inicial = float(grasa)
                    grasa_actual = float(grasa)

            delta_peso = (
                round(peso_actual - peso_inicial, 2)
                if peso_inicial is not None and peso_actual is not None
                else None
            )
            delta_grasa = (
                round(grasa_actual - grasa_inicial, 2)
                if grasa_inicial is not None and grasa_actual is not None
                else None
            )

            return {
                'planes_registrados': len(registros),
                'peso_inicial': peso_inicial,
                'peso_actual': peso_actual,
                'delta_peso': delta_peso,
                'grasa_inicial': grasa_inicial,
                'grasa_actual': grasa_actual,
                'delta_grasa': delta_grasa,
                'fecha_inicio': registros[0].get('fecha_generacion'),
                'fecha_fin': registros[-1].get('fecha_generacion'),
            }

        except Exception as e:
            logger.error("[BD] Error obteniendo progreso cliente: %s", e, exc_info=True)
            return {
                'planes_registrados': 0,
                'peso_inicial': None,
                'peso_actual': None,
                'delta_peso': None,
                'grasa_inicial': None,
                'grasa_actual': None,
                'delta_grasa': None,
                'fecha_inicio': None,
                'fecha_fin': None,
            }
        finally:
            conn.close()

    def obtener_estadisticas_gym(self,
                                 fecha_inicio: Optional[datetime] = None,
                                 fecha_fin: Optional[datetime] = None) -> Dict:
        """Obtiene estadísticas generales del gimnasio."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        try:
            if not fecha_inicio:
                fecha_inicio = datetime.now() - timedelta(days=30)
            if not fecha_fin:
                fecha_fin = datetime.now()

            c.execute('SELECT COUNT(*) FROM clientes WHERE activo = 1')
            total_clientes = c.fetchone()[0]

            c.execute('''
                SELECT COUNT(*) FROM clientes
                WHERE fecha_registro BETWEEN ? AND ?
            ''', (fecha_inicio, fecha_fin))
            clientes_nuevos = c.fetchone()[0]

            c.execute('''
                SELECT COUNT(*) FROM planes_generados
                WHERE fecha_generacion BETWEEN ? AND ?
            ''', (fecha_inicio, fecha_fin))
            planes_periodo = c.fetchone()[0]

            c.execute('''
                SELECT AVG(kcal_objetivo) FROM planes_generados
                WHERE fecha_generacion BETWEEN ? AND ?
            ''', (fecha_inicio, fecha_fin))
            promedio_kcal = c.fetchone()[0] or 0

            c.execute('''
                SELECT objetivo, COUNT(*) as count
                FROM planes_generados
                WHERE fecha_generacion BETWEEN ? AND ?
                GROUP BY objetivo
            ''', (fecha_inicio, fecha_fin))
            objetivos = {row[0]: row[1] for row in c.fetchall()}

            c.execute('''
                SELECT c.nombre, c.total_planes_generados
                FROM clientes c
                WHERE c.activo = 1
                ORDER BY c.total_planes_generados DESC
                LIMIT 10
            ''')
            top_clientes = [
                {'nombre': row[0], 'planes': row[1]} for row in c.fetchall()
            ]

            # --- KPIs de negocio adicionales ---

            # Clientes activos: con plan generado en el período
            c.execute('''
                SELECT COUNT(DISTINCT id_cliente) FROM planes_generados
                WHERE fecha_generacion BETWEEN ? AND ?
            ''', (fecha_inicio, fecha_fin))
            clientes_activos = c.fetchone()[0]

            # Renovaciones: clientes con más de 1 plan en el período
            c.execute('''
                SELECT COUNT(*) FROM (
                    SELECT id_cliente, COUNT(*) as cnt
                    FROM planes_generados
                    WHERE fecha_generacion BETWEEN ? AND ?
                    GROUP BY id_cliente
                    HAVING cnt > 1
                )
            ''', (fecha_inicio, fecha_fin))
            renovaciones = c.fetchone()[0]

            # Tasa de retención: clientes activos / total clientes (%)
            tasa_retencion = (
                round(clientes_activos / total_clientes * 100, 1)
                if total_clientes > 0 else 0.0
            )

            # Planes por tipo (menú fijo vs opciones)
            c.execute('''
                SELECT tipo_plan, COUNT(*) FROM planes_generados
                WHERE fecha_generacion BETWEEN ? AND ?
                GROUP BY tipo_plan
            ''', (fecha_inicio, fecha_fin))
            planes_por_tipo = {row[0] or "menu_fijo": row[1] for row in c.fetchall()}

            return {
                'total_clientes': total_clientes,
                'clientes_nuevos': clientes_nuevos,
                'clientes_activos': clientes_activos,
                'planes_periodo': planes_periodo,
                'promedio_kcal': round(promedio_kcal, 1),
                'objetivos': objetivos,
                'top_clientes': top_clientes,
                'renovaciones': renovaciones,
                'tasa_retencion': tasa_retencion,
                'planes_por_tipo': planes_por_tipo,
                'fecha_inicio': fecha_inicio.isoformat(),
                'fecha_fin': fecha_fin.isoformat(),
            }

        except Exception as e:
            logger.error("[BD] Error obteniendo estadísticas: %s", e, exc_info=True)
            return {}

        finally:
            conn.close()

    def desactivar_cliente(self, id_cliente: str) -> bool:
        """Marca un cliente como inactivo (no lo elimina)."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        try:
            c.execute('UPDATE clientes SET activo = 0 WHERE id_cliente = ?',
                      (id_cliente,))
            conn.commit()
            logger.info("[BD] Cliente desactivado: %s", id_cliente)
            return True

        except Exception as e:
            logger.error("[BD] Error desactivando cliente: %s", e, exc_info=True)
            return False

        finally:
            conn.close()

    def reactivar_cliente(self, id_cliente: str) -> bool:
        """Reactiva un cliente previamente desactivado."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        try:
            c.execute('UPDATE clientes SET activo = 1 WHERE id_cliente = ?',
                      (id_cliente,))
            conn.commit()
            logger.info("[BD] Cliente reactivado: %s", id_cliente)
            return True

        except Exception as e:
            logger.error("[BD] Error reactivando cliente: %s", e, exc_info=True)
            return False

        finally:
            conn.close()

    def crear_backup(self) -> Optional[str]:
        """Crea un backup de la base de datos."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            nombre_backup = f"clientes_{timestamp}.db"
            ruta_backup = self.backup_dir / nombre_backup
            shutil.copy2(self.db_path, ruta_backup)
            logger.info("[BD] Backup creado: %s", ruta_backup)
            return str(ruta_backup)

        except Exception as e:
            logger.error("[BD] Error creando backup: %s", e, exc_info=True)
            return None

    def _verificar_backup_automatico(self) -> None:
        """Verifica si es necesario crear un backup automático (cada 7 días)."""
        try:
            backups = sorted(self.backup_dir.glob("clientes_*.db"), reverse=True)

            if not backups:
                self.crear_backup()
                return

            ultimo_backup = backups[0]
            fecha_backup = datetime.fromtimestamp(ultimo_backup.stat().st_mtime)

            if (datetime.now() - fecha_backup).days >= 7:
                logger.info("[BD] Backup automático (>7 días desde último)")
                self.crear_backup()

        except Exception as e:
            logger.error("[BD] Error en backup automático: %s", e, exc_info=True)

    def limpiar_backups_antiguos(self, dias_antiguedad: int = 90) -> int:
        """Elimina backups más antiguos que N días."""
        try:
            fecha_limite = datetime.now() - timedelta(days=dias_antiguedad)
            backups_eliminados = 0

            for backup in self.backup_dir.glob("clientes_*.db"):
                fecha_backup = datetime.fromtimestamp(backup.stat().st_mtime)
                if fecha_backup < fecha_limite:
                    backup.unlink()
                    backups_eliminados += 1

            if backups_eliminados > 0:
                logger.info("[BD] Eliminados %s backups antiguos", backups_eliminados)

            return backups_eliminados

        except Exception as e:
            logger.error("[BD] Error limpiando backups: %s", e, exc_info=True)
            return 0

    def obtener_todos_clientes(self, solo_activos: bool = False) -> list[dict]:
        """Devuelve todos los clientes de la base de datos para exportación."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        try:
            query = '''
                SELECT id_cliente, nombre, telefono, email, edad,
                       peso_kg, estatura_cm, grasa_corporal_pct,
                       nivel_actividad, objetivo, plantilla_tipo, fecha_registro,
                       ultimo_plan, total_planes_generados, activo
                FROM clientes
            '''
            if solo_activos:
                query += ' WHERE activo = 1'
            query += ' ORDER BY nombre ASC'

            c.execute(query)
            resultados = [dict(row) for row in c.fetchall()]
            logger.info("[BD] Exportando todos los clientes: %s registros", len(resultados))
            return resultados

        except Exception as e:
            logger.error("[BD] Error obteniendo todos los clientes: %s", e, exc_info=True)
            return []

        finally:
            conn.close()

    def obtener_planes_periodo(self,
                               fecha_inicio: datetime,
                               fecha_fin: datetime) -> list[dict]:
        """Devuelve todos los planes generados en el período con nombre del cliente."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        try:
            c.execute('''
                SELECT
                    c.nombre,
                    p.fecha_generacion, p.kcal_objetivo, p.kcal_real,
                    p.proteina_g, p.carbs_g, p.grasa_g, p.objetivo,
                    p.plantilla_tipo, p.tipo_plan,
                    p.peso_en_momento, p.grasa_en_momento,
                    p.desviacion_maxima_pct, p.ruta_pdf
                FROM planes_generados p
                LEFT JOIN clientes c ON p.id_cliente = c.id_cliente
                WHERE p.fecha_generacion BETWEEN ? AND ?
                ORDER BY p.fecha_generacion DESC
            ''', (fecha_inicio, fecha_fin))
            resultados = [dict(row) for row in c.fetchall()]
            logger.info("[BD] Planes período: %s registros", len(resultados))
            return resultados

        except Exception as e:
            logger.error("[BD] Error obteniendo planes del período: %s", e, exc_info=True)
            return []

        finally:
            conn.close()
