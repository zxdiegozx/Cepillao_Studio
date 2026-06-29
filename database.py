import sqlite3, os
from constants import MACHINE_CREAMI_DELUXE

_vol    = os.environ.get("RAILWAY_VOLUME_MOUNT_PATH", "").strip()
DB_PATH = os.path.join(_vol if _vol else os.path.dirname(os.path.abspath(__file__)), "gelato.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS ingredients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    category TEXT NOT NULL,
    fat REAL DEFAULT 0,
    msnf REAL DEFAULT 0,
    sugars REAL DEFAULT 0,
    other_st REAL DEFAULT 0,
    pod REAL DEFAULT 0,
    pac REAL DEFAULT 0,
    water REAL DEFAULT 0,
    notes TEXT DEFAULT '',
    function TEXT DEFAULT '',
    brix REAL DEFAULT 0,
    ph REAL DEFAULT 0,
    price_per_kg REAL DEFAULT 0,
    calories_per_100g REAL DEFAULT 0,
    zero_calorie INTEGER DEFAULT 0
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_ingredients_name ON ingredients(name);

CREATE TABLE IF NOT EXISTS recipes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    product_type TEXT DEFAULT 'Helado/Gelato',
    machine TEXT DEFAULT 'Ninja Creami Deluxe',
    base_grams REAL DEFAULT 1000,
    notes TEXT DEFAULT '',
    tasting_notes TEXT DEFAULT '',
    cost_total REAL DEFAULT 0,
    is_base INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS recipe_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recipe_id INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    ingredient_id INTEGER REFERENCES ingredients(id),
    ingredient_name TEXT NOT NULL,
    grams REAL NOT NULL,
    price_per_kg REAL DEFAULT 0,
    sort_order INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    description TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS user_config (
    key        TEXT PRIMARY KEY NOT NULL,
    value      TEXT NOT NULL DEFAULT '{}',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

MIGRATIONS = [
    (1, "ALTER TABLE ingredients ADD COLUMN price_per_kg REAL DEFAULT 0",
        "Añade precio por kg a ingredientes"),
    (2, "ALTER TABLE ingredients ADD COLUMN calories_per_100g REAL DEFAULT 0",
        "Añade calorías por 100g a ingredientes"),
    (3, "ALTER TABLE ingredients ADD COLUMN zero_calorie INTEGER DEFAULT 0",
        "Añade flag zero_calorie a ingredientes"),
    (4, "ALTER TABLE recipes ADD COLUMN is_base INTEGER DEFAULT 0",
        "Añade flag is_base para distinguir bases de helado de recetas finales"),
    # Migración 5: seed incremental.
    # INSERT OR IGNORE respeta el UNIQUE en 'name': si ya existe, no toca nada.
    # Para añadir más ingredientes en el futuro: agrega a DB_DATA y crea migración 6, 7...
    (5, "SELECT 1",
        "Seed incremental v1: 134 ingredientes estándar con categorias nuevas"),
    (6, """CREATE TABLE IF NOT EXISTS user_config (
        key        TEXT PRIMARY KEY NOT NULL,
        value      TEXT NOT NULL DEFAULT '{}',
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )""",
    "Tabla user_config para persistir rangos personalizados por tipo/máquina")
]

# Versión de migración que dispara el seed incremental.
# Sube este número (y crea la migración correspondiente) cada vez que amplíes DB_DATA.
_SEED_MIGRATION_VERSION = 5

# ─────────────────────────────────────────────────────────────────────────────
# BASE DE DATOS ESTÁNDAR
# Columnas: name, category, fat, msnf, sugars, other_st, pod, pac, water,
#           notes, function, brix, ph
# Categorías alineadas con INGREDIENT_CATEGORIES en constants.py
# ─────────────────────────────────────────────────────────────────────────────
DB_DATA = [

    # ══════════════════════════════════════════════════════════════════════════
    # BASE LÁCTEA
    # ══════════════════════════════════════════════════════════════════════════
    ("Leche entera 3.5%",           "Base láctea", 3.5,  9.0,  4.7,  0.0, 0.10, 0.10, 82.8,
     "Emulsión O/W natural, lactosa 4.7%, pH 6.6",          "Base principal",         0,  6.6),
    ("Leche semidescremada 1.5%",   "Base láctea", 1.5,  9.3,  4.8,  0.0, 0.10, 0.10, 84.4,
     "Equilibrio grasa/MSNF, deslactosada disponible",      "Base media grasa",       0,  6.6),
    ("Leche descremada 0.1%",       "Base láctea", 0.1,  9.5,  4.8,  0.0, 0.10, 0.10, 85.6,
     "Alta MSNF sin grasa, máx proteína",                   "Base baja grasa",        0,  6.6),
    ("Leche entera deslactosada",   "Base láctea", 3.5,  9.0,  4.7,  0.0, 0.10, 0.10, 82.8,
     "Lactosa hidrolizada→glucosa+galactosa, más dulce",    "Base para intolerantes", 0,  6.6),
    ("Leche descremada deslactosada","Base láctea",0.1,  9.5,  4.8,  0.0, 0.10, 0.10, 85.6,
     "Sin lactosa, sin grasa, MSNF alto",                   "Base light intolerante", 0,  6.6),
    ("Leche condensada azucarada",  "Base láctea", 8.5,  20.0, 55.0, 0.0, 0.55, 0.55, 26.5,
     "Azúcar añadida ~44%, muy concentrada, POD alto",      "Dulzor + sólidos altos", 0,  6.3),
    ("Leche condensada sin azúcar", "Base láctea", 7.5,  20.0, 11.0, 0.0, 0.22, 0.22, 61.5,
     "Leche evaporada 2.5x, MSNF concentrado",              "Aumentar sólidos lácteos",0, 6.5),
    ("Leche evaporada 7.5%",        "Base láctea", 7.5,  17.0, 10.0, 0.0, 0.20, 0.20, 65.5,
     "Concentrada 2x, sin azúcar añadida",                  "Sólidos sin dulzor extra",0, 6.5),
    ("Crema de leche 25% MG",       "Base láctea", 25.0, 7.0,  4.0,  0.0, 0.04, 0.04, 64.0,
     "Crema media, común en Venezuela/LatAm",               "Grasa moderada",         0,  6.5),
    ("Crema de leche 35% MG",       "Base láctea", 35.0, 6.0,  3.5,  0.0, 0.04, 0.04, 55.5,
     "Globos grasos 3-8µm, pasteurizar 85°C/15s",           "Fuente grasa primaria",  0,  6.5),
    ("Crema de leche 48% MG",       "Base láctea", 48.0, 4.0,  2.5,  0.0, 0.03, 0.03, 45.5,
     "Ultra-grasa, para semifreddo y bases ricas",          "Grasa máxima",           0,  6.5),
    ("Leche en polvo entera",       "Base láctea", 26.0, 38.0, 37.5, 0.0, 0.38, 0.38,  1.0,
     "Higroscópica, añadir en seco con azúcares",           "Concentrar MSNF+ST",     0,  6.8),
    ("Leche en polvo descremada",   "Base láctea",  1.0, 52.0, 50.0, 0.0, 0.50, 0.50,  3.0,
     "Proteínas 34%, lactosa 50%, MSNF puro",               "Aumentar MSNF sin grasa",0,  6.8),
    ("Leche en polvo deslactosada", "Base láctea",  1.0, 52.0,  2.0, 0.0, 0.05, 0.05,  3.0,
     "Lactosa hidrolizada, MSNF proteico concentrado",      "MSNF sin lactosa",       0,  6.8),
    ("Mantequilla 82% MG",          "Base láctea", 82.0,  1.5,  0.6, 0.0, 0.01, 0.01, 15.9,
     "Cristalización Forma β', sabor intenso",              "Ajuste fino grasa",      0,  6.5),
    ("Mantequilla sin sal 84%",     "Base láctea", 84.0,  1.2,  0.5, 0.0, 0.01, 0.01, 14.3,
     "Sin sal, más pura, para salsas y bases neutras",      "Grasa + sabor neutro",   0,  6.5),
    ("Mascarpone 41% MG",           "Base láctea", 41.0,  5.0,  3.5, 0.0, 0.04, 0.04, 50.5,
     "Ácido cítrico, pH 5.5, textura untuosa",              "Gelato ricco",           0,  5.5),
    ("Queso crema 30% MG",          "Base láctea", 30.0,  8.0,  3.8, 0.0, 0.04, 0.04, 58.2,
     "Philadelphia-style, pH 4.5-5.0",                     "Textura densa",          0,  4.8),
    ("Ricotta entera",              "Base láctea", 13.0,  9.0,  3.0, 0.0, 0.03, 0.03, 75.0,
     "Suero+leche, granulosa → licuar",                     "Cuerpo, proteína",       0,  6.2),
    ("Yogur griego 10% MG",         "Base láctea", 10.0, 10.0,  4.0, 0.0, 0.04, 0.04, 76.0,
     "Colado, pH 4.0-4.5, proteína alta ~10%",              "Frescura + proteína",    0,  4.2),
    ("Yogur entero 3.5%",           "Base láctea",  3.5,  9.0,  4.7, 0.0, 0.10, 0.10, 82.8,
     "Ácido láctico, pH 4.0-4.5",                           "Acidez, frescura",       0,  4.2),
    ("Suero de leche en polvo",     "Base láctea",  1.5, 72.0, 70.0, 0.0, 0.70, 0.70,  4.0,
     "WPC 35%, lactosa alta 70%",                           "Sólidos económicos",     0,  6.5),
    ("Natulac 25% MG",              "Base láctea", 25.0,  7.5,  4.0, 0.5, 0.04, 0.04, 63.0,
     "Crema pasteurizada venezolana con carragenina — NO combinar con CMC+fruta ácida",
     "Crema local",                 0,  6.5),

    # ══════════════════════════════════════════════════════════════════════════
    # BASE VEGETAL
    # ══════════════════════════════════════════════════════════════════════════
    ("Leche de coco entera 17%",    "Base vegetal", 17.5,  0.0,  3.8,  1.5, 0.04, 0.05, 77.2,
     "Ácido láurico, emulsión natural, aroma coco",         "Base gelato vegano",     0,  6.5),
    ("Crema de coco 24%",           "Base vegetal", 24.0,  0.0,  4.0,  2.0, 0.04, 0.06, 70.0,
     "Ultra-grasa vegetal, solidifica <25°C",               "Grasa vegana premium",   0,  6.5),
    ("Leche de almendra",           "Base vegetal",  1.1,  0.0,  0.3,  0.5, 0.00, 0.01, 98.1,
     "Baja en sólidos, requiere espesantes",                "Base vegana ligera",     0,  6.8),
    ("Leche de avena",              "Base vegetal",  1.5,  0.0,  4.5,  1.0, 0.05, 0.07, 93.0,
     "β-glucanos, POD moderado, cremosa",                   "Base vegana cremosa",    0,  6.5),
    ("Leche de soya",               "Base vegetal",  1.8,  0.0,  1.0,  3.5, 0.01, 0.02, 93.7,
     "Proteína 3.5%, emulsión natural",                     "Base vegana proteica",   0,  6.8),
    ("Agua destilada",              "Base vegetal",  0.0,  0.0,  0.0,  0.0, 0.00, 0.00,100.0,
     "Diluyente neutro puro",                               "Dilución, ajuste",       0,  7.0),
    ("Agua de coco natural",        "Base vegetal",  0.2,  0.0,  6.0,  0.5, 0.06, 0.08, 93.3,
     "Electrolitos, sabor suave, Brix 5-7°",               "Base refrescante",       6,  4.7),

    # ══════════════════════════════════════════════════════════════════════════
    # FRUTA — TROPICAL
    # ══════════════════════════════════════════════════════════════════════════
    ("Mango Tommy (pulpa)",         "Fruta",  0.4,  0.0, 15.0,  0.8, 0.15, 0.21, 83.8,
     "Brix 16-20°, pH 3.5-4.2, variedad común Venezuela",  "Sorbete tropical",      18,  3.8),
    ("Mango de hilacha (pulpa)",    "Fruta",  0.3,  0.0, 17.0,  1.0, 0.17, 0.23, 81.7,
     "Muy dulce, fibroso → tamizar bien",                   "Sorbete intenso",       18,  3.9),
    ("Maracuyá (pulpa c/semilla)",  "Fruta",  0.7,  0.0, 11.5,  1.5, 0.12, 0.17, 86.3,
     "Brix 14-16°, pH 2.8-3.2, ácido fuerte",              "Acidez + aroma",        15,  3.0),
    ("Maracuyá (jugo filtrado)",    "Fruta",  0.4,  0.0, 12.0,  0.5, 0.12, 0.17, 87.1,
     "Sin semillas, más limpio, pH 2.8",                    "Sorbete limpio",        13,  2.9),
    ("Guanábana (pulpa)",           "Fruta",  0.3,  0.0, 13.5,  3.5, 0.14, 0.16, 82.7,
     "Fibra 3.5%, pH 3.5, textura untuosa",                 "Sorbete cremoso vegano",14,  3.5),
    ("Piña golden (pulpa)",         "Fruta",  0.2,  0.0, 16.0,  0.7, 0.16, 0.22, 83.1,
     "Bromelina activa → inactiva al cocinar, pH 3.5",      "Sorbete refrescante",   15,  3.5),
    ("Cambur/Banana madura",        "Fruta",  0.3,  0.0, 17.0,  2.8, 0.17, 0.22, 79.9,
     "Almidón→azúcar en madurez, pectina alta",             "Cuerpo, dulzor natural",18,  4.8),
    ("Lechosa/Papaya (pulpa)",      "Fruta",  0.3,  0.0,  8.3,  0.9, 0.08, 0.11, 90.5,
     "Papaína activa → inactivar con calor, β-caroteno",    "Sorbete suave",          9,  5.8),
    ("Aguacate (pulpa)",            "Fruta",  15.0, 0.0,  0.7,  3.0, 0.01, 0.01, 81.3,
     "66% MG monoinsaturada, cremosidad única",             "Base vegana untuosa",    0,  6.3),
    ("Parchita/Fruta de la pasión", "Fruta",  0.4,  0.0, 11.0,  1.8, 0.11, 0.16, 86.8,
     "Igual que maracuyá, nombre local venezolano",         "Acidez + aroma",        13,  3.0),
    ("Guayaba (pulpa)",             "Fruta",  0.9,  0.0,  9.0,  5.5, 0.09, 0.13, 84.6,
     "Pectina muy alta, pH 3.5-4.0, licopeno",              "Sorbete con cuerpo",    10,  3.7),
    ("Tamarindo (pulpa)",           "Fruta",  0.6,  0.0, 38.0,  5.5, 0.38, 0.55, 55.9,
     "Muy concentrado, ácido tartárico, azúcar alta",       "Sorbete agridulce",     55,  3.0),
    ("Lulo (pulpa)",                "Fruta",  0.1,  0.0,  4.5,  0.5, 0.05, 0.07, 94.9,
     "pH 2.5-3.0, muy ácido, aroma único andino",           "Sorbete intenso ácido", 5,   2.8),
    ("Carambola (pulpa)",           "Fruta",  0.3,  0.0,  7.1,  0.4, 0.07, 0.10, 92.2,
     "Ácido oxálico, pH 3.0-4.0, apariencia estrella",      "Sorbete tropical raro", 7,   3.5),
    ("Mango (enlatado en almíbar)", "Fruta",  0.2,  0.0, 23.0,  0.5, 0.23, 0.32, 76.3,
     "Almíbar añadido, Brix 18-22°, pasteurizado",          "Sorbete sin temporada", 22,  3.8),
    ("Durazno (enlatado en almíbar)","Fruta", 0.1,  0.0, 18.0,  0.3, 0.18, 0.25, 81.6,
     "Almíbar ligero, consistente todo el año",             "Sorbete clásico",       18,  3.9),
    ("Piña (enlatada en jugo)",     "Fruta",  0.1,  0.0, 14.0,  0.5, 0.14, 0.19, 85.4,
     "Sin almíbar extra, bromelina inactiva por proceso",   "Sorbete conveniente",   14,  3.6),
    ("Cereza maraschino (enlatada)","Fruta",  0.3,  0.0, 28.0,  0.3, 0.28, 0.39, 71.4,
     "Alta azúcar añadida, uso como inclusion o swirl",     "Decoration / inclusion",28,  3.5),
    ("Coco rallado seco",           "Fruta",  64.0, 0.0,  6.5,  9.0, 0.07, 0.07, 20.5,
     "Grasa saturada laurica, fibra 9%",                    "Textura, sabor coco",   0,   6.5),

    # ── Fruta europea/templada ────────────────────────────────────────────────
    ("Fresa (pulpa)",               "Fruta",  0.3,  0.0,  7.7,  0.5, 0.08, 0.11, 91.5,
     "Antocianos, pH 3.0-3.5, Brix 8-11°",                 "Sorbete clásico",        9,  3.2),
    ("Frambuesa (pulpa)",           "Fruta",  0.7,  0.0,  5.4,  2.8, 0.05, 0.07, 91.1,
     "pH 2.8-3.2, muy ácida, pepitas → tamizar",           "Sorbete intenso",        7,  3.0),
    ("Arándano (blueberry)",        "Fruta",  0.3,  0.0, 10.0,  0.8, 0.10, 0.14, 88.9,
     "Antocianos altos, pH 3.1-3.3",                        "Sorbete antioxidante",  11,  3.2),
    ("Mora (blackberry)",           "Fruta",  0.5,  0.0,  9.6,  2.2, 0.10, 0.13, 87.7,
     "Antocianos, pepitas → tamizar",                       "Sorbete oscuro",        10,  3.2),
    ("Limón (jugo fresco)",         "Fruta",  0.3,  0.0,  2.5,  0.3, 0.03, 0.04, 96.9,
     "pH 2.0-2.6, ácido cítrico 5-8%",                     "Acidez, equilibrio",     9,  2.3),
    ("Naranja (jugo fresco)",       "Fruta",  0.2,  0.0,  9.4,  0.4, 0.09, 0.13, 90.0,
     "pH 3.5-4.0, hesperidina",                             "Sorbete cítrico",       11,  3.7),
    ("Durazno/Melocotón (fresco)",  "Fruta",  0.3,  0.0,  9.5,  0.8, 0.10, 0.13, 89.4,
     "Ácido málico, β-caroteno",                            "Sorbete aromático",     10,  3.7),

    # ══════════════════════════════════════════════════════════════════════════
    # DULCIFICANTE
    # ══════════════════════════════════════════════════════════════════════════
    ("Sacarosa",                    "Dulcificante",  0.0, 0.0,100.0,  0.0, 1.00, 1.00,  0.0,
     "Referencia absoluta POD=PAC=1.0",                     "Base de dulzor",         0,  7.0),
    ("Dextrosa monohidrato",        "Dulcificante",  0.0, 0.0, 91.0,  0.0, 0.75, 1.90,  9.0,
     "MW=198, PAC=1.9 → crioscópico potente, frescor suave","Bajar congelación",      0,  7.0),
    ("Fructosa",                    "Dulcificante",  0.0, 0.0, 99.5,  0.0, 1.20, 1.90,  0.5,
     "POD>sacarosa en frío, ideal sorbetes, IG bajo",       "Dulzor potenciado frío", 0,  7.0),
    ("Trehalosa",                   "Dulcificante",  0.0, 0.0, 99.5,  0.0, 0.45, 0.70,  0.5,
     "Crioprotector, protege membranas, POD neutro",        "Estabilidad congelado",  0,  7.0),
    ("Alulosa",                     "Dulcificante",  0.0, 0.0, 99.0,  0.0, 0.70, 1.00,  1.0,
     "0.4 kcal/g, sabor idéntico a sacarosa, POD=0.70",    "Dulcificante light",     0,  7.0),
    ("Eritritol",                   "Dulcificante",  0.0, 0.0, 99.5,  0.0, 0.65, 1.30,  0.5,
     "0.2 kcal/g, PAC alto, máx 1.5% mezcla total",        "Low-calorie, frescor",   0,  7.0),
    ("Azúcar invertido",            "Dulcificante",  0.0, 0.0, 75.0,  0.0, 1.30, 1.90, 25.0,
     "Fructosa+glucosa libres, higroscópico, antirecristal","Textura suave, brillo",  0,  7.0),
    ("Glucosa líquida DE40",        "Dulcificante",  0.0, 0.0, 95.0,  0.0, 0.50, 0.64,  5.0,
     "Sirop DE40, anticristalización, textura extensible",  "Textura, anti-cristal",  0,  7.0),
    ("Glucosa atomizada DE60",      "Dulcificante",  0.0, 0.0, 95.0,  0.0, 0.70, 0.90,  5.0,
     "Mayor dulzor que DE40, polvo soluble",                "Balance dulzor/textura", 0,  7.0),
    ("Miel de abeja",               "Dulcificante",  0.0, 0.0, 80.0,  1.0, 1.00, 1.50, 19.0,
     "Fructosa+glucosa 70%, polifenoles, aroma floral",     "Dulzor floral complejo", 0,  3.9),
    ("Isomalt",                     "Dulcificante",  0.0, 0.0, 98.5,  0.0, 0.45, 0.70,  1.5,
     "Sin caries, bajo IG, cristales transparentes",        "Reducir azúcar normal",  0,  7.0),
    ("Xilitol",                     "Dulcificante",  0.0, 0.0, 98.0,  0.0, 1.00, 1.20,  2.0,
     "PAC=1.2, frescor, efecto laxante >50g/día",           "Dulcificante dental",    0,  7.0),
    ("Maltitol",                    "Dulcificante",  0.0, 0.0, 99.0,  0.0, 0.75, 0.90,  1.0,
     "Similar a sacarosa, molestias GI en exceso",          "Sugar-free",             0,  7.0),
    ("Panela rallada",              "Dulcificante",  0.0, 0.0, 92.0,  2.0, 0.92, 1.20,  4.0,
     "Sacarosa+minerales, aroma melado venezolano",         "Dulzor tradicional",     0,  5.5),
    ("Melaza",                      "Dulcificante",  0.0, 0.0, 68.0,  5.0, 0.85, 1.20, 22.0,
     "Subproducto azúcar, hierro, potasio, amargo residual","Dulzor oscuro",          0,  5.0),

    # ══════════════════════════════════════════════════════════════════════════
    # EDULCORANTE INTENSIVO
    # ══════════════════════════════════════════════════════════════════════════
    ("Stevia en polvo (pura)",      "Edulcorante intensivo", 0.0, 0.0, 0.0, 5.0, 0.00, 0.00, 5.0,
     "200-300x sacarosa, retrogusto regaliz, máx 0.3g/kg",  "Corrector dulzor",       0,  7.0),
    ("Sucralosa",                   "Edulcorante intensivo", 0.0, 0.0, 0.0, 2.0, 0.00, 0.00, 2.0,
     "600x sacarosa, estable al calor, sin retrogusto",      "Endulzar sin calorías",  0,  7.0),
    ("Splenda (eritritol+stevia)",  "Edulcorante intensivo", 0.0, 0.0, 99.0,0.0, 0.65, 1.30, 1.0,
     "Mezcla comercial, POD/PAC del eritritol base",         "Corrector sabor light",  0,  7.0),

    # ══════════════════════════════════════════════════════════════════════════
    # ESTABILIZANTE
    # ══════════════════════════════════════════════════════════════════════════
    ("Goma Xantana",                "Estabilizante", 0.0, 0.0, 0.0, 99.0, 0.00, 0.00,  1.0,
     "Pseudoplástica, estable pH 2-8, dosis 0.1-0.3g/kg",   "Estabilidad universal",  0,  7.0),
    ("Goma Guar",                   "Estabilizante", 0.0, 0.0, 0.0, 99.0, 0.00, 0.00,  1.0,
     "Hidrocoloide frío, dosis 0.1-0.2g/kg, sinergia Xantana","Sorbetes, viscosidad", 0,  7.0),
    ("CMC (carboximetilcelulosa)",  "Estabilizante", 0.0, 0.0, 0.0, 99.0, 0.00, 0.00,  1.0,
     "Espesante clásico, dosis 0.8-1.5g/kg, se degrada pH<4","Retención agua",        0,  7.0),
    ("Pectina LM 99%",              "Estabilizante", 0.0, 0.0, 0.0, 99.0, 0.00, 0.00,  1.0,
     "Baja metoxilación, gelifica con Ca²⁺, dosis 1-2g/kg", "Sorbetes, frutas",       0,  7.0),
    ("Pectina HM",                  "Estabilizante", 0.0, 0.0, 0.0, 99.0, 0.00, 0.00,  1.0,
     "Alta metoxilación, gelifica pH<3.5 + azúcar >55%",    "Frutas ácidas altas Brix",0, 7.0),
    ("LBG (algarroba)",             "Estabilizante", 0.0, 0.0, 0.0, 99.0, 0.00, 0.00,  1.0,
     "Galactomanano, requiere >80°C para hidratar, dosis 1-2g/kg","Cuerpo cremoso",   0,  7.0),
    ("Agar-agar",                   "Estabilizante", 0.0, 0.0, 0.0, 99.0, 0.00, 0.00,  1.0,
     "Polisacárido alga, gel firme reversible, dosis 2-5g/kg","Gel fuerte",           0,  7.0),
    ("Gelatina sin sabor (200 bloom)","Estabilizante",0.0,0.0, 0.0, 87.0, 0.00, 0.00,  3.0,
     "Colageno hidrolizado, 200 bloom, dosis 3-8g/kg",       "Cuerpo, overrun",        0,  7.0),
    ("Almidón modificado",          "Estabilizante", 0.0, 0.0, 0.0, 88.0, 0.00, 0.00, 12.0,
     "Pregelatinizado, no requiere cocción, dosis 10-20g/kg","Textura lisa",           0,  7.0),
    ("Inulina HP",                  "Estabilizante", 0.0, 0.0, 0.0, 94.0, 0.00, 0.00,  6.0,
     "Cadena larga, reemplaza grasa, prebiótico, 1.5 kcal/g","Grasa mimética vegana", 0,  7.0),
    ("Neutro para helado (mezcla)", "Estabilizante", 0.0, 0.0, 0.0, 99.0, 0.00, 0.00,  1.0,
     "LBG+Guar+κ-Carragenina, dosis 3-5g/kg, listo para usar","Estructura completa",  0,  7.0),

    # ══════════════════════════════════════════════════════════════════════════
    # EMULSIONANTE
    # ══════════════════════════════════════════════════════════════════════════
    ("Lecitina de girasol en polvo","Emulsionante",  0.0, 0.0, 0.0, 99.0, 0.00, 0.00,  1.0,
     "HLB 4, fosfatidilcolina, dosis 2-5g/kg, sin alérgeno soja","Emulsión, overrun", 0,  7.0),
    ("Lecitina de soja líquida",    "Emulsionante",  0.0, 0.0, 0.0, 99.0, 0.00, 0.00,  1.0,
     "HLB 4, más económica, alérgeno declarable soja",       "Emulsión económica",     0,  7.0),
    ("Yema de huevo fresca",        "Emulsionante", 32.0, 0.0, 0.6, 18.0, 0.01, 0.01, 49.4,
     "Lecitina natural, pasteurizar 72°C, POD/PAC mínimo",   "Emulsión perfecta",      0,  6.5),
    ("Yema de huevo en polvo",      "Emulsionante", 57.0, 0.0, 2.0, 35.0, 0.02, 0.02,  6.0,
     "Lecitina concentrada, 5x yema fresca",                 "Emulsión concentrada",   0,  6.5),

    # ══════════════════════════════════════════════════════════════════════════
    # PROTEÍNA
    # ══════════════════════════════════════════════════════════════════════════
    ("WPC 80% (suero concentrado)", "Proteína",      4.0, 82.0, 8.0,  0.0, 0.08, 0.08,  6.0,
     "80% proteína, espumante, desnaturaliza 72°C",          "Overrun, cuerpo",        0,  6.5),
    ("WPI 90% (suero aislado)",     "Proteína",      1.0, 92.0, 2.0,  0.0, 0.02, 0.02,  5.0,
     "90% proteína, sin lactosa, máxima pureza",             "Helado proteico",        0,  6.5),
    ("Caseína micelar (MPC 85)",    "Proteína",      2.0, 87.0, 4.0,  0.0, 0.04, 0.04,  7.0,
     "Termoestable hasta 140°C, gelificante lento",          "Cuerpo, textura gelada", 0,  6.8),
    ("Proteína de guisante (pea)",  "Proteína",      6.0, 82.0, 2.0,  2.0, 0.02, 0.02,  8.0,
     "Vegetal, sin alérgenos comunes, desnaturaliza 90°C",   "Proteína vegana",        0,  7.0),
    ("Clara de huevo en polvo",     "Proteína",      0.0, 82.0, 8.0,  0.0, 0.08, 0.08, 10.0,
     "Albumina, espumante excepcional, desnaturaliza 60°C",  "Overrun máximo",         0,  7.0),

    # ══════════════════════════════════════════════════════════════════════════
    # GRASA
    # ══════════════════════════════════════════════════════════════════════════
    ("Aceite de coco virgen",       "Grasa",        99.0, 0.0,  0.0,  0.0, 0.00, 0.00,  1.0,
     "Laurico 50%, solidifica <25°C, aroma coco",            "Grasa vegana cristalina",0, 7.0),
    ("Aceite neutro (maíz/girasol)","Grasa",        99.5, 0.0,  0.0,  0.0, 0.00, 0.00,  0.5,
     "Sin aroma, insaturado, no cristaliza",                 "Grasa neutra vegana",    0,  7.0),

    # ══════════════════════════════════════════════════════════════════════════
    # CACAO Y CHOCOLATE
    # ══════════════════════════════════════════════════════════════════════════
    ("Cacao polvo sin azúcar natural","Cacao y chocolate",10.0,0.0, 0.0, 55.0, 0.00, 0.00, 35.0,
     "pH 5.0-6.0, rojizo, sabor vivo y ácido, sin alcalinizar","Sabor cacao intenso",  0,  5.5),
    ("Cacao polvo alcalinizado",    "Cacao y chocolate",11.0,0.0, 0.0, 58.0, 0.00, 0.00, 31.0,
     "Dutched pH 7.5-8.5, color oscuro, sabor suave",        "Cacao oscuro suave",     0,  8.0),
    ("Pasta de cacao 100%",         "Cacao y chocolate",54.0,0.0, 0.0, 18.0, 0.00, 0.00, 28.0,
     "Manteca 54%, theobromina, sin azúcar",                 "Cacao puro profundo",    0,  5.5),
    ("Manteca de cacao",            "Cacao y chocolate",99.5,0.0, 0.0,  0.0, 0.00, 0.00,  0.5,
     "Grasa pura Forma V, temperado",                        "Ajuste grasa/textura",   0,  7.0),
    ("Chocolate Savoy 46% cacao",   "Cacao y chocolate",28.0,1.5,41.0, 14.0, 0.41, 0.41, 15.5,
     "Cobertura venezolana 46%, equilibrado, Brix ~55°",     "Base chocolate venezolano",0, 5.5),
    ("Cobertura negra 70% cacao",   "Cacao y chocolate",42.0,0.0,29.0, 16.0, 0.29, 0.29, 13.0,
     "Forma V manteca, temperado, intenso",                  "Gelato premium oscuro",  0,  5.5),
    ("Cobertura negra 55% cacao",   "Cacao y chocolate",33.0,0.0,38.0, 14.0, 0.38, 0.38, 15.0,
     "Balance dulzor/amargo, versátil",                      "Gelato chocolate medio", 0,  5.5),
    ("Cobertura blanca",            "Cacao y chocolate",36.0,5.0,48.0,  5.0, 0.48, 0.48,  6.0,
     "Sin sólidos de cacao, solo manteca+leche+azúcar",     "Gelato blanco",          0,  6.0),
    ("Cobertura de leche 38%",      "Cacao y chocolate",35.0,4.0,46.0,  8.0, 0.46, 0.46,  7.0,
     "Leche en polvo integrada, dulce",                      "Gelato con leche",       0,  5.5),
    ("Chips de chocolate 50%",      "Cacao y chocolate",30.0,0.0,50.0, 10.0, 0.50, 0.50, 10.0,
     "Estables al horneado, tamaño mini/estándar",           "Inclusion",              0,  5.5),
    ("Cacao en polvo Savoy",        "Cacao y chocolate",11.0,0.0, 0.0, 55.0, 0.00, 0.00, 34.0,
     "Cacao venezolano, ligeramente alcalinizado, ph ~6.5",  "Sabor cacao local",      0,  6.5),

    # ══════════════════════════════════════════════════════════════════════════
    # SABORIZANTE
    # ══════════════════════════════════════════════════════════════════════════
    ("Pasta de pistacho (100%)",    "Saborizante",  45.0, 0.0,  7.5, 20.0, 0.08, 0.08, 27.5,
     "53% MG insaturada, clorofila natural, sin azúcar",     "Gelato pistacchio",      0,  6.5),
    ("Pasta de avellana (100%)",    "Saborizante",  61.0, 0.0,  4.0, 14.0, 0.04, 0.04, 21.0,
     "Oleico 75%, aroma tostado intenso",                    "Gelato nocciola",        0,  6.5),
    ("Pasta de almendra (100%)",    "Saborizante",  51.0, 0.0,  4.5, 17.5, 0.05, 0.05, 27.0,
     "Oleico 70%, amandina, suave",                          "Gelato mandorla",        0,  6.8),
    ("Mantequilla de maní",         "Saborizante",  50.0, 0.0,  6.0, 20.0, 0.06, 0.06, 24.0,
     "Oleico+linoleico, proteína 25%, sal variable",         "Gelato/sorbete maní",    0,  6.5),
    ("Crema de pistacho (azucarada)","Saborizante", 32.0, 0.0, 28.0, 18.0, 0.28, 0.28, 22.0,
     "Pasta+azúcar+leche, lista para usar, POD significativo","Gelato pistacchio fácil",0, 6.5),
    ("Praliné de avellana",         "Saborizante",  40.0, 0.0, 40.0, 12.0, 0.40, 0.40,  8.0,
     "Avellana+caramelo molido, 50/50 grasa/azúcar aprox",   "Gelato praliné",         0,  5.5),
    ("Extracto de vainilla 2x",     "Saborizante",   0.0, 0.0,  0.0,  5.0, 0.00, 0.00, 95.0,
     "200+ aromáticos, vainillina, dosis 3-8g/kg",           "Aroma base universal",   0,  5.5),
    ("Vaina de vainilla (raspado)",  "Saborizante",  0.0, 0.0,  0.0,  8.0, 0.00, 0.00, 92.0,
     "Vainillina + aromáticos complejos, 1 vaina ≈ 5ml extracto","Premium aroma",      0,  5.5),
    ("Café espresso (líquido)",     "Saborizante",   0.0, 0.0,  0.5,  1.5, 0.01, 0.01, 98.0,
     "Clorogénico, cafeína, pH 5.0, dosis 50-100g/kg",      "Sabor café",             0,  5.0),
    ("Té matcha ceremonial",        "Saborizante",   5.3, 0.0,  0.0, 60.0, 0.00, 0.00, 34.7,
     "L-teanina, catequinas, clorofila, dosis 10-20g/kg",    "Gelato matcha",          0,  6.0),
    ("Canela en polvo",             "Saborizante",   1.2, 0.0,  2.2, 80.0, 0.02, 0.02, 10.0,
     "Cinamaldehído, trazas anticoagulante, dosis 1-3g/kg", "Aroma especiado",        0,  6.0),
    ("Cardamomo molido",            "Saborizante",   6.7, 0.0,  0.0, 60.0, 0.00, 0.00, 20.0,
     "Aceite esencial cineol, muy potente, dosis <1g/kg",    "Aroma floral especiado", 0,  6.0),

    # ══════════════════════════════════════════════════════════════════════════
    # INCLUSION
    # ══════════════════════════════════════════════════════════════════════════
    ("Nueces picadas",              "Inclusion",    65.0, 0.0,  3.5, 14.0, 0.04, 0.04, 13.5,
     "Omega-3, tostadas potencian sabor",                    "Textura crujiente",      0,  6.5),
    ("Almendras fileteadas",        "Inclusion",    49.0, 0.0,  4.3, 20.0, 0.04, 0.04, 20.0,
     "Monoinsaturadas, tostadas o crudas",                   "Textura, sabor",         0,  6.5),
    ("Granola (mix estándar)",      "Inclusion",    11.0, 0.0, 28.0, 40.0, 0.28, 0.28, 10.0,
     "Avena+miel+aceite, variado en azúcar",                 "Textura crujiente swirl",0,  6.0),
    ("Dulce de leche",              "Inclusion",     7.5, 8.0, 45.0,  2.0, 0.45, 0.45, 37.5,
     "Maillard de leche+azúcar, POD~0.45",                   "Swirl, saborizante",     0,  6.5),
    ("Mermelada de fresa",          "Inclusion",     0.0, 0.0, 55.0,  1.5, 0.55, 0.77, 43.5,
     "Pectina HM, Brix 60-65°, swirl o ripple",              "Swirl frutal",          62,  3.2),
    ("Galleta tipo Oreo (triturada)","Inclusion",   21.0, 0.0, 48.0, 15.0, 0.48, 0.48, 16.0,
     "Cacao alcalinizado+azúcar+grasa",                      "Mix-in clásico",         0,  7.0),
    ("Caramelo líquido (salted)",   "Inclusion",     5.0, 0.0, 75.0,  0.5, 0.75, 1.05, 19.5,
     "Maillard de sacarosa+crema+sal",                       "Swirl caramelo",        70,  5.0),

    # ══════════════════════════════════════════════════════════════════════════
    # ALCOHOL
    # ══════════════════════════════════════════════════════════════════════════
    ("Ron añejo 40% vol",           "Alcohol",  0.0, 0.0,  0.0,  0.2, 0.00, 3.50, 57.8,
     "Etanol PAC=3.5, dosis segura ≤50g/kg mix",             "Aroma, suaviza textura", 0,  7.0),
    ("Amaretto 28% vol",            "Alcohol",  0.0, 0.0, 25.0,  0.5, 0.25, 2.30, 74.5,
     "Almendra amarga+azúcar, dosis ≤40g/kg",               "Aroma almendra",         0,  7.0),
    ("Baileys 17% vol",             "Alcohol",  9.0, 0.0, 15.0,  1.0, 0.15, 1.50, 75.0,
     "Crema+whisky, MG real afecta grasa",                   "Aroma irlandés cremoso", 0,  7.0),
    ("Kahlúa 20% vol",              "Alcohol",  0.0, 0.0, 30.0,  1.0, 0.30, 1.80, 68.0,
     "Café+azúcar+vodka",                                    "Aroma café dulce",       0,  7.0),

    # ══════════════════════════════════════════════════════════════════════════
    # ÁCIDO Y MINERAL
    # ══════════════════════════════════════════════════════════════════════════
    ("Ácido cítrico en polvo",      "Ácido y mineral",0.0, 0.0, 0.0, 99.5, 0.00, 0.00,  0.5,
     "Acidulante, activa pectina HM, dosis 1-3g/kg",         "Ajuste pH, equilibrio",  0,  2.0),
    ("Ácido málico",                "Ácido y mineral",0.0, 0.0, 0.0, 99.5, 0.00, 0.00,  0.5,
     "Más suave que cítrico, sabor manzana, pH bajo",        "Acidez fina frutal",     0,  2.0),
    ("Sal marina fina",             "Ácido y mineral",0.0, 0.0, 0.0, 99.5, 0.00, 2.20,  0.5,
     "NaCl PAC=2.2!, potenciador sabor, dosis 1-2g/kg",      "Contraste dulce, PAC",   0,  7.0),
    ("Bicarbonato de sodio",        "Ácido y mineral",0.0, 0.0, 0.0, 99.0, 0.00, 0.00,  1.0,
     "Neutralizador de acidez, dosis <1g/kg",                "Ajuste pH base",         0, 11.0),
]


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_connection()
    conn.executescript(SCHEMA)

    applied = {
        row[0]
        for row in conn.execute("SELECT version FROM schema_migrations").fetchall()
    }
    for version, sql, description in MIGRATIONS:
        if version not in applied:
            try:
                conn.execute(sql)
                conn.execute(
                    "INSERT INTO schema_migrations (version, description) VALUES (?, ?)",
                    (version, description)
                )
                conn.commit()
            except Exception as e:
                conn.execute(
                    "INSERT OR IGNORE INTO schema_migrations (version, description) VALUES (?, ?)",
                    (version, f"{description} [ya existía: {e}]")
                )
                conn.commit()

    # ── Seed incremental ─────────────────────────────────────────────────────
    # Se ejecuta siempre que la migración _SEED_MIGRATION_VERSION esté aplicada.
    # INSERT OR IGNORE: inserta solo ingredientes cuyo nombre no exista todavía.
    # Esto garantiza que los nuevos ingredientes del DB_DATA llegan a bases de datos
    # existentes (ya con datos), sin tocar ningún ingrediente personalizado del usuario.
    seed_applied = _SEED_MIGRATION_VERSION in {
        row[0] for row in conn.execute("SELECT version FROM schema_migrations").fetchall()
    }
    if seed_applied:
        conn.executemany(
            "INSERT OR IGNORE INTO ingredients "
            "(name,category,fat,msnf,sugars,other_st,pod,pac,water,notes,function,brix,ph) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            DB_DATA
        )
    conn.commit()
    conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# INGREDIENTES
# ─────────────────────────────────────────────────────────────────────────────

def get_all_ingredients():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM ingredients ORDER BY category, name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_ingredient_by_name(name):
    conn = get_connection()
    row = conn.execute("SELECT * FROM ingredients WHERE name=?", (name,)).fetchone()
    conn.close()
    return dict(row) if row else None


def save_ingredient(data):
    conn = get_connection()
    if data.get('id'):
        conn.execute("""UPDATE ingredients SET name=?,category=?,fat=?,msnf=?,sugars=?,
            other_st=?,pod=?,pac=?,water=?,notes=?,function=?,brix=?,ph=?,
            price_per_kg=?,calories_per_100g=?,zero_calorie=?
            WHERE id=?""",
            (data['name'], data['category'], data['fat'], data['msnf'], data['sugars'],
             data['other_st'], data['pod'], data['pac'], data['water'],
             data['notes'], data['function'], data.get('brix', 0), data.get('ph', 0),
             data.get('price_per_kg', 0), data.get('calories_per_100g', 0),
             data.get('zero_calorie', 0), data['id']))
    else:
        conn.execute("""INSERT INTO ingredients
            (name,category,fat,msnf,sugars,other_st,pod,pac,water,notes,function,brix,ph,
             price_per_kg,calories_per_100g,zero_calorie)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (data['name'], data['category'], data['fat'], data['msnf'], data['sugars'],
             data['other_st'], data['pod'], data['pac'], data['water'],
             data['notes'], data['function'], data.get('brix', 0), data.get('ph', 0),
             data.get('price_per_kg', 0), data.get('calories_per_100g', 0),
             data.get('zero_calorie', 0)))
    conn.commit()
    conn.close()


def update_ingredient(ing_id, data):
    data['id'] = ing_id
    save_ingredient(data)


def delete_ingredient(ing_id):
    conn = get_connection()
    conn.execute("DELETE FROM ingredients WHERE id=?", (ing_id,))
    conn.commit()
    conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# RECETAS Y BASES DE HELADO
# is_base=0 → receta final   |   is_base=1 → base de helado (concentrado)
# ─────────────────────────────────────────────────────────────────────────────

def get_all_recipes(bases_only=False, recipes_only=False):
    conn = get_connection()
    if bases_only:
        rows = conn.execute(
            "SELECT * FROM recipes WHERE is_base=1 ORDER BY updated_at DESC"
        ).fetchall()
    elif recipes_only:
        rows = conn.execute(
            "SELECT * FROM recipes WHERE is_base=0 ORDER BY updated_at DESC"
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM recipes ORDER BY is_base DESC, updated_at DESC"
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_recipe(recipe_id):
    conn = get_connection()
    rec = conn.execute("SELECT * FROM recipes WHERE id=?", (recipe_id,)).fetchone()
    if not rec:
        conn.close()
        return None
    lines = conn.execute(
        "SELECT * FROM recipe_lines WHERE recipe_id=? ORDER BY sort_order",
        (recipe_id,)
    ).fetchall()
    conn.close()
    result = dict(rec)
    result['lines'] = [dict(l) for l in lines]
    return result


def save_recipe(data):
    conn = get_connection()
    rec_id  = data.get('id')
    is_base = int(data.get('is_base', 0))
    if rec_id:
        conn.execute("""UPDATE recipes SET name=?,product_type=?,machine=?,base_grams=?,
            notes=?,tasting_notes=?,is_base=?,updated_at=CURRENT_TIMESTAMP WHERE id=?""",
            (data['name'], data['product_type'], data['machine'], data['base_grams'],
             data.get('notes', ''), data.get('tasting_notes', ''), is_base, rec_id))
        conn.execute("DELETE FROM recipe_lines WHERE recipe_id=?", (rec_id,))
    else:
        cur = conn.execute("""INSERT INTO recipes
            (name,product_type,machine,base_grams,notes,tasting_notes,is_base)
            VALUES (?,?,?,?,?,?,?)""",
            (data['name'], data['product_type'], data['machine'], data['base_grams'],
             data.get('notes', ''), data.get('tasting_notes', ''), is_base))
        rec_id = cur.lastrowid
    for i, line in enumerate(data.get('lines', [])):
        conn.execute("""INSERT INTO recipe_lines (recipe_id,ingredient_name,grams,price_per_kg,sort_order)
            VALUES (?,?,?,?,?)""",
            (rec_id, line['ingredient_name'], line['grams'],
             line.get('price_per_kg', 0), i))
    conn.commit()
    conn.close()
    return rec_id


def update_recipe(recipe_id, data):
    data['id'] = recipe_id
    save_recipe(data)


def delete_recipe(recipe_id):
    conn = get_connection()
    conn.execute("DELETE FROM recipes WHERE id=?", (recipe_id,))
    conn.commit()
    conn.close()


def get_bases_as_ingredients():
    """
    Retorna las bases de helado guardadas formateadas como ingredientes,
    para que puedan usarse directamente en el formulador como ingrediente compuesto.
    Calcula fat/msnf/sugars/water/pod/pac desde sus líneas constituyentes.
    """
    conn = get_connection()
    bases = conn.execute("SELECT * FROM recipes WHERE is_base=1").fetchall()
    result = []
    for base in bases:
        bid = base['id']
        lines = conn.execute(
            "SELECT * FROM recipe_lines WHERE recipe_id=?", (bid,)
        ).fetchall()

        # Reconstruir totales desde líneas
        totals = dict(grams=0, fat=0, msnf=0, sugars=0, other_st=0,
                      pod=0, pac=0, water=0)
        for line in lines:
            ing_row = conn.execute(
                "SELECT * FROM ingredients WHERE name=?",
                (line['ingredient_name'],)
            ).fetchone()
            if not ing_row:
                continue
            g = float(line['grams'])
            totals['grams']    += g
            totals['fat']      += g * float(ing_row['fat'])      / 100
            totals['msnf']     += g * float(ing_row['msnf'])     / 100
            totals['sugars']   += g * float(ing_row['sugars'])   / 100
            totals['other_st'] += g * float(ing_row['other_st']) / 100
            totals['pod']      += g * float(ing_row['pod'])
            totals['pac']      += g * float(ing_row['pac'])
            totals['water']    += g * float(ing_row['water'])    / 100

        m = totals['grams']
        if m <= 0:
            continue

        result.append({
            'id':              f"base_{bid}",
            'name':            f"🧪 Base: {base['name']}",
            'category':        "Base de helado",
            'fat':             round(totals['fat']      / m * 100, 2),
            'msnf':            round(totals['msnf']     / m * 100, 2),
            'sugars':          round(totals['sugars']   / m * 100, 2),
            'other_st':        round(totals['other_st'] / m * 100, 2),
            'pod':             round(totals['pod']      / m,       4),
            'pac':             round(totals['pac']      / m,       4),
            'water':           round(totals['water']    / m * 100, 2),
            'notes':           f"Base guardada: {base['name']} · {m:.0f}g",
            'function':        'Base de helado compuesta',
            'brix':            0,
            'ph':              0,
            'price_per_kg':    0,
            'calories_per_100g': 0,
            'zero_calorie':    0,
        })
    conn.close()
    return result


if __name__ == "__main__":
    init_db()
    print("DB initialized:", DB_PATH)
    ings = get_all_ingredients()
    print(f"Ingredientes: {len(ings)}")
    bases = get_all_recipes(bases_only=True)
    print(f"Bases de helado: {len(bases)}")

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURACIÓN DE USUARIO
# Persiste los rangos objetivo personalizados (config_params en session_state)
# en SQLite para que sobrevivan reinicios de Railway y cierres de navegador.
# key   = "{product_type}_{machine}"  ej: "Helado/Gelato_Ninja Creami Deluxe"
# value = JSON string del dict de rangos  ej: '{"st": [28, 38], "fat": [4, 15], ...}'
# ─────────────────────────────────────────────────────────────────────────────

import json as _json

def get_user_config() -> dict:
    """Carga toda la configuración guardada. Retorna dict {key: dict_de_rangos}."""
    try:
        conn = get_connection()
        rows = conn.execute("SELECT key, value FROM user_config").fetchall()
        conn.close()
        result = {}
        for row in rows:
            try:
                result[row["key"]] = _json.loads(row["value"])
            except Exception:
                pass  # fila corrupta → ignorar
        return result
    except Exception:
        return {}


def set_user_config(key: str, value: dict) -> None:
    """Guarda o actualiza un rango personalizado para la combinación tipo/máquina."""
    try:
        conn = get_connection()
        conn.execute(
            """INSERT INTO user_config (key, value, updated_at)
               VALUES (?, ?, CURRENT_TIMESTAMP)
               ON CONFLICT(key) DO UPDATE SET
                 value      = excluded.value,
                 updated_at = CURRENT_TIMESTAMP""",
            (key, _json.dumps(value))
        )
        conn.commit()
        conn.close()
    except Exception:
        pass


def delete_user_config(key: str) -> None:
    """Elimina la config personalizada de una combinación tipo/máquina."""
    try:
        conn = get_connection()
        conn.execute("DELETE FROM user_config WHERE key=?", (key,))
        conn.commit()
        conn.close()
    except Exception:
        pass
