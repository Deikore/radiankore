# Revisión de documentación, referencias y arquitectura

Fecha: 23 de octubre de 2026. Estado: plan implementado y verificado.
Se aplicaron `python-library-architect` y `radian-anexo`. Los hallazgos y la
verificación inicial se conservan abajo como antecedente; su resolución figura
en «Resultado de la implementación». Se preservaron los cambios previos y los
bytes originales de las referencias oficiales.

## Respuesta sobre los eventos posteriores a 045

Sí están en las referencias locales. El anexo RADIAN 1.1 tiene 482 páginas y
no termina en el evento 045. Su índice de la página 3 enumera los perfiles que
siguen al pago 045. Se comprobaron también sus encabezados en las páginas de
generación y validación, no solo los nombres del índice.

Archivo: `docs/references/dian/radian/1.1/anexo-tecnico.pdf`.

| Evento | Generación | Página física | Validación | Página física | XML de ejemplo |
| --- | --- | ---: | --- | ---: | ---: |
| 046 Informe para el pago | §7.2.5.14 | 231 | §9.2.15 | 402 | 1 |
| 047 Endoso con efectos de cesión ordinaria | §7.2.5.15 | 239 | §9.2.16 | 405 | 1 |
| 048 Protesto | §7.2.5.16 | 250 | §9.2.17 | 411 | 2 |
| 049 Transferencia de derechos económicos | §7.2.5.17 | 261 | §9.2.18 | 416 | 4 |
| 050 Notificación al deudor | §7.2.5.18 | 272 | §9.2.19 | 422 | 1 |
| 051 Pago de transferencia | §7.2.5.19 | 280 | §9.2.20 | 425 | 2 |

Los 11 XML están bajo
`docs/references/dian/radian/toolbox/Ejemplificaciones/XMLs de ejemplo/`,
en las carpetas con prefijos `046-` a `051-`. Las operaciones están en §14.1.2,
pp. 468–469, y la tabla de eventos en §14.2.1, p. 470. Las extensiones de 048–051
se describen en §§7.2.4.10–13 y §§9.2.3.10–13.

Hay otro archivo con el mismo nombre, bajo
`docs/references/dian/invoicing/1.9/anexo-tecnico.pdf`: es el anexo de Factura
Electrónica 1.9, con 753 páginas. Su tabla local FE 13.3.1 contiene 02/04 y
030–034; no es el catálogo completo de perfiles RADIAN. No se puede inferir
ausencia de un evento RADIAN a partir de esa tabla o de ese anexo de FE.
No se identifica qué copia estaba viendo el usuario; se confirma el contenido
de las dos copias locales.

El SHA-256 del anexo RADIAN coincide con el registrado:
`f7e75b3fdbe93ae3167918f27fde2cbd370a5cffc175b14481793f9c38e7c9cc`.
Los inventarios SHA256SUMS de la caja RADIAN y de FE 1.9 pasan completos.

## Hallazgos documentales

### D1 — Prioridad alta: contenido general sustituido por duplicados de API

`docs/technical-references.md:1`, `docs/models.md:1`, `docs/catalogs.md:1` y
`docs/errors.md:1` empiezan con `# API pública` y repiten la introducción,
cliente y métodos. La duplicación no es únicamente un título incorrecto: se
perdió contenido propio, como fuentes/procedencia, modelos de respuesta,
motivos de notas y clasificación de excepciones.

Se contrastaron las versiones de trabajo con `git show HEAD:<ruta>`: las
versiones anteriores sí tienen esas secciones. Deben recuperarse sus contenidos
útiles y combinarse con las incorporaciones recientes. No hacer un checkout
completo que elimine las nuevas secciones de emisión ni cambios previos.

Impacto: el sitio muestra varias entradas «API pública» en la navegación y no
permite encontrar con confianza modelos, excepciones o referencias.

### D2 — Prioridad alta: la compilación limpia de documentación falla

Comando ejecutado, con salida fuera del proyecto:

```bash
UV_CACHE_DIR=/tmp/radiankore-uv-cache uv run --no-project \
  --with-requirements docs/requirements.txt \
  sphinx-build -E -W --keep-going -b html docs /tmp/radiankore-doc-review
```

Falla con `myst.xref_missing`: la guía de `GetDocumentInfo`, enlace de
`docs/operations/document-info.md:164`, apunta a `catalogs.md#motivos-de-notas`,
sección perdida en D1. La validación incremental anterior no detectó este enlace.
Además, una compilación correcta por sí sola no detectaría la sustitución de
una página por contenido válido pero ajeno a su propósito.

