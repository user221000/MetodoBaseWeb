"""Build and validate the execution ledger from immutable audit sources.

JSON is the canonical state. ``--render`` regenerates its Markdown view;
``--check`` rejects missing IDs, incomplete records, or a stale view.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "docs/implementation/20261018-evolution"
AUDIT = ROOT / "docs/audit/2026-10-18"
LINKS = {
    "R01": "B01 B02 B03 B13 B14 B15 B16 B17 UX-01 UX-13",
    "R02": "B06 B07 B22 QA-05", "R03": "B04 B18 QA-03 QA-04 OPS01 UX-14",
    "R04": "B04 B05 QA-05 OPS02", "R05": "QA-01 QA-02 QA-07 QA-08 QA-09 QA-10 OPS07",
    "R06": "B09 B22 B23 UX-02 UX-15", "R07": "B11 OPS03", "R08": "B10 OPS04",
    "R09": "QA-06 B02 UX-16", "R10": "B08 B19 B20", "R11": "B06 B19 UX-06",
    "R12": "UX-07", "R13": "UX-05 UX-08 UX-09 QA-09", "R14": "UX-03 UX-04 B17",
    "R15": "UX-01 UX-10 UX-11 UX-12 UX-13 UX-17", "R16": "B19 UX-15 OPS06",
    "R17": "B12 B22 OPS05", "R18": "B21 QA-10 OPS07",
    "R19": "QA-05 QA-08 QA-09 B13 B14 B16 B17", "R20": "B22 UX-12",
    "R21": "QA-10", "R22": "UX-11 UX-12 UX-17", "R23": "UX-13",
    "R24": "UX-02 UX-10 UX-17", "R25": "UX-07", "R26": "B02 B13 B14 B15 B18 UX-01 UX-13",
    "R27": "B15 UX-13 OPS06", "R28": "B16 B17", "R29": "UX-16", "R30": "UX-17",
    "R31": "B20 UX-03", "R32": "B19 B20", "R33": "B09 B23 UX-02",
    "R34": "B17", "R35": "UX-05 UX-09",
}
DEPENDENCIES = {"R04": ["R02", "R03"], "R07": ["R04"], "R09": ["R01"],
    "R11": ["R02", "R16"], "R12": ["R04"], "R19": ["R01", "R02", "R12"],
    "R24": ["R14"], "R25": ["R12", "R14"], "R26": ["R01", "R09"],
    "R27": ["R16", "R26"], "R32": ["R10", "R16"], "R35": ["R14", "R34"]}
EXPECTED = ({f"R{i:02}" for i in range(1, 36)} | {f"B{i:02}" for i in range(1, 24)}
    | {f"QA-{i:02}" for i in range(1, 11)} | {f"UX-{i:02}" for i in range(1, 18)}
    | {f"OPS{i:02}" for i in range(1, 8)})


def owner(task: str) -> str:
    """Return the accountable role, including work awaiting a later wave."""
    if task in {"R05", "R18", "R19", "R34"}: return "QA y automatización"
    if task in {"R10", "R31", "R32"}: return "Seguridad y privacidad"
    if task in {"R07", "R08", "R17", "R21"}: return "Operación y documentación"
    if task in {"R13", "R15", "R22", "R23", "R24", "R29", "R35"}: return "Frontend y UX/UI"
    if task in {"R09", "R20", "R30", "R33"}: return "Coordinación y arquitectura"
    return "Backend y datos"


def record(ident: str, path: Path, section: str, problem: str, criterion: str, priority: str) -> dict:
    tasks = [ident] if ident.startswith("R") else [r for r, refs in LINKS.items() if ident in refs.split()]
    return {"id": ident, "identificador_original": ident, "fuente": path.relative_to(ROOT).as_posix(),
        "seccion": section, "problema": problem.strip(), "criterio_exacto": criterion.strip(),
        "prioridad": priority, "responsable": owner(tasks[0]), "tareas": tasks,
        "dependencias": DEPENDENCIES.get(ident, []), "estado": "pendiente",
        "implementacion": "pendiente", "validacion": "pendiente", "despliegue": "no_desplegado",
        "entorno": "local", "cambios": [], "commits": [], "pruebas": [], "evidencia": [],
        "documentacion": [], "revisor": None, "bloqueo": None, "observaciones": []}


def sections(path: Path, prefix: str):
    text = path.read_text(encoding="utf-8")
    matches = list(re.finditer(r"^### (" + prefix + r"\d{2})[^\n]*", text, re.M))
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = re.split(r"\n## ", text[match.end():end], maxsplit=1)[0].strip()
        yield match.group(1), match.group(0).removeprefix("### "), body


def initial() -> list[dict]:
    records = []
    path = AUDIT / "ROADMAP_PRIORIZADO.md"
    for line in path.read_text(encoding="utf-8").splitlines():
        if not re.match(r"\| R\d{2} P", line): continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        ident, priority = cells[0].split()
        records.append(record(ident, path, cells[0], cells[1], cells[3], priority))
    path = AUDIT / "backend/INFORME_BACKEND.md"
    for ident, heading, body in sections(path, "B"):
        if ident not in EXPECTED: continue
        parts = body.split("Aceptación:", 1)
        records.append(record(ident, path, heading, parts[0], parts[-1], re.search(r"P[0-2]", heading).group()))
    for line in path.read_text(encoding="utf-8").splitlines():
        if not re.match(r"\| B\d{2} \|", line): continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        records.append(record(cells[0], path, cells[0], cells[2], cells[3], cells[1]))
    path = AUDIT / "qa/INFORME_QA.md"
    for ident, heading, body in sections(path, "QA-"):
        parts = re.split(r"\*\*Acción/aceptación:\*\*", body, maxsplit=1)
        priority = "P0" if int(ident[-2:]) <= 5 else "P1" if int(ident[-2:]) <= 9 else "P2"
        records.append(record(ident, path, heading, parts[0], parts[-1], priority))
    path = AUDIT / "ux/INFORME_UX.md"
    for line in path.read_text(encoding="utf-8").splitlines():
        if not re.match(r"\| UX-\d{2} /", line): continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        ident, priority = cells[0].split(" / ")
        records.append(record(ident, path, cells[0], cells[1], cells[2], priority))
    path = AUDIT / "OPERACION_Y_SEGURIDAD.md"
    for ident, heading, body in sections(path, "OPS"):
        parts = re.split(r"\*\*Aceptación(?: propuesta)?:\*\*", body, maxsplit=1)
        priority = re.search(r"Prioridad (P[0-2])", body).group(1)
        records.append(record(ident, path, heading, parts[0], parts[-1], priority))
    return sorted(records, key=lambda r: (0 if r["id"].startswith("R") else 1, r["id"]))


def markdown(data: dict) -> str:
    lines = ["# Trazabilidad de ejecución", "", f"Ejecución: `{data['ejecucion']}`. Fuente canónica: [TRAZABILIDAD.json](TRAZABILIDAD.json).",
        "", "Los 92 IDs se conservan; los solapamientos no representan defectos independientes. Los estados pendientes no constituyen aprobación.", "",
        "| ID | Prioridad | Responsable | Tareas | Estado | Validación | Entorno |", "|---|---|---|---|---|---|---|"]
    for r in data["requisitos"]:
        lines.append(f"| [{r['id']}](#{r['id'].lower()}) | {r['prioridad']} | {r['responsable']} | {', '.join(r['tareas'])} | {r['estado']} | {r['validacion']} | {r['entorno']} |")
    for r in data["requisitos"]:
        lines.extend(["", f"## {r['id']}", "", f"Fuente: [{r['seccion']}](../../audit/2026-10-18/{Path(r['fuente']).relative_to('docs/audit/2026-10-18').as_posix()}).",
            "", "Problema: " + r["problema"], "", "Criterio original: " + r["criterio_exacto"], "",
            f"Estado: {r['estado']}; implementación: {r['implementacion']}; validación: {r['validacion']}; despliegue: {r['despliegue']}; entorno: {r['entorno']}.",
            "", "Dependencias: " + (", ".join(r["dependencias"]) or "sin dependencia declarada"),
            "", "Evidencia: " + ("; ".join(r["evidencia"]) or "pendiente"),
            "", "Revisión: " + (r["revisor"] or "pendiente"),
            "", "Bloqueo: " + (json.dumps(r["bloqueo"], ensure_ascii=False) if r["bloqueo"] else "no registrado"),
            "", "Observaciones: " + ("; ".join(r["observaciones"]) or "sin observaciones")])
    return "\n".join(lines) + "\n"


def validate(data: dict) -> None:
    rows = data["requisitos"]
    ids = [r["id"] for r in rows]
    if len(ids) != len(set(ids)) or not EXPECTED.issubset(ids): raise ValueError("IDs ausentes o duplicados")
    states = {"pendiente", "en_curso", "en_revision", "verificado", "bloqueado_externo"}
    for row in rows:
        for key in ("fuente", "seccion", "problema", "criterio_exacto", "prioridad", "responsable", "tareas", "estado"):
            if not row.get(key): raise ValueError(f"{row['id']}: falta {key}")
        if row["estado"] not in states: raise ValueError(f"{row['id']}: estado inválido")
        if not (ROOT / row["fuente"]).is_file(): raise ValueError(f"Fuente ausente: {row['fuente']}")
        if row["estado"] == "verificado" and (not row["revisor"] or not row["evidencia"] or row["validacion"] != "verificado"):
            raise ValueError(f"{row['id']}: cierre sin revisión/evidencia")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--initialize", action="store_true")
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    path = RUN / "TRAZABILIDAD.json"
    if args.initialize:
        if path.exists(): raise SystemExit("El registro ya existe; no se sobrescribe")
        data = {"ejecucion": "20261018-evolution", "base_commit": "daa25efbf51d154710bad625025b345fa9ec9252", "requisitos": initial()}
        validate(data)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    data = json.loads(path.read_text(encoding="utf-8"))
    validate(data)
    rendered = markdown(data)
    target = RUN / "TRAZABILIDAD.md"
    if args.render or args.initialize: target.write_text(rendered, encoding="utf-8")
    if args.check and target.read_text(encoding="utf-8") != rendered: raise SystemExit("Vista Markdown desactualizada")
    print(f"{len(data['requisitos'])} requisitos; fuentes y campos válidos")


if __name__ == "__main__":
    main()
