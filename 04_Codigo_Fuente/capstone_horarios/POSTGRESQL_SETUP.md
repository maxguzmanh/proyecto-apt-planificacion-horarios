# Configuración PostgreSQL - UniPlan

## 1. Motor de base de datos

UniPlan utiliza PostgreSQL como motor de base de datos.

Configuración local utilizada:

- PostgreSQL: 18
- Administrador gráfico: pgAdmin 4
- Base de datos: `uniplan_db`
- Usuario de aplicación: `uniplan_user`
- Host: `localhost`
- Puerto: `5432`

La contraseña de PostgreSQL no se almacena directamente en el código fuente.

---

## 2. Variable de entorno

Dentro de:

`04_Codigo_Fuente/capstone_horarios/`

se utiliza un archivo local `.env`.

Ejemplo:

```env
UNIPLAN_DB_PASSWORD=CONTRASEÑA_LOCAL

y continúa pegando esto debajo:

```md
El archivo `.env` está excluido del repositorio mediante `.gitignore`.

No subir contraseñas a GitHub.

---

## 3. Configuración de Django

Django está configurado para utilizar PostgreSQL desde el archivo:

`config/settings.py`

La conexión utiliza:

- Motor: PostgreSQL
- Base de datos: `uniplan_db`
- Usuario: `uniplan_user`
- Host: `localhost`
- Puerto: `5432`

La contraseña se obtiene desde la variable:

`UNIPLAN_DB_PASSWORD`

No es necesario modificar nuevamente `settings.py`.

---

## 4. Dependencias

Las dependencias necesarias para PostgreSQL están registradas en:

`requirements.txt`

Entre ellas se utilizan:

- `psycopg`
- `psycopg-binary`
- `python-dotenv`

Para instalar las dependencias del proyecto:

```powershell
python -m pip install -r requirements.txt