### D3 — Prioridad media: índice de referencias incompleto y poco visible

`docs/references/dian/README.md:126` presenta la incorporación anterior
036–040/044–047 y sus 18 operaciones/20 muestras. Esa sección es válida para
ese subconjunto, pero no ofrece una visión completa de la emisión actual:
faltan la incorporación 035/041/042/048–051, sus catálogos y la matriz por evento.

El mapa detallado de páginas existe en una skill local, no como índice navegable
del proyecto. `docs/conf.py:25` excluye los originales de referencias del sitio,
correctamente; por eso la página pública `technical-references.md` debe servir
de puente con enlaces a procedencia y archivos del repositorio.

### D4 — Prioridad media: resúmenes y ayudas de desarrollo desactualizados

`README.md:78` describe solo las familias de la incorporación anterior, aunque
la tabla inicial anuncia 16 eventos RADIAN. `docs/development.md:15` todavía
describe `models/events/` como entradas y artefactos del mandato, y la guía de
pruebas se concentra en consultas/mandatos. Actualizar estas descripciones y
dar a cada página una responsabilidad propia, sin repetir la tabla del cliente.

### D5 — Prioridad media: ejemplos documentados sin regresión persistente

Los ejemplos se ejecutaron manualmente en la implementación anterior, pero esa
comprobación se hizo mediante scripts temporales y no quedó como prueba de CI.
Un cambio futuro en firmas o imports podría romper ejemplos sin fallar la suite.
Conviene probar los bloques seleccionados de las guías reales con certificado
sintético, transporte simulado y separación explícita entre preparar y enviar.

## Evaluación de la organización Python

La base está organizada de forma adecuada para la librería:

- `models/events/` expresa contratos por familia; `models/responses/` mantiene
  resultados de consulta y envío separados de las entradas.
- Los 42 modelos dataclass de emisión revisados son inmutables, con slots y
  construcción por nombre. El análisis de imports no encontró dependencias de
  `models/` o `catalogs/` hacia XML, transporte, httpx o xmlsec.
- `_soap/events/` separa builders, firma, empaquetado y parsing. `client.py`
  coordina el certificado y el transporte sin una clase de cliente por evento.
- Los catálogos son constantes sin cargar fuentes durante la ejecución. Los
  exports son explícitos, existe `py.typed` y las referencias se excluyen de
  wheel/sdist. No se necesitan dependencias adicionales para estas mejoras.

Hay oportunidades acotadas, sin evidencia de que requieran una reescritura:

| Mejora | Evidencia | Propuesta compatible |
| --- | --- | --- |
| Ubicar comprobaciones financieras compartidas en un módulo neutral | `models/events/economic_rights.py:14` importa `payment_values` desde otra familia | Extraer el helper privado si se acomete la limpieza; conservar contratos y errores públicos de 045/051 |
| Clarificar catálogos de participantes | `catalogs/invoice_events.py:36` define organización y régimen compartidos con RADIAN | Separación interna opcional, preservando exports y rutas existentes con reexportación; no renombrar enums |
| Simplificar ramas del serializer de pago/notificación | `_soap/events/payment_builder.py:86` combina cuatro perfiles con condicionales anidados | Separar funciones privadas de pago y notificación, reutilizando XML común y conservando el dispatcher |
| Reducir concentración de datos de prueba | `tests/conftest.py:387` contiene una factoría grande con todas las familias | Helpers de fixtures por familia y error explícito para variante desconocida; mantener la factoría común de las matrices |
| Hacer visible la omisión del XSD | `tests/conftest.py:672` devuelve `None` si falta el esquema; `tests/test_radian_xml.py:62` lo omite sin un skip de esa comprobación | Exigir referencias en el job de checkout; permitir ausencia explícita solo en pruebas de distribución e informar la cobertura real |

Estas limpiezas son posteriores a las correcciones documentales. No añadir
clases base, protocolos, registros dinámicos ni una API nueva por evento. No
fusionar los tres flujos públicos de emisión: sus contratos actuales son distintos
y la compatibilidad ya está cubierta por pruebas.

## Plan incremental de mejoras

1. **Restaurar la documentación general.** Reconstruir referencias, modelos,
   catálogos y errores desde contenido anterior comprobado, incorporando las
   nuevas familias. Mantener `api.md` como índice de métodos y enlazar desde él
   los contratos específicos. Validar títulos y recuperar anclas existentes.
