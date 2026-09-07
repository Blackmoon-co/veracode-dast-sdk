<!-- Traducción de README.md. Mantener sincronizado con la versión en inglés (fuente canónica). -->

# veracode-dast-sdk

[English](README.md) · **Español**

Un SDK de Python reutilizable para la API REST de [Veracode DAST](https://docs.veracode.com/r/DAST_Essentials_and_DAST_Advanced_API).

> **Estado:** Fase 1 MVP (Autenticación, Cliente HTTP, Gestión de Equipos,
> Gestión de Targets, Gestión de Especificaciones de API), Fase 2 (Perfiles
> de Análisis, Perfiles de Scanner, Autenticaciones, Variables de Scanner,
> Gateways ISM) y Fase 3 (Ejecuciones de Análisis) están implementadas. Ver
> [AGENTS.md](AGENTS.md) para la visión, el alcance y el roadmap del proyecto.

## Qué es esto

`veracode-dast-sdk` abstrae la API REST de Veracode DAST detrás de un cliente
de Python tipado y basado en servicios, para consumirlo de la misma forma
desde un script local, un pipeline de CI/CD (Azure DevOps hoy, cualquier otro
mañana) o cualquier otra base de código en Python — sin ninguna dependencia
específica de plataforma incrustada en el SDK.

## Requisitos

- Python 3.11+

## Instalación

```bash
pip install -e ".[dev]"
```

## Autenticación

El SDK lee las credenciales HMAC de Veracode desde variables de entorno:

```bash
export VERACODE_API_KEY_ID="..."
export VERACODE_API_KEY_SECRET="..."
```

---

## Fase 1 — Gestión de Targets

`VeracodeClient` arma un `HttpClient` por cada API REST de Veracode que usa,
y expone un atributo por recurso encima de él:

| Atributo de `VeracodeClient` | API de Veracode                   | Base URL                                          |
| --------------------------- | ---------------------------------- | -------------------------------------------------- |
| `client.teams`               | Admin API                         | `https://api.veracode.com/api/authn/v2`           |
| `client.targets`             | DAST Target Configuration Service | `https://api.veracode.com/dae/api/tcs-api/api/v1` |
| `client.api_specifications`  | DAST Target Configuration Service | `https://api.veracode.com/dae/api/tcs-api/api/v1` |

- **Gestión de Equipos** (`client.teams`) — consulta de solo lectura, para
  resolver un nombre de equipo al `team_id` al que se asigna un Target.
- **Gestión de Targets** (`client.targets`) — CRUD de Targets de DAST (la
  aplicación/API escaneada), más los helpers idempotentes
  `ensure`/`update_by_name`/`exists` para pipelines.
- **Gestión de Especificaciones de API** (`client.api_specifications`) —
  sube, obtiene metadata y descarga el archivo OpenAPI (JSON/YAML) o HAR que
  respalda a un Target de tipo `API`. Las colecciones de Postman no se
  aceptan — hay que convertirlas a OpenAPI primero.

### Inicio rápido

```python
from veracode_dast.client import VeracodeClient
from veracode_dast.models.target import TargetCreate, TargetType, ScanType, Protocol

client = VeracodeClient()  # lee VERACODE_API_KEY_ID / VERACODE_API_KEY_SECRET

team = client.teams.get_by_name("Development")

target = client.targets.create(
    TargetCreate(
        name="My API",
        url="api.example.com",
        protocol=Protocol.HTTPS,
        target_type=TargetType.API,
        scan_type=ScanType.QUICK,
        authorized_to_scan=True,
        is_sec_lead_only=False,
        teams=[team.team_id],
        api_specification_file_url="https://example.com/openapi.yaml",
    )
)

client.api_specifications.upload(target.target_id, "openapi.yaml")
spec = client.api_specifications.get(target.target_id)
```

### Uso en pipelines: aprovisionamiento idempotente

Para pipelines de CI/CD que corren en cada despliegue, prefiere los métodos
idempotentes `ensure`/`update_by_name`/`delete` sobre `create`/`get` — se
basan en el `name` único del target en vez de un `target_id` que el pipeline
tendría que persistir entre corridas:

```python
target = client.targets.ensure(TargetCreate(name="My API", ...))  # get-or-create, nunca actualiza
client.targets.update_by_name("My API", TargetUpdate(description="Deployed by CI"))
client.targets.delete(target.target_id)  # teardown, p. ej. al destruir un entorno
```

`ensure()` nunca actualiza los campos de un target existente — solo crea
cuando no existe. Usa `update_by_name()` explícitamente cuando un pipeline
necesita cambiar la configuración de un target ya aprovisionado.

### Target de API cuando solo tienes un OpenAPI local

Crear un Target de tipo `API` requiere `api_specification_file_url`, y
Veracode **descarga y parsea esa URL de forma síncrona mientras crea el
target**. Una URL fabricada o inalcanzable hace fallar toda la llamada
`create()` con un `502` de Cloudflare (`origin_bad_gateway`) — no un error
de validación limpio. Es decir, no puedes crear un target de API apuntando
a la URL de tu propia aplicación cuando esa URL no sirve una especificación.

`api_specifications.upload()` (`POST /targets/{id}/spec`) **reemplaza por
completo** lo que descargó `create()`: después, `api_spec_url` queda en
`null`, `api_spec_name` es el nombre del archivo subido, y el alcance del
escaneo se regenera a partir del documento subido (verificado contra la API
en vivo, 2026-09-07).

Entonces, cuando tu especificación solo existe como archivo local, crea el
target con cualquier OpenAPI público siempre alcanzable como *bootstrap*
desechable, y luego sube el archivo real encima — nada tuyo necesita estar
hospedado:

```python
BOOTSTRAP = "https://petstore3.swagger.io/api/v3/openapi.json"  # o tu propia spec siempre disponible

target = client.targets.ensure(
    TargetCreate(
        name="client-api-1",
        url="api.client.com",              # el host real a escanear; no necesita servir una spec
        protocol=Protocol.HTTPS,
        target_type=TargetType.API,
        scan_type=ScanType.ENTERPRISE,
        authorized_to_scan=True,
        is_sec_lead_only=False,
        teams=[team.team_id],
        api_specification_file_url=BOOTSTRAP,   # solo tiene que ser alcanzable durante create()
    )
)
client.api_specifications.upload(target.target_id, "client-openapi.json")  # reemplaza el bootstrap
assert client.api_specifications.get(target.target_id).api_spec_url is None
```

Una colección de Postman **no** es un formato de especificación aceptado —
conviértela primero (`npx postman-to-openapi collection.json -o openapi.yaml`)
o captura un HAR.

La versión ejecutable es
[`scan_api_with_local_openapi_example.py`](examples/scan_api_with_local_openapi_example.py)
(`--bootstrap-spec-url` sobreescribe el valor por defecto).
`end_to_end_workflow_example.py` hace lo mismo cuando se omite su flag
`--spec-url`.

### Ejemplos de la Fase 1

Scripts ejecutables en [examples/](examples/). Cada uno requiere
`VERACODE_API_KEY_ID` / `VERACODE_API_KEY_SECRET`:

| Script | Qué muestra |
| --- | --- |
| [`auth_example.py`](examples/auth_example.py) | Construye el proveedor de auth HMAC desde el entorno. |
| [`http_client_example.py`](examples/http_client_example.py) | Un `GET` autenticado crudo vía `HttpClient`, sin modelos tipados. |
| [`team_management_example.py`](examples/team_management_example.py) | Resuelve un Equipo por nombre a su `team_id`. |
| [`target_management_example.py`](examples/target_management_example.py) | Ciclo de vida completo del Target: `ensure` → `update_by_name` → `delete`. |
| [`api_specification_management_example.py`](examples/api_specification_management_example.py) | Sube, obtiene metadata y descarga una Especificación de API de un Target existente. |
| [`scan_api_with_local_openapi_example.py`](examples/scan_api_with_local_openapi_example.py) | Crea un target de API cuya URL real no sirve un OpenAPI, usando solo un archivo de spec local (URL bootstrap + `upload()`). |
| [`end_to_end_workflow_example.py`](examples/end_to_end_workflow_example.py) | El flujo completo de la Fase 1 en un script: resolver un Equipo, `ensure`/actualizar un Target, subir su spec, leer la spec de vuelta — salida en JSON. |

```bash
python examples/end_to_end_workflow_example.py \
  --team-name "Development" --target-name "My API" \
  --target-url api.example.com --spec-file examples/sample-openapi.yaml \
  --target-type API --scan-type ENTERPRISE

# Target de API cuando la spec solo existe localmente (la URL real no sirve un OpenAPI):
python examples/scan_api_with_local_openapi_example.py \
  --team-name "Development" --target-name "client-api-1" \
  --target-url api.client.com --spec-file ./client-openapi.json
```

---

## Fase 2 — Configuración del Escaneo

Una vez que existe un Target, la Fase 2 configura cómo se escanea realmente:
ajustes de crawl/escaneo, qué scanners de seguridad corren, cómo se autentica
Veracode contra la aplicación objetivo, credenciales de runtime y (para apps
hospedadas privadamente) el gateway de Internal Scanning Management usado para
alcanzarla.

| Atributo de `VeracodeClient` | API de Veracode                  | Base URL                                          |
| --------------------------- | ---------------------------------- | -------------------------------------------------- |
| `client.analysis_profiles`  | DAST Target Configuration Service | `https://api.veracode.com/dae/api/tcs-api/api/v1` |
| `client.scanners`            | DAST Target Configuration Service | `https://api.veracode.com/dae/api/tcs-api/api/v1` |
| `client.authentications`     | DAST Target Configuration Service | `https://api.veracode.com/dae/api/tcs-api/api/v1` |
| `client.scanner_variables`   | DAST Target Configuration Service | `https://api.veracode.com/dae/api/tcs-api/api/v1` |
| `client.ism_gateways`        | DAST Target Configuration Service | `https://api.veracode.com/dae/api/tcs-api/api/v1` |

- **Perfiles de Análisis** (`client.analysis_profiles`) — el recurso raíz de
  configuración del escaneo DAST: `list`/`get`/`update` de los ajustes de
  crawl y escaneo de un Perfil de Análisis. Todos los demás recursos de la
  Fase 2 se direccionan por el `analysis_profile_id` que este servicio
  resuelve.
- **Perfiles de Scanner** (`client.scanners`) — habilita/deshabilita
  scanners de seguridad DAST individuales en un Perfil de Análisis, usando
  un pequeño documento de Configuración del SDK en vez del modelo de request
  crudo de Veracode.
- **Autenticaciones** (`client.authentications`) — configura cómo se
  autentica Veracode contra la aplicación objetivo (HTTP Basic, basada en
  formulario, certificado de cliente, scripts de login/logout, Scriptable
  Request Modification, OAuth 2.0 o Parameter Authentication), un mecanismo
  por llamada a `update()` vía un documento de Configuración del SDK.
- **Variables de Scanner** (`client.scanner_variables`) — valores de runtime
  (credenciales, semillas TOTP, tokens) que los mecanismos de autenticación
  referencian por nombre. `update()` reemplaza la lista *completa* — ver la
  advertencia abajo.
- **Gateways ISM** (`client.ism_gateways`) — asigna, cambia o quita el
  gateway de Internal Scanning Management que un Target usa para alcanzar una
  aplicación hospedada privadamente, por nombre de gateway (nunca un ID crudo).

### Configurar Targets

Resuelve el Perfil de Análisis del Target y configura el escaneo mediante
archivos JSON de Configuración del SDK, pequeños y versionables, en vez de
los modelos de request crudos de la API de Veracode:

```python
profile = client.analysis_profiles.get(analysis_profile_id)

client.scanners.update(analysis_profile_id, config_file="scanner-profile.json")
client.authentications.update(analysis_profile_id, config_file="authentication.json")
client.scanner_variables.update(analysis_profile_id, config_file="scanner-variables.json")
client.ism_gateways.update(target.target_id, gateway_name="Corporate Gateway")
```

Cada llamada a `update()`: carga la configuración (ruta o `dict` en memoria),
la valida localmente (nombres desconocidos de scanner/tipo-de-autenticación
lanzan error antes de cualquier llamada HTTP, con una sugerencia de "¿quisiste
decir...?" cuando aplica), la transforma en el request correspondiente de la
API de Veracode, y devuelve el estado actualizado del servidor como un modelo
tipado.

Los archivos de configuración de ejemplo viven junto a la spec de cada
funcionalidad:
[`specs/scanners-profiles/scanner-profile.json`](specs/scanners-profiles/scanner-profile.json),
[`specs/authentications/authentication.json`](specs/authentications/authentication.json),
[`specs/scanner-variables/scanner-variables.json`](specs/scanner-variables/scanner-variables.json),
[`specs/ism-gateway/ism-gateway.json`](specs/ism-gateway/ism-gateway.json).

**La autenticación Scriptable Request Modification (SRM) toma su script como
base64, no como una ruta de archivo.** El mecanismo `"srm"` de
`authentication.json` (y los `login_script`/`logout_script` de `"script"`)
tiene un campo `script_body`, pero el formato de Configuración del SDK nunca
acepta una ruta a un archivo `.js` ahí — debes leer el archivo del script tú
mismo y codificar su contenido en base64 dentro del JSON antes de llamar a
`update()`:

```python
import base64, json

with open("srm-script.js", "rb") as f:
    script_body = base64.b64encode(f.read()).decode("ascii")

config = {
    "authentication": {
        "type": "srm",
        "script_name": "srm-script.js",
        "script_type": "JAVASCRIPT",
        "script_body": script_body,
    }
}
client.authentications.update(analysis_profile_id, config_file=config)  # el dict funciona, sin archivo
```

Ver [`specs/authentications/authentication-srm.json`](specs/authentications/authentication-srm.json)
para un ejemplo ya codificado, construido a partir de
[`specs/authentications/srm-script-example.js`](specs/authentications/srm-script-example.js).

**El `update()` de Variables de Scanner es un reemplazo total, no un merge.**
A diferencia de los Perfiles de Scanner (que solo tocan los scanners que
listas), llamar a `client.scanner_variables.update(...)` envía la lista
*completa* deseada — cualquier variable existente cuyo `reference_key` falte
en tu configuración se elimina. Un pipeline que quiera agregar una variable
sin alterar las demás debe hacer `get()` primero, agregar a `.variables`, y
pasar la lista completa de vuelta a `update()`.

**Las Variables de Scanner son parte de la Autenticación, no un concepto
aparte.** No hacen nada por sí solas — son los valores de runtime (usuario,
contraseña, semilla TOTP) que el script de login o el paso de MFA de un
mecanismo de Autenticación busca por `reference_key`. No hay un flag de
"activo/inactivo" en una Variable de Scanner; sus únicos estados son
"presente en la lista" (usable por la Autenticación) o "ausente" (eliminada).
Configura `client.authentications` primero para definir *cómo* entra Veracode,
y luego `client.scanner_variables` para proveer los *valores* que ese login
referencia.

`client.ism_gateways` y `client.api_specifications` toman `target_id`, no
`analysis_profile_id` — resuélvelo vía
`client.analysis_profiles.get(analysis_profile_id).target_id`, o usa el
`target_id` que ya devuelve `client.targets.ensure(...)`.

**No todos los scanners son editables.** Qué scanners expone un Target, y si
cada uno se puede cambiar, depende de su `scan_type`/`target_type` —
confirmado en vivo contra dos cuentas:

- Target QUICK/WEB_APP: solo `fingerprinting`, `http_header`, `portscan` y
  `ssl` eran editables; scanners como `sql_injection`, `xss` y `csrf`
  volvieron con `editable=False` y rechazaron el update con un 400.
- Target ENTERPRISE/API: lo opuesto — 32 de 34 scanners eran editables;
  solo `fuzzer` y `file_dir_exposure` volvieron con `editable=False`.
  `privilege_escalation` no apareció en la lista de scanners del perfil en
  absoluto — incluirlo en una llamada a `update()` falla, no porque sea no
  editable, sino porque no aplica a ese perfil.

Enviar un scanner que Veracode rechaza hace fallar la llamada `update()`
*completa*, aunque todos los demás scanners del mismo request sean válidos.
Revisa el campo `editable` de cada `Scanner` de `client.scanners.get(...)`
antes de llamar a `update()`, en vez de asumir una lista fija.

### Ejemplos de la Fase 2

Scripts ejecutables en [examples/](examples/). Cada uno requiere
`VERACODE_API_KEY_ID` / `VERACODE_API_KEY_SECRET`:

| Script | Qué muestra |
| --- | --- |
| [`analysis_profiles_example.py`](examples/analysis_profiles_example.py) | Obtiene la configuración de crawl/escaneo de un Perfil de Análisis, y luego actualiza campos seleccionados. |
| [`scanner_profiles_example.py`](examples/scanner_profiles_example.py) | Obtiene, y luego actualiza, los scanners habilitados de un Perfil de Análisis desde un archivo de Configuración del SDK. |
| [`authentications_example.py`](examples/authentications_example.py) | Obtiene la configuración efectiva de Autenticación, y luego configura un mecanismo desde un archivo de Configuración del SDK. |
| [`scanner_variables_example.py`](examples/scanner_variables_example.py) | Obtiene, y luego reemplaza, las Variables de Scanner de un Perfil de Análisis desde un archivo de Configuración del SDK. |
| [`ism_gateway_example.py`](examples/ism_gateway_example.py) | Lista los Gateways ISM disponibles, asigna uno a un Target por nombre, y luego quita la asignación. |

---

## Fase 3 — Ejecutar Escaneos

Una vez que un Target está configurado (Fase 2), la Fase 3 corre el escaneo
en sí: inicia una Ejecución de Análisis, la monitorea o espera a que
termine, la detiene antes de tiempo si hace falta, y descarga el reporte
resultante.

| Atributo de `VeracodeClient` | API de Veracode                  | Base URL                                          |
| --------------------------- | ---------------------------------- | -------------------------------------------------- |
| `client.analysis_runs`      | DAST Target Configuration Service | `https://api.veracode.com/dae/api/tcs-api/api/v1` |

- **Ejecuciones de Análisis** (`client.analysis_runs`) —
  `start`/`stop`/`list`/`get` de una Ejecución de Análisis para un Target
  existente, `wait_for_completion` para bloquear hasta que alcance un estado
  terminal, y `get_report` para descargar el reporte (PDF, CSV o JUnit) de
  una ejecución específica.

### Correr un escaneo

```python
target = client.targets.get_by_name("My API")

run = client.analysis_runs.start(target.target_id)

finished = client.analysis_runs.wait_for_completion(
    target.target_id, run.analysis_run_id, poll_interval=15, timeout=3600
)
print(finished.status)  # TargetStatus.FINISHED / STOPPED / FAILED

client.analysis_runs.get_report(
    target.target_id, finished.analysis_run_id, "pdf", "scan-report.pdf"
)
```

Los estados terminales de `wait_for_completion()` son `FINISHED`, `STOPPED` y
`FAILED` (`RUNNING`/`STOPPING` lo mantienen haciendo polling). `timeout` es un
límite *suave* — solo se revisa una vez por poll, así que se puede exceder
por hasta aproximadamente un `poll_interval` más una petición HTTP — y lanza
`AnalysisRunTimeoutError` una vez superado.

### Detener un escaneo antes de tiempo

```python
from veracode_dast.models.analysis_run import StopActionType

client.analysis_runs.stop(target.target_id, action=StopActionType.STOP_SAVE)
```

`action` por defecto es `StopActionType.STOP_DELETE` y también acepta un
string plano (`action="STOP_SAVE"`), validado igual que el `format` de
`get_report()`.

### Ejemplos de la Fase 3

Scripts ejecutables en [examples/](examples/). Cada uno requiere
`VERACODE_API_KEY_ID` / `VERACODE_API_KEY_SECRET`:

| Script | Qué muestra |
| --- | --- |
| [`analysis_runs_example.py`](examples/analysis_runs_example.py) | Resuelve un Target por nombre, inicia (o reutiliza) una Ejecución de Análisis, espera a que termine, opcionalmente descarga un reporte, o detiene la ejecución. |

```bash
# Correr un escaneo por nombre de Target (resuelto vía TargetsService.get_by_name)
python examples/analysis_runs_example.py --target-name "sdk-demo"

# Correr un escaneo y descargar un reporte
python examples/analysis_runs_example.py --target-name "sdk-demo" \
  --report pdf --output ./report.pdf

# Correr un escaneo por ID de Target en vez de nombre
python examples/analysis_runs_example.py --target-id <existing-target-id>

# Inspeccionar una Ejecución de Análisis existente en vez de iniciar una nueva
python examples/analysis_runs_example.py --target-name "sdk-demo" \
  --analysis-run-id <existing-run-id>

# Detener una Ejecución de Análisis en curso en vez de esperar a que termine
python examples/analysis_runs_example.py --target-name "sdk-demo" --stop
```

---

## Estructura del proyecto

```
src/veracode_dast/       Código del SDK (layout src)
  services/               Un módulo por recurso de la API (targets, ...)
  models/                 Modelos de datos tipados para los recursos de la API
  utils/                  Helpers pequeños y genéricos (carga de Configuración del SDK)
tests/                    Suite de pruebas (pytest)
examples/                 Ejemplos de uso ejecutables
```

## Documentación

- [AGENTS.md](AGENTS.md) — arquitectura, alcance, convenciones y roadmap.
  Es la fuente de verdad de cómo se construye el proyecto.

## Licencia

MIT
