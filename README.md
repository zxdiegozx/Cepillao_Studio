# Cepillao' Studio — Despliegue en Railway

## Estructura del proyecto

```
gelato_app/
├── app.py                  # UI principal (Streamlit)
├── calculator.py           # Motor de cálculo (sin dependencias)
├── database.py             # Capa de datos SQLite
├── test_calculator.py      # Tests unitarios
├── requirements.txt        # Dependencias Python
├── Procfile                # Comando de arranque para Railway
├── railway.json            # Configuración de build
├── .gitignore              # Archivos a excluir del repo
└── .streamlit/
    └── config.toml         # Configuración de Streamlit
```

---

## Despliegue paso a paso

### 1. Subir el código a GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/cepillao-studio.git
git push -u origin main
```

### 2. Crear proyecto en Railway

1. Ve a [railway.app](https://railway.app) e inicia sesión con GitHub
2. Clic en **New Project → Deploy from GitHub repo**
3. Selecciona tu repositorio `cepillao-studio`
4. Railway detecta automáticamente el `Procfile` y empieza el build

### 3. Añadir volumen persistente para la base de datos

> Este paso es crítico. Sin él, la DB se borra cada vez que Railway reinicia el contenedor.

1. En tu proyecto de Railway, clic en el servicio desplegado
2. Ve a la pestaña **Volumes**
3. Clic en **Add Volume**
4. Configura:
   - **Mount Path:** `/data`
   - **Size:** 1 GB (suficiente para SQLite)
5. Railway añade automáticamente la variable de entorno `RAILWAY_VOLUME_MOUNT_PATH=/data`

La app detecta esta variable y guarda `gelato.db` en `/data/gelato.db`, que persiste entre deploys y reinicios.

### 4. Verificar el despliegue

1. Railway te da una URL pública tipo `cepillao-studio.up.railway.app`
2. Abre la URL — la app debería arrancar en ~30 segundos
3. La primera vez se inicializa la DB con los 69 ingredientes automáticamente

---

## Variables de entorno

Railway gestiona `RAILWAY_VOLUME_MOUNT_PATH` automáticamente al añadir el volumen.
No necesitas configurar ninguna variable adicional.

---

## Desarrollo local

```bash
# Instalar dependencias
pip install -r requirements.txt

# Arrancar la app
streamlit run app.py

# Correr los tests
python test_calculator.py
# o con pytest si está instalado:
pytest test_calculator.py -v
```

---

## Actualizaciones

Cada `git push` a `main` dispara un redeploy automático en Railway.
La base de datos en el volumen **no se toca** durante el redeploy.

```bash
git add .
git commit -m "Descripción del cambio"
git push
```

---

## Solución de problemas

**La app arranca pero la DB está vacía**
→ Verifica que el volumen está montado en `/data` y que `RAILWAY_VOLUME_MOUNT_PATH` está definida en las variables de entorno del servicio.

**Error de puerto**
→ El `Procfile` ya usa `$PORT` automáticamente. Railway inyecta esta variable.

**Build falla**
→ Revisa que `requirements.txt` tiene exactamente los tres paquetes. Railway usa Nixpacks para detectar Python automáticamente.
