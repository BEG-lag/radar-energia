# Fuentes verificadas

Verificación hecha el **17 de noviembre de 2026**, antes de escribir el código, para decidir qué
fuentes oficiales se pueden leer de forma automática, estable y **sin cuentas ni tokens**. Sobre las
que funcionan se construyó el radar; las demás solo se enlazan como "consulta manual".

**Método.** Peticiones `GET` con `curl` y luego con el cliente del proyecto (`httpx`), con un
User-Agent genérico (`radar-energia/1.0 (+https://github.com/BEG-lag/radar-energia)`), tiempo
máximo de 20 a 30 segundos, al menos un segundo entre peticiones al mismo servidor y revisión previa
de `robots.txt`. No se resolvió ningún CAPTCHA, no se creó ninguna cuenta y no se usó ninguna API
que pida token.

**Semáforo.**

- **VERDE**: legible por máquina (JSON o XML), estable, sin cuenta. Se usa de forma automática.
- **AMARILLO**: funciona sin cuenta pero solo como HTML o PDF. Se usa con cautela (lectura mínima
  que falla en silencio) o solo se enlaza.
- **ROJO**: no se puede usar de forma automática (CAPTCHA, `robots.txt`, token o servidor que no
  responde). Se enlaza para consulta manual y nunca se raspa.

## Resumen

| Semáforo | Fuente | Emisor | Uso en el radar |
| --- | --- | --- | --- |
| VERDE | DOF, índice diario por la API de SIDOF (`/notas/{fecha}`) | Segob | Automático: notas de energía por subsector |
| VERDE | Tipo de cambio FIX publicado en el DOF (`/indicadores/158/...`) | Banxico vía DOF | Automático: serie y variación diaria |
| VERDE | Precios de zonas de carga del MDA, servicio web SW-PEND | CENACE | Automático: promedio diario de 6 zonas |
| VERDE | Precios de gasolinas y diésel por estación (XML) | CNE | Automático: mediana nacional diaria, desde el arranque |
| VERDE | Servicio web SW-PML (precios por nodo) | CENACE | Funciona; no se usa (el radar sigue zonas, no nodos) |
| AMARILLO | Archivos de gob.mx: prensa, documentos y artículos de CNE, SENER, ASEA y CENACE | gob.mx | Automático con cautela: título, fecha y liga |
| AMARILLO | Precios máximos de gas LP (PDF semanal) | CNE | Liga automática al PDF vigente, sin extraer cifras |
| ROJO | Índice de referencia de precios de gas natural (IPGN) | CNE | Consulta manual (reCAPTCHA) |
| ROJO | Demanda del Sistema Eléctrico Nacional | CENACE | Consulta manual (sin servicio documentado) |
| ROJO | Precio de la mezcla mexicana de exportación | Pemex | Consulta manual (`robots.txt`, token) |
| ROJO | datos.gob.mx | Gobierno de México | No se usa (HTTP 403 a clientes automáticos) |
| ROJO | Sitio anterior de la CRE (`www.cre.gob.mx`) | CRE | No responde (el dominio no resuelve) |
| ROJO | Consultas públicas de CONAMER (`cofemersimir.gob.mx`) | CONAMER | No responde (el dominio no resuelve) |

## Detalle por fuente

### VERDE · Diario Oficial de la Federación (API de SIDOF)