2. **Publicar una matriz de trazabilidad 030–051.** Incluir fuente FE/RADIAN,
   versión, sección/página, XML oficial, modelo, guía y pruebas. Diferenciar
   02/04 como respuestas de DIAN y 403/443 como operaciones sin muestra propia.
   Incluir los 36 XML de las 16 clases de la API RADIAN común, además de las
   fuentes específicas de 030–034 y 043. No copiar ni alterar los originales.
3. **Actualizar navegación y resúmenes.** Completar el índice de referencias y
   sus enlaces públicos; actualizar README/desarrollo; separar hechos oficiales,
   interpretaciones, discrepancias y validación pendiente en habilitación.
4. **Impedir regresiones documentales.** Build limpio `-E` en CI, comprobación
   de destinos/anclas, presencia de métodos públicos en API y cobertura de la
   matriz de eventos. Persistir las pruebas de ejemplos con datos sintéticos.
   Estos controles complementan Sphinx; no sustituyen la revisión de contenido.
5. **Aplicar limpieza interna limitada.** Solo los cambios de la tabla anterior
   que reduzcan acoplamiento o ramas reales, sin modificar firmas/imports
   existentes, XML, bytes firmados ni reglas por familia. Comparar los XML y
   ejecutar las regresiones, Ruff, mypy y pruebas del wheel.

Aceptación: ninguna página de referencia ocupa el lugar de otra; la navegación
tiene títulos correctos; cada evento 030–051 puede rastrearse hasta sus fuentes y
ejemplos; la compilación limpia pasa; ejemplos verificados en CI; ausencia de
referencias reportada explícitamente; ninguna ruptura de la API o distribución.

## Verificación efectuada en la revisión inicial

- PDF/índice y encabezados de generación y validación de 046–051 comprobados.
- Once ejemplificaciones de esos seis eventos encontradas e inventariadas.
- Hash del PDF y dos inventarios de fuentes correctos.
- Imports de dominio y atributos de dataclasses revisados mediante AST.
- Ruff y mypy pasan. La compilación Sphinx limpia falla por el enlace descrito.
- No se reejecutó la suite completa ni se contactó a DIAN: esta revisión no
  modifica comportamiento. El resultado anterior de 1.909 pruebas no se utiliza
  como evidencia de que la documentación esté completa.

## Resultado de la implementación

Los cinco pasos están completos:

- D1/D2: páginas generales restauradas combinando sus contratos anteriores con
  la emisión nueva; títulos propios, ancla `motivos-de-notas` recuperada y
  compilación limpia `sphinx-build -E -W` sin advertencias. Se comprobaron
  también los títulos de las páginas HTML generadas.
- D3/D4: [mapa público 030–051](../docs/event-reference-map.md), con modelos,
  guías, páginas de ambos anexos, ejemplos y pruebas; índice local de referencias,
  README y desarrollo actualizados. Se distinguen 02/04 y las operaciones sin
  ejemplo propio. Los 25 ejemplos anidados del mandato también se inventarían.
- D5: `tests/test_documentation.py` comprueba identidad de páginas, métodos
  públicos, cobertura de la matriz y conteos de originales;
  `test_documentation_examples.py` ejecuta las diez guías de emisión, con
  certificados sintéticos, verificación de firmas, XSD y MockTransport.
- Helpers de pago en `_payment.py`, catálogos de participantes en `parties.py`
  con reexportaciones compatibles, builder separado para pagos y notificaciones,
  y factorías por familia en `tests/event_factories.py`. Los 72 XML deterministas
  de ambas configuraciones de ambiente conservaron exactamente sus bytes.
- CI exige referencias en el checkout y compila documentación desde cero.
  Las distribuciones usan `--allow-missing-references`; el resumen indica
  expresamente la omisión de XSD. Se verificó que referencias exigidas ausentes
  y opciones contradictorias producen un error de configuración.

Verificación final local con Python 3.13: 1.928 pruebas completas, cobertura del
99 %, Ruff, formato y mypy estrictos correctos; wheel y sdist construidos.
El wheel aislado pasa los imports de CI y 1.881 pruebas, con 47 omisiones por
documentación/fuentes excluidas. Los dos inventarios SHA-256 se verificaron sin
alteraciones. La matriz CI mantiene Python 3.13–3.15; no se ejecutaron localmente
las otras dos versiones. No se contactó a DIAN.
