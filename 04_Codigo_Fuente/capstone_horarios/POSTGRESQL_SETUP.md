# Configuraci?n PostgreSQL - UniPlan

UniPlan utiliza PostgreSQL mediante Django ORM y psycopg. El entorno local
verificado utiliza PostgreSQL 18 y puede administrarse con pgAdmin 4.

## Configuraci?n de entorno

Desde `04_Codigo_Fuente/capstone_horarios/`, configure las siguientes variables
en el entorno o en un archivo local `.env`:

| Variable | Descripci?n | Valor predeterminado |
|---|---|---|
| `DB_NAME` | Nombre de la base PostgreSQL | Sin valor predeterminado |
| `DB_USER` | Usuario autorizado en PostgreSQL | Sin valor predeterminado |
| `DB_PASSWORD` | Contrase?a local del usuario | Sin valor predeterminado |
| `DB_HOST` | Host del servidor | `localhost` |
| `DB_PORT` | Puerto del servidor | `5432` |
| `SECRET_KEY` | Clave secreta de Django, privada y estable | Sin clave fija |

La base del entorno de desarrollo se denomina `uniplan_db`.
`config/settings.py` carga `.env` desde el directorio del proyecto mediante
`python-dotenv`. La configuraci?n integrada utiliza `DB_PASSWORD`, no
`UNIPLAN_DB_PASSWORD`. Adapte las variables del entorno antes de ejecutarla.

No publique contrase?as, claves ni el archivo `.env`; est? excluido por
`.gitignore`. No use credenciales reales como ejemplos en la documentaci?n.

Con `DEBUG=True`, si no se configura `SECRET_KEY`, Django recibe una clave
aleatoria por proceso para desarrollo; las sesiones pueden invalidarse al
reiniciar. Configure una clave privada estable para conservarlas. Con
`DEBUG=False`, la ausencia de `SECRET_KEY` impide iniciar la aplicaci?n.
La configuraci?n actual sigue siendo de desarrollo, no de producci?n.

## Dependencias y comprobaci?n

Las dependencias est?n fijadas en `requirements.txt`, codificado en UTF-8.
Incluyen `psycopg`, `psycopg-binary` y `python-dotenv`.

Desde el directorio del proyecto y con su entorno virtual activo:

```powershell
python -m pip install -r requirements.txt
python manage.py check
python manage.py showmigrations
python manage.py migrate --plan
```

Revise el plan y respalde los datos antes de aplicar migraciones a una base
existente. La migraci?n de sede de horarios requiere poder determinar la sede
de cada registro y rechaza casos sin informaci?n suficiente.
