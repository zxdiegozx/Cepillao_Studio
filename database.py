"""
database.py — Capa de datos con SQLite
Mejoras: WAL mode, DB_DATA como lista de dicts, context managers
"""
import sqlite3
import os

# Railway monta el volumen persistente en la ruta definida por RAILWAY_VOLUME_MOUNT_PATH.
# Si no existe esa variable (desarrollo local), usa el directorio del script.
_DATA_DIR = os.environ.get("RAILWAY_VOLUME_MOUNT_PATH", os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(_DATA_DIR, "gelato.db")

SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS ingredients (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    name      TEXT    UNIQUE NOT NULL,
    category  TEXT    NOT NULL,
    fat       REAL    DEFAULT 0,
    msnf      REAL    DEFAULT 0,
    sugars    REAL    DEFAULT 0,
    other_st  REAL    DEFAULT 0,
    pod       REAL    DEFAULT 0,
    pac       REAL    DEFAULT 0,
    water     REAL    DEFAULT 0,
    notes     TEXT    DEFAULT '',
    function  TEXT    DEFAULT '',
    brix      REAL    DEFAULT 0,
    ph        REAL    DEFAULT 0
);

CREATE TABLE IF NOT EXISTS recipes (
    id            INTEGER  PRIMARY KEY AUTOINCREMENT,
    name          TEXT     NOT NULL,
    product_type  TEXT     DEFAULT 'Helado/Gelato',
    machine       TEXT     DEFAULT 'Pacojet',
    base_grams    REAL     DEFAULT 1000,
    notes         TEXT     DEFAULT '',
    tasting_notes TEXT     DEFAULT '',
    cost_total    REAL     DEFAULT 0,
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS recipe_lines (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    recipe_id       INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    ingredient_id   INTEGER REFERENCES ingredients(id),
    ingredient_name TEXT    NOT NULL,
    grams           REAL    NOT NULL,
    price_per_kg    REAL    DEFAULT 0,
    sort_order      INTEGER DEFAULT 0
);
"""

# ── SEED DATA como lista de dicts — legible y a prueba de reordenación ────────
DB_DATA = [
    # ── Lácteos ───────────────────────────────────────────────────────────────
    dict(name="Leche entera 3.5%",       category="Lácteo",            fat=3.5,  msnf=9.0,  sugars=4.7,  other_st=0.0,  pod=0.10, pac=0.10, water=82.8, brix=0,  ph=6.6, function="Base principal",           notes="Emulsión O/W natural, lactosa 4.7%, pH 6.6"),
    dict(name="Leche descremada 0.1%",   category="Lácteo",            fat=0.1,  msnf=9.5,  sugars=4.8,  other_st=0.0,  pod=0.10, pac=0.10, water=85.6, brix=0,  ph=6.6, function="Base baja grasa",          notes="Alta MSNF sin grasa"),
    dict(name="Leche concentrada s/a",   category="Lácteo",            fat=7.5,  msnf=20.0, sugars=11.0, other_st=0.0,  pod=0.22, pac=0.22, water=61.5, brix=0,  ph=6.5, function="Aumentar sólidos lácteos", notes="MSNF concentrado 2.5x"),
    dict(name="Crema 35% MG",            category="Lácteo",            fat=35.0, msnf=6.0,  sugars=3.5,  other_st=0.0,  pod=0.04, pac=0.04, water=55.5, brix=0,  ph=6.5, function="Fuente grasa primaria",    notes="Globos grasos 3-8µm, pasteurizar 85°C/15s"),
    dict(name="Crema 45% MG",            category="Lácteo",            fat=45.0, msnf=4.5,  sugars=2.8,  other_st=0.0,  pod=0.03, pac=0.03, water=47.7, brix=0,  ph=6.5, function="Grasa máxima",             notes="Ultra-grasa, semifreddo"),
    dict(name="Leche en polvo entera",   category="Lácteo",            fat=26.0, msnf=38.0, sugars=37.5, other_st=0.0,  pod=0.38, pac=0.38, water=1.0,  brix=0,  ph=6.8, function="Concentrar MSNF+ST",       notes="Higroscópica, añadir al final"),
    dict(name="Leche en polvo descremada",category="Lácteo",           fat=1.0,  msnf=52.0, sugars=50.0, other_st=0.0,  pod=0.50, pac=0.50, water=3.0,  brix=0,  ph=6.8, function="Aumentar MSNF sin grasa",  notes="Proteínas 34%, lactosa 50%"),
    dict(name="Mantequilla 82% MG",      category="Lácteo",            fat=82.0, msnf=1.5,  sugars=0.6,  other_st=0.0,  pod=0.01, pac=0.01, water=15.9, brix=0,  ph=6.5, function="Ajuste fino grasa",        notes="Cristalización Form β'"),
    dict(name="Mascarpone 41% MG",       category="Lácteo",            fat=41.0, msnf=5.0,  sugars=3.5,  other_st=0.0,  pod=0.04, pac=0.04, water=50.5, brix=0,  ph=5.5, function="Gelato ricco",             notes="Ácido cítrico, pH 5.5"),
    dict(name="Queso crema 30% MG",      category="Lácteo",            fat=30.0, msnf=8.0,  sugars=3.8,  other_st=0.0,  pod=0.04, pac=0.04, water=58.2, brix=0,  ph=4.8, function="Textura densa",            notes="Philadelphia-style, pH 4.5-5.0"),
    dict(name="Yogur entero 3.5%",       category="Lácteo",            fat=3.5,  msnf=9.0,  sugars=4.7,  other_st=0.0,  pod=0.10, pac=0.10, water=82.8, brix=0,  ph=4.2, function="Acidez, frescura",         notes="Ácido láctico, pH 4.0-4.5"),
    dict(name="Suero de leche (whey)",   category="Lácteo",            fat=0.3,  msnf=10.0, sugars=5.0,  other_st=0.0,  pod=0.10, pac=0.10, water=84.7, brix=0,  ph=6.5, function="Estructura proteica",      notes="Proteínas WPC, funcional"),
    # ── Azúcares ─────────────────────────────────────────────────────────────
    dict(name="Sacarosa",                category="Azúcar",            fat=0.0,  msnf=0.0,  sugars=100.0,other_st=0.0,  pod=1.00, pac=1.00, water=0.0,  brix=0,  ph=7.0, function="Base de dulzor",           notes="Referencia absoluta POD=PAC=1.0"),
    dict(name="Dextrosa monohidrato",    category="Azúcar",            fat=0.0,  msnf=0.0,  sugars=91.0, other_st=0.0,  pod=0.75, pac=1.90, water=9.0,  brix=0,  ph=7.0, function="Bajar punto congelación",  notes="MW=198, PAC=1.9x! Crioscópica potente"),
    dict(name="Glucosa atomizada DE40",  category="Azúcar",            fat=0.0,  msnf=0.0,  sugars=95.0, other_st=0.0,  pod=0.50, pac=0.64, water=5.0,  brix=0,  ph=7.0, function="Textura, anti-cristal",    notes="Antirecristalizante, sinergia con sacarosa"),
    dict(name="Glucosa atomizada DE60",  category="Azúcar",            fat=0.0,  msnf=0.0,  sugars=95.0, other_st=0.0,  pod=0.70, pac=0.90, water=5.0,  brix=0,  ph=7.0, function="Balance dulzor/textura",   notes="Mayor dulzor que DE40"),
    dict(name="Fructosa",                category="Azúcar",            fat=0.0,  msnf=0.0,  sugars=99.5, other_st=0.0,  pod=1.20, pac=1.90, water=0.5,  brix=0,  ph=7.0, function="Dulzor potenciado",        notes="POD>sacarosa en frío, ideal sorbetes"),
    dict(name="Trehalosa",               category="Azúcar",            fat=0.0,  msnf=0.0,  sugars=99.5, other_st=0.0,  pod=0.45, pac=0.70, water=0.5,  brix=0,  ph=7.0, function="Estabilidad, Pacojet",     notes="Protege proteínas y membranas celulares"),
    dict(name="Isomalt",                 category="Azúcar",            fat=0.0,  msnf=0.0,  sugars=98.5, other_st=0.0,  pod=0.45, pac=0.70, water=1.5,  brix=0,  ph=7.0, function="Reducir azúcar",           notes="0 caries, bajo IG"),
    dict(name="Azúcar invertido",        category="Azúcar",            fat=0.0,  msnf=0.0,  sugars=75.0, other_st=0.0,  pod=1.30, pac=1.90, water=25.0, brix=0,  ph=7.0, function="Antirecristalizante",      notes="Fructosa+glucosa libres, higroscópico"),
    dict(name="Miel de abeja",           category="Azúcar",            fat=0.0,  msnf=0.0,  sugars=80.0, other_st=1.0,  pod=1.00, pac=1.50, water=19.0, brix=0,  ph=3.9, function="Dulzor floral",            notes="Fructosa+glucosa 70%, polifenoles"),
    dict(name="Eritritol",               category="Azúcar",            fat=0.0,  msnf=0.0,  sugars=99.5, other_st=0.0,  pod=0.65, pac=1.30, water=0.5,  brix=0,  ph=7.0, function="Low-calorie",              notes="0 cal, buen PAC, refrescante"),
    # ── Fruta tropical ───────────────────────────────────────────────────────
    dict(name="Mango Ataulfo (pulpa)",   category="Fruta tropical",    fat=0.4,  msnf=0.0,  sugars=14.0, other_st=0.8,  pod=0.14, pac=0.20, water=84.8, brix=20, ph=3.9, function="Sorbete tropical",         notes="Brix 18-22°, pH 3.9, β-caroteno"),
    dict(name="Maracuyá (pulpa)",        category="Fruta tropical",    fat=0.4,  msnf=0.0,  sugars=11.0, other_st=1.5,  pod=0.11, pac=0.16, water=87.1, brix=15, ph=3.1, function="Sorbete limpio",           notes="Filtrada sin semilla, Brix 14-16°"),
    dict(name="Guanábana (pulpa)",       category="Fruta tropical",    fat=0.3,  msnf=0.0,  sugars=13.5, other_st=3.5,  pod=0.14, pac=0.16, water=82.7, brix=14, ph=3.5, function="Sorbete cremoso vegano",   notes="Fibra 3.5%, pH 3.5, untuosa"),
    dict(name="Piña Golden (pulpa)",     category="Fruta tropical",    fat=0.2,  msnf=0.0,  sugars=16.0, other_st=0.7,  pod=0.16, pac=0.22, water=83.1, brix=15, ph=3.5, function="Sorbete refrescante",      notes="Bromelina activa, tamizar"),
    dict(name="Banana madura (pulpa)",   category="Fruta tropical",    fat=0.3,  msnf=0.0,  sugars=17.0, other_st=2.8,  pod=0.17, pac=0.22, water=79.9, brix=18, ph=4.8, function="Cuerpo, dulzor natural",   notes="Almidón→azúcar, pectina"),
    dict(name="Leche de coco 17-18%",   category="Fruta tropical",    fat=17.5, msnf=0.0,  sugars=3.8,  other_st=1.5,  pod=0.04, pac=0.05, water=77.2, brix=0,  ph=6.5, function="Base gelato vegano",       notes="Emulsión natural, ácido láurico"),
    dict(name="Crema de coco 22-24%",   category="Fruta tropical",    fat=23.0, msnf=0.0,  sugars=4.0,  other_st=2.0,  pod=0.04, pac=0.06, water=71.0, brix=0,  ph=6.5, function="Gelato vegano premium",    notes="Ultra-grasa vegetal"),
    dict(name="Aguacate (pulpa)",        category="Fruta tropical",    fat=15.0, msnf=0.0,  sugars=0.7,  other_st=3.0,  pod=0.01, pac=0.01, water=81.3, brix=0,  ph=6.3, function="Gelato vegano untuoso",    notes="66% MG monoins., cremosidad"),
    dict(name="Tamarindo (pulpa)",       category="Fruta tropical",    fat=0.6,  msnf=0.0,  sugars=38.0, other_st=5.5,  pod=0.38, pac=0.55, water=55.9, brix=55, ph=3.0, function="Sorbete agridulce",        notes="Muy dulce+ácido, ácido tartárico"),
    dict(name="Lichi (pulpa)",           category="Fruta tropical",    fat=0.4,  msnf=0.0,  sugars=16.0, other_st=0.5,  pod=0.16, pac=0.22, water=83.1, brix=16, ph=4.1, function="Sorbete floral",           notes="Aroma floral, pH 4.1"),
    dict(name="Papaya (pulpa)",          category="Fruta tropical",    fat=0.3,  msnf=0.0,  sugars=8.3,  other_st=0.9,  pod=0.08, pac=0.11, water=90.5, brix=9,  ph=5.8, function="Sorbete suave",            notes="Papaína activa, β-caroteno"),
    # ── Fruta europea ────────────────────────────────────────────────────────
    dict(name="Fresa (pulpa fresca)",    category="Fruta europea",     fat=0.3,  msnf=0.0,  sugars=7.7,  other_st=0.5,  pod=0.08, pac=0.11, water=91.5, brix=9,  ph=3.2, function="Sorbete clásico",          notes="Antocianos, pH 3.0-3.5, Brix 8-11°"),
    dict(name="Frambuesa (pulpa)",       category="Fruta europea",     fat=0.7,  msnf=0.0,  sugars=5.4,  other_st=2.8,  pod=0.05, pac=0.07, water=91.1, brix=7,  ph=3.0, function="Sorbete intenso",          notes="Muy ácida pH 2.8-3.2"),
    dict(name="Arándano (blueberry)",    category="Fruta europea",     fat=0.3,  msnf=0.0,  sugars=10.0, other_st=0.8,  pod=0.10, pac=0.14, water=88.9, brix=11, ph=3.2, function="Sorbete antioxidante",     notes="Antocianos altos, pH 3.1-3.3"),
    dict(name="Mora (blackberry)",       category="Fruta europea",     fat=0.5,  msnf=0.0,  sugars=9.6,  other_st=2.2,  pod=0.10, pac=0.13, water=87.7, brix=10, ph=3.2, function="Sorbete oscuro",           notes="Antocianos, pepitas→tamizar"),
    dict(name="Cereza dulce (pulpa)",    category="Fruta europea",     fat=0.2,  msnf=0.0,  sugars=12.8, other_st=0.5,  pod=0.13, pac=0.18, water=86.5, brix=17, ph=4.0, function="Sorbete suave",            notes="Brix 15-19°, pH 3.8-4.2"),
    dict(name="Durazno/Melocotón",       category="Fruta europea",     fat=0.3,  msnf=0.0,  sugars=9.5,  other_st=0.8,  pod=0.10, pac=0.13, water=89.4, brix=10, ph=3.7, function="Sorbete aromático",        notes="Ácido málico, β-caroteno"),
    dict(name="Limón (jugo fresco)",     category="Fruta europea",     fat=0.3,  msnf=0.0,  sugars=2.5,  other_st=0.3,  pod=0.03, pac=0.04, water=96.9, brix=9,  ph=2.3, function="Acidez, equilibrio",       notes="pH 2.0-2.6, ácido cítrico 5-8%"),
    dict(name="Lima (jugo fresco)",      category="Fruta europea",     fat=0.2,  msnf=0.0,  sugars=1.7,  other_st=0.2,  pod=0.02, pac=0.03, water=97.9, brix=9,  ph=2.2, function="Acidez fina",              notes="pH 2.0-2.4, aromática"),
    dict(name="Naranja (jugo fresco)",   category="Fruta europea",     fat=0.2,  msnf=0.0,  sugars=9.4,  other_st=0.4,  pod=0.09, pac=0.13, water=90.0, brix=11, ph=3.7, function="Sorbete cítrico",          notes="pH 3.5-4.0, hesperidina"),
    dict(name="Naranja sanguina",        category="Fruta europea",     fat=0.2,  msnf=0.0,  sugars=9.8,  other_st=0.4,  pod=0.10, pac=0.13, water=89.6, brix=11, ph=3.5, function="Sorbete visual",           notes="Antocianos únicos, pH 3.2-3.8"),
    dict(name="Kiwi (pulpa)",            category="Fruta europea",     fat=0.5,  msnf=0.0,  sugars=9.0,  other_st=1.2,  pod=0.09, pac=0.12, water=89.3, brix=10, ph=3.1, function="Sorbete vibrante",         notes="Actinidina (proteasa), pH 3.1"),
    dict(name="Granada (arils)",         category="Fruta europea",     fat=1.2,  msnf=0.0,  sugars=13.7, other_st=0.5,  pod=0.14, pac=0.19, water=84.6, brix=14, ph=3.0, function="Sorbete rojo vivo",        notes="Punicalagina, pH 3.0"),
    # ── Pasta frutos secos ───────────────────────────────────────────────────
    dict(name="Pasta pistache (pura)",   category="Pasta frutos secos",fat=45.0, msnf=0.0,  sugars=7.5,  other_st=20.0, pod=0.08, pac=0.08, water=27.5, brix=0,  ph=6.5, function="Gelato pistacchio",        notes="53% MG insaturada, clorofila"),
    dict(name="Pasta avellana (pura)",   category="Pasta frutos secos",fat=61.0, msnf=0.0,  sugars=4.0,  other_st=14.0, pod=0.04, pac=0.04, water=21.0, brix=0,  ph=6.5, function="Gelato nocciola",          notes="Oleico 75%, aroma tostado"),
    dict(name="Pasta almendra (pura)",   category="Pasta frutos secos",fat=51.0, msnf=0.0,  sugars=4.5,  other_st=17.5, pod=0.05, pac=0.05, water=27.0, brix=0,  ph=6.8, function="Gelato mandorla",          notes="Oleico 70%, amandina"),
    # ── Cacao / Chocolate ────────────────────────────────────────────────────
    dict(name="Cacao polvo alcalino 10%",category="Cacao/Chocolate",  fat=11.0, msnf=0.0,  sugars=0.0,  other_st=58.0, pod=0.00, pac=0.00, water=31.0, brix=0,  ph=8.0, function="Sabor choco suave",        notes="pH 7.5-8.5, Dutched, oscuro"),
    dict(name="Cacao polvo natural 10%", category="Cacao/Chocolate",  fat=10.0, msnf=0.0,  sugars=0.0,  other_st=55.0, pod=0.00, pac=0.00, water=35.0, brix=0,  ph=5.5, function="Sabor choco vivo",         notes="pH 5.0-6.0, rojizo, ácido"),
    dict(name="Pasta de cacao 100%",     category="Cacao/Chocolate",  fat=54.0, msnf=0.0,  sugars=0.0,  other_st=18.0, pod=0.00, pac=0.00, water=28.0, brix=0,  ph=5.5, function="Cacao puro profundo",      notes="Manteca 54%, theobromina"),
    dict(name="Cobertura negra 70%",     category="Cacao/Chocolate",  fat=42.0, msnf=0.0,  sugars=29.0, other_st=16.0, pod=0.29, pac=0.29, water=13.0, brix=0,  ph=5.5, function="Chunk, base premium",      notes="Form V manteca, temperado"),
    dict(name="Cobertura leche 38%",     category="Cacao/Chocolate",  fat=35.0, msnf=4.0,  sugars=46.0, other_st=8.0,  pod=0.46, pac=0.46, water=7.0,  brix=0,  ph=5.5, function="Gelato latte",             notes="Leche en polvo, dulce"),
    dict(name="Manteca de cacao",        category="Cacao/Chocolate",  fat=99.5, msnf=0.0,  sugars=0.0,  other_st=0.0,  pod=0.00, pac=0.00, water=0.5,  brix=0,  ph=7.0, function="Ajuste grasa/textura",     notes="Grasa pura Form V"),
    # ── Café / Té / Aroma ────────────────────────────────────────────────────
    dict(name="Té matcha ceremonial",    category="Café/Té/Aroma",    fat=5.3,  msnf=0.0,  sugars=0.0,  other_st=60.0, pod=0.00, pac=0.00, water=34.7, brix=0,  ph=6.0, function="Gelato matcha",            notes="L-teanina, catequinas, clorofila"),
    dict(name="Café espresso (líquido)", category="Café/Té/Aroma",    fat=0.0,  msnf=0.0,  sugars=0.5,  other_st=1.5,  pod=0.01, pac=0.01, water=98.0, brix=0,  ph=5.0, function="Sabor café",               notes="Clorogénico, cafeína, pH 5.0"),
    dict(name="Extracto de vainilla 2x", category="Café/Té/Aroma",    fat=0.0,  msnf=0.0,  sugars=0.0,  other_st=5.0,  pod=0.00, pac=0.00, water=95.0, brix=0,  ph=5.5, function="Aromatizante base",        notes="200+ aromáticos, vainillina"),
    # ── Alcohol ──────────────────────────────────────────────────────────────
    dict(name="Ron añejo (40% vol)",     category="Alcohol",           fat=0.0,  msnf=0.0,  sugars=0.0,  other_st=0.2,  pod=0.00, pac=3.50, water=57.8, brix=0,  ph=7.0, function="Aroma, suaviza textura",   notes="Etanol PAC=3.5, dosis ≤50g/kg"),
    dict(name="Amaretto (28% vol)",      category="Alcohol",           fat=0.0,  msnf=0.0,  sugars=25.0, other_st=0.5,  pod=0.25, pac=2.30, water=74.5, brix=0,  ph=7.0, function="Aroma almendra",           notes="Almendra amarga + azúcar"),
    dict(name="Limoncello (30% vol)",    category="Alcohol",           fat=0.0,  msnf=0.0,  sugars=28.0, other_st=0.2,  pod=0.28, pac=2.50, water=71.8, brix=0,  ph=7.0, function="Sorbete adulto",           notes="Limoneno, azúcar alta"),
    # ── Estabilizantes ───────────────────────────────────────────────────────
    dict(name="Neutro LBG+Guar+κ-Carr", category="Estabilizante",     fat=0.0,  msnf=0.0,  sugars=0.0,  other_st=99.5, pod=0.00, pac=0.00, water=0.5,  brix=0,  ph=7.0, function="Estructura, overrun",      notes="Dosis 3-5g/kg, sinergia LBG+κ"),
    dict(name="Goma Guar",               category="Estabilizante",     fat=0.0,  msnf=0.0,  sugars=0.0,  other_st=99.0, pod=0.00, pac=0.00, water=1.0,  brix=0,  ph=7.0, function="Sorbetes, viscosidad",     notes="Dosis 0.1-0.2g/kg, soluble en frío"),
    dict(name="Goma Xantana",            category="Estabilizante",     fat=0.0,  msnf=0.0,  sugars=0.0,  other_st=99.0, pod=0.00, pac=0.00, water=1.0,  brix=0,  ph=7.0, function="Estabilidad universal",    notes="Dosis 0.1-0.2g/kg, pseudoplástica"),
    dict(name="Inulina HP",              category="Estabilizante",     fat=0.0,  msnf=0.0,  sugars=0.0,  other_st=94.0, pod=0.00, pac=0.00, water=6.0,  brix=0,  ph=7.0, function="Grasa mimética vegana",    notes="Prebiótico, reemplaza grasa"),
    # ── Emulsionantes ────────────────────────────────────────────────────────
    dict(name="Lecitina de girasol",     category="Emulsionante",      fat=0.0,  msnf=0.0,  sugars=0.0,  other_st=99.0, pod=0.00, pac=0.00, water=1.0,  brix=0,  ph=7.0, function="Emulsión, overrun",        notes="HLB 4, fosfatidilcolina, dosis 2-5g/kg"),
    dict(name="Yema de huevo fresca",    category="Emulsionante",      fat=32.0, msnf=0.0,  sugars=0.6,  other_st=18.0, pod=0.01, pac=0.01, water=49.4, brix=0,  ph=6.5, function="Emulsión perfecta",        notes="Lecitina natural, pasteurizar 72°C"),
    # ── Funcionales ──────────────────────────────────────────────────────────
    dict(name="Sal marina fina",         category="Funcional",         fat=0.0,  msnf=0.0,  sugars=0.0,  other_st=99.5, pod=0.00, pac=2.20, water=0.5,  brix=0,  ph=7.0, function="Contraste dulce, PAC",     notes="NaCl PAC=2.2!, potenciador sabor"),
    dict(name="Ácido cítrico (polvo)",   category="Funcional",         fat=0.0,  msnf=0.0,  sugars=0.0,  other_st=99.5, pod=0.00, pac=0.00, water=0.5,  brix=0,  ph=2.0, function="Ajuste pH",                notes="Acidulante, activa pectina HM"),
    # ── Base ─────────────────────────────────────────────────────────────────
    dict(name="Agua destilada",          category="Base",              fat=0.0,  msnf=0.0,  sugars=0.0,  other_st=0.0,  pod=0.00, pac=0.00, water=100.0,brix=0,  ph=7.0, function="Dilución, ajuste",         notes="Diluyente neutro"),
]

# ── CONEXIÓN ──────────────────────────────────────────────────────────────────

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    with get_connection() as conn:
        conn.executescript(SCHEMA)
        count = conn.execute("SELECT COUNT(*) FROM ingredients").fetchone()[0]
        if count == 0:
            fields = "name,category,fat,msnf,sugars,other_st,pod,pac,water,notes,function,brix,ph"
            placeholders = ",".join(["?"] * 13)
            rows = [(
                d['name'], d['category'], d['fat'], d['msnf'], d['sugars'],
                d['other_st'], d['pod'], d['pac'], d['water'],
                d.get('notes',''), d.get('function',''),
                d.get('brix', 0), d.get('ph', 7.0)
            ) for d in DB_DATA]
            conn.executemany(
                f"INSERT OR IGNORE INTO ingredients ({fields}) VALUES ({placeholders})",
                rows
            )

# ── INGREDIENTES ──────────────────────────────────────────────────────────────

def get_all_ingredients():
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM ingredients ORDER BY category, name").fetchall()
    return [dict(r) for r in rows]

def get_ingredient_by_name(name):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM ingredients WHERE name=?", (name,)).fetchone()
    return dict(row) if row else None

def save_ingredient(data):
    fields = "name,category,fat,msnf,sugars,other_st,pod,pac,water,notes,function,brix,ph"
    vals = (
        data['name'], data['category'], data['fat'], data['msnf'], data['sugars'],
        data['other_st'], data['pod'], data['pac'], data['water'],
        data.get('notes',''), data.get('function',''),
        data.get('brix', 0), data.get('ph', 7.0)
    )
    with get_connection() as conn:
        if data.get('id'):
            sets = ",".join(f"{f}=?" for f in fields.split(","))
            conn.execute(f"UPDATE ingredients SET {sets} WHERE id=?", vals + (data['id'],))
        else:
            placeholders = ",".join(["?"] * 13)
            conn.execute(f"INSERT INTO ingredients ({fields}) VALUES ({placeholders})", vals)

def delete_ingredient(ing_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM ingredients WHERE id=?", (ing_id,))

# ── RECETAS ───────────────────────────────────────────────────────────────────

def get_all_recipes():
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM recipes ORDER BY updated_at DESC").fetchall()
    return [dict(r) for r in rows]

def get_recipe(recipe_id):
    with get_connection() as conn:
        rec = conn.execute("SELECT * FROM recipes WHERE id=?", (recipe_id,)).fetchone()
        if not rec:
            return None
        lines = conn.execute(
            "SELECT * FROM recipe_lines WHERE recipe_id=? ORDER BY sort_order",
            (recipe_id,)
        ).fetchall()
    result = dict(rec)
    result['lines'] = [dict(l) for l in lines]
    return result

def save_recipe(data):
    rec_id = data.get('id')
    with get_connection() as conn:
        if rec_id:
            conn.execute(
                "UPDATE recipes SET name=?,product_type=?,machine=?,base_grams=?,"
                "notes=?,tasting_notes=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (data['name'], data['product_type'], data['machine'], data['base_grams'],
                 data.get('notes',''), data.get('tasting_notes',''), rec_id)
            )
            conn.execute("DELETE FROM recipe_lines WHERE recipe_id=?", (rec_id,))
        else:
            cur = conn.execute(
                "INSERT INTO recipes (name,product_type,machine,base_grams,notes,tasting_notes)"
                " VALUES (?,?,?,?,?,?)",
                (data['name'], data['product_type'], data['machine'], data['base_grams'],
                 data.get('notes',''), data.get('tasting_notes',''))
            )
            rec_id = cur.lastrowid
        for i, line in enumerate(data.get('lines', [])):
            conn.execute(
                "INSERT INTO recipe_lines (recipe_id,ingredient_name,grams,price_per_kg,sort_order)"
                " VALUES (?,?,?,?,?)",
                (rec_id, line['ingredient_name'], line['grams'], line.get('price_per_kg', 0), i)
            )
    return rec_id

def delete_recipe(recipe_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM recipes WHERE id=?", (recipe_id,))

if __name__ == "__main__":
    init_db()
    print("DB initialized:", DB_PATH)
    print(f"Ingredients: {len(get_all_ingredients())}")