- **Endpoint:** `https://sidof.segob.gob.mx/dof/sidof/notas/{DD-MM-YYYY}`. Documentado (de forma no
  oficial) en [mcp-dof/docs/api.md](https://github.com/BEG-lag/mcp-dof/blob/main/docs/api.md).
- **Prueba:** `notas/17-11-2026` respondió HTTP 200, 83 KB, en 0.28 s. El respaldo de 90 días (del 20
  de agosto al 17 de noviembre de 2026) hizo 90 peticiones sin una sola falla: 62 días con edición,
  1,122 notas con título revisadas (sin contar avisos judiciales y generales) y 79 notas de energía.
- **robots.txt:** solo bloquea `/CopiasCert?` y algunas notas puntuales; la API no está restringida.
- **Detalles que importan:** con `Accept: application/json` a secas responde 406 (se manda `*/*`).
  Los días sin edición responden 200 con listas vacías. Las notas de la CNE aparecen con emisor
  "SECRETARIA DE ENERGIA", porque la CNE es órgano desconcentrado de la SENER; el clasificador lo
  corrige a partir del título.
- **Decisión:** se usa. Liga de cada nota: `https://dof.gob.mx/nota_detalle.php?codigo=...`.

### VERDE · Tipo de cambio FIX (indicadores de SIDOF)

- **Endpoint:** `https://sidof.segob.gob.mx/dof/sidof/indicadores/158/{inicio}/{fin}`.
- **Prueba:** del 1 de agosto al 17 de noviembre de 2026 regresó 74 valores; el del 17 de noviembre
  es 18.5525. Es el FIX que determinó Banco de México el día hábil anterior y que el DOF publica.
- **Decisión:** se usa. La API SIE de Banxico pide token, así que no se usa.

### VERDE · Precios de zonas de carga del MDA (CENACE, SW-PEND)

- **Endpoint:** `https://ws01.cenace.gob.mx:8082/SWPEND/SIM/{sistema}/MDA/{zonas}/{aaaa/mm/dd}/{aaaa/mm/dd}/JSON`.
- **Prueba:** sin registro. Respuesta JSON en 0.3 s con un valor por hora (`pz`, `pz_ene`, `pz_per`,
  `pz_cng`). El MDA del día siguiente ya está disponible la tarde anterior.
- **Límites verificados:** máximo 7 días por consulta (con 9 días responde HTTP 400 y el mensaje
  "No se pueden mostrar datos con un lapso mayor a 7 dias"); las zonas con espacio en el nombre
  (por ejemplo `VDM CENTRO`, `LA PAZ`) regresan vacías porque el servicio no decodifica `%20`, así que
  el radar sigue zonas sin espacios: Monterrey, Guadalajara, Puebla, Mérida y Hermosillo (SIN) y
  Mexicali (BCA). El respaldo trajo los 90 días completos de las 6 zonas.
- **robots.txt:** el servidor no publica uno (404).
- **Decisión:** se usa. El radar guarda el promedio simple, el mínimo y el máximo de las 24 horas.

### VERDE · Precios de gasolinas y diésel por estación (CNE)

- **Página oficial:** <https://www.cne.gob.mx/ConsultaPrecios/GasolinasyDiesel/GasolinasyDiesel.html>,
  que ofrece la descarga directa del XML y dice que se actualiza "diariamente a las 18:00 hrs".
- **Endpoint:** `https://publicacionexterna.azurewebsites.net/publicaciones/prices` (el mismo que usaba
  la CRE). La descarga es una liga normal; el reCAPTCHA de esa página solo protege la consulta por
  municipio, que el radar no usa.
- **Prueba:** 15,377 estaciones; 13,780 precios de regular, 12,981 de premium y 10,608 de diésel
  dentro del rango plausible. Algunas estaciones reportan 0.01 como marcador; se excluyen los valores
  fuera de 5 a 60 pesos por litro y se cuentan como excluidos.
- **Limitación:** el XML no trae fecha ni histórico. La serie del radar empieza el 17 de noviembre de
  2026 y crece un punto por día.
- **Decisión:** se usa (mediana, media, percentiles 10 y 90, número de estaciones).

### VERDE · Servicio web SW-PML (CENACE), no usado

- **Endpoint:** `https://ws01.cenace.gob.mx:8082/SWPML/SIM/SIN/MDA/{nodos}/...`. Funciona sin registro
  (se probó con los nodos `01PLO-115` y `01ANS-85`). No se usa porque para un radar general son más
  útiles las zonas de carga.

### AMARILLO · Archivos de gob.mx (CNE, SENER, ASEA, CENACE)

- **Páginas:** `https://www.gob.mx/{cne|sener|asea|cenace}/es/archivo/{prensa|documentos|articulos}?order=DESC&page=N`.
- **Prueba:** todas respondieron 200. No hay RSS ni JSON: las variantes `.rss`, `.atom` y `.json`
  responden HTTP 500. Con `Accept: */*` el archivo regresa un envoltorio de JavaScript; con
  `Accept: text/html` regresa la página. Todas las dependencias usan la misma plantilla: cada entrada
  es un `<article>` con `<time>`, `<h2>` y una liga.
- **robots.txt:** solo menciona a los robots de Google con `Disallow` vacío; no restringe a otros.
- **Observaciones:** la SENER casi no usa "prensa" (la entrada más reciente es del 17 de marzo de
  2026); publica en "artículos". El archivo de prensa del CENACE tiene poca actividad (última entrada
  del 3 de junio de 2026). La CNE publica cada mes "Sesión del mes de ..." con los PDF de las
  resoluciones aprobadas y, por separado, las actas.
- **Resoluciones y acuerdos:** los de carácter general salen en el DOF y el radar los toma de ahí. Las
  resoluciones particulares de la CNE están en los PDF de cada sesión; el radar enlaza la página de
  la sesión, no lee los PDF.
- **Decisión:** se usa con cautela: solo título, fecha y liga; si la plantilla cambia, el radar deja de
  encontrar entradas en lugar de inventarlas. Se excluyen páginas administrativas (avisos de
  privacidad, bienes muebles, comités de ética). El respaldo encontró 37 entradas en 90 días.

### AMARILLO · Precios máximos de gas LP (CNE)

- **Página:** <https://www.gob.mx/cne/documentos/precios-maximos-aplicables-de-gas-lp-399897>, con un PDF
  por semana (76 listados al 17 de noviembre de 2026; el vigente es "PRECIOS MÁXIMOS VIGENTES DEL 15
  AL 21 DE NOVIEMBRE DE 2026").
- **Decisión:** el radar enlaza el PDF más reciente con su título oficial y sus fechas de vigencia. No
  extrae cifras de las tablas en PDF.

### ROJO · Índice de referencia de precios de gas natural (IPGN, CNE)

- **Página:** <https://www.cne.gob.mx/IPGN/>. La tabla se llena con una consulta protegida por
  reCAPTCHA. La página llama a una API interna, pero usarla directamente sería saltarse el CAPTCHA,
  así que el radar no la usa. La búsqueda web encontró un histórico 2017 a 2025 en datos.gob.mx,
  pero ese portal rechaza a los clientes automáticos (ver abajo).
- **Decisión:** consulta manual.

### ROJO · Demanda del Sistema Eléctrico Nacional (CENACE)

- **Página:** <https://www.cenace.gob.mx/GraficaDemanda.aspx>. Es una gráfica que se arma con scripts
  internos de la página; no hay servicio web documentado como SW-PML o SW-PEND.
- **Decisión:** consulta manual.

### ROJO · Mezcla mexicana de exportación (Pemex)

- `https://www.pemex.com/robots.txt` tiene `User-agent: *` con `Disallow: /`. La API SIE de Banxico
  pide token y SIDOF no publica este indicador.
- **Decisión:** consulta manual en <https://www.pemex.com/>.

### ROJO · Otras

- **datos.gob.mx:** respondió HTTP 403 ("Access Denied") desde la primera petición.
- **www.cre.gob.mx:** el dominio no resuelve. `gob.mx/cre` redirige a `gob.mx/cre-historico`, cuyo
  archivo termina en marzo de 2025. La CNE es la sucesora de la CRE y la CNH conforme a las leyes
  de energía de 2025.
- **cofemersimir.gob.mx (CONAMER):** el dominio no resuelve. Los avisos de consulta pública de normas
  oficiales mexicanas sí salen en el DOF y el radar los clasifica.

## Reglas de clasificación

El radar no usa inteligencia artificial ni llaves de API. Clasifica títulos oficiales con reglas de
palabras clave públicas, en [`src/radar_energia/rules.py`](../src/radar_energia/rules.py), que
partieron de los filtros de energía e hidrocarburos de
[mcp-dof](https://github.com/BEG-lag/mcp-dof). Cada tarjeta del sitio muestra qué reglas la
incluyeron. Con las reglas de la versión 1.0.0, 79 de 1,122 notas revisadas del DOF en 90 días (7%)
resultaron de energía.

---

Información pública recopilada automáticamente. No constituye asesoría legal. Solo el DOF y las
autoridades emisoras son fuente oficial.
