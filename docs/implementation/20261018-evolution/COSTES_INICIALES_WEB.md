# Costes iniciales del servicio web

El usuario confirmó el 23 de octubre de 2026 que busca vender el SaaS a gimnasios y todavía no ha definido demanda ni presupuesto mensual. Los escenarios de este documento son supuestos de ingeniería para tomar esa decisión. No son una factura, un presupuesto aprobado ni una capacidad de usuarios demostrada.

## Tarifas de referencia verificadas

Las tarifas publicadas para contenedores Railway son 10 dólares por GB de RAM/mes, 20 por vCPU/mes de uso, 0,15 por GB de volumen/mes y 0,05 por GB de salida. Pro tiene una cuota mínima de 20 dólares que cuenta como crédito de uso; no se suma dos veces. Estos valores corresponden a contenedores, no a las tarifas de máquinas virtuales o agentes. [Tarifas oficiales](https://docs.railway.com/pricing), [crédito y planes](https://docs.railway.com/pricing/plans).

Para un mes completo, una aproximación de planificación es:

`total Railway = max(20, 10 × RAM_GB_media + 20 × vCPU_media + 0,15 × volumen_GB + 0,05 × salida_GB)`

Se suman todos los servicios del proyecto: web, PostgreSQL y Redis, si se utiliza. La RAM media es consumo retenido durante el mes y la vCPU media es uso de CPU, no el límite configurado. El proveedor mide el consumo real; sus redondeos pueden diferir de esta aproximación mensual. [Interpretación de métricas](https://docs.railway.com/guides/right-size-cpu-memory).

| Supuesto técnico mensual, sin capacidad comercial atribuida | RAM media conjunta | CPU media conjunta | Volumen | Salida | Aproximación Railway |
|---|---:|---:|---:|---:|---:|
| A | 1 GB | 0,1 vCPU | 5 GB | 2 GB | 20,00 dólares |
| B | 2 GB | 0,3 vCPU | 10 GB | 10 GB | 28,00 dólares |
| C | 4 GB | 1 vCPU | 20 GB | 50 GB | 65,50 dólares |

Las cifras se calculan con la fórmula anterior; no representan mediciones de MetodoBase. No incluyen dominio, correo, copias externas, almacenamiento remoto, comisiones de cobro, impuestos ni conversión a MXN. Tampoco fijan precios de venta o margen.

## Medición que debe alimentar la decisión

R34 mide generación real, PDF, PUT y descarga con datos sintéticos y cuotas reales. Debe conservar número de muestras, concurrencia, errores, CPU/RSS del worker, tiempos por fase y bytes. Una ejecución rechazada o sin generaciones no aporta un coste por plan ni capacidad. El primer intento de esta reanudación generó cero planes y permanece rechazado.

La medición local Windows no equivale al consumo facturable de web, PostgreSQL y Redis en Railway. Para fijar presupuesto y capacidad vendible faltan una ejecución aceptada, la imagen Linux final, la mezcla de uso prevista y métricas del entorno elegido. Se deben definir después un límite de gasto, alertas y un umbral de admisión coherentes con esa evidencia. No se ha cambiado ningún plan ni límite de facturación del proveedor.
