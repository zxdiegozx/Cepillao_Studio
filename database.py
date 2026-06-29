import sqlite3, os
from constants import MACHINE_CREAMI_DELUXE

# FIX B4: DB_PATH ahora lee RAILWAY_VOLUME_MOUNT_PATH correctamente.
# En Railway con volumen montado: guarda en /data/gelato.db (persistente).
# En desarrollo local o sin volumen: guarda junto al script (comportamiento anterior).
_vol  = os.environ.get("RAILWAY_VOLUME_MOUNT_PATH", "").strip()
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

-- T3: índice explícito en name para búsquedas frecuentes por nombre
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

-- T6: registro de versiones de migración aplicadas
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    description TEXT NOT NULL
);
"""

# T6: migraciones con versión explícita.
# Cada entrada: (version, sql, description)
# Nunca modificar entradas ya aplicadas — solo añadir nuevas al final.
MIGRATIONS = [
    (1, "ALTER TABLE ingredients ADD COLUMN price_per_kg REAL DEFAULT 0",
        "Añade precio por kg a ingredientes"),
    (2, "ALTER TABLE ingredients ADD COLUMN calories_per_100g REAL DEFAULT 0",
        "Añade calorías por 100g a ingredientes"),
    (3, "ALTER TABLE ingredients ADD COLUMN zero_calorie INTEGER DEFAULT 0",
        "Añade flag zero_calorie a ingredientes"),
]

DB_DATA = [
    # name, cat, fat, msnf, sugars, other_st, pod, pac, water, notes, function, brix, ph
    ("Leche entera 3.5%","Lácteo",3.5,9.0,4.7,0.0,0.10,0.10,82.8,"Emulsión O/W natural, lactosa 4.7%, pH 6.6","Base principal",0,6.6),
    ("Leche descremada 0.1%","Lácteo",0.1,9.5,4.8,0.0,0.10,0.10,85.6,"Alta MSNF sin grasa","Base baja grasa",0,6.6),
    ("Leche concentrada s/a","Lácteo",7.5,20.0,11.0,0.0,0.22,0.22,61.5,"MSNF concentrado 2.5x","Aumentar sólidos lácteos",0,6.5),
    ("Crema 35% MG","Lácteo",35.0,6.0,3.5,0.0,0.04,0.04,55.5,"Globos grasos 3-8µm, pasteurizar 85°C/15s","Fuente grasa primaria",0,6.5),
    ("Crema 45% MG","Lácteo",45.0,4.5,2.8,0.0,0.03,0.03,47.7,"Ultra-grasa, semifreddo","Grasa máxima",0,6.5),
    ("Leche en polvo entera","Lácteo",26.0,38.0,37.5,0.0,0.38,0.38,1.0,"Higroscópica, añadir al final","Concentrar MSNF+ST",0,6.8),
    ("Leche en polvo descremada","Lácteo",1.0,52.0,50.0,0.0,0.50,0.50,3.0,"Proteínas 34%, lactosa 50%","Aumentar MSNF sin grasa",0,6.8),
    ("Mantequilla 82% MG","Lácteo",82.0,1.5,0.6,0.0,0.01,0.01,15.9,"Cristalización Form β'","Ajuste fino grasa",0,6.5),
    ("Mascarpone 41% MG","Lácteo",41.0,5.0,3.5,0.0,0.04,0.04,50.5,"Ácido cítrico, pH 5.5","Gelato ricco",0,5.5),
    ("Queso crema 30% MG","Lácteo",30.0,8.0,3.8,0.0,0.04,0.04,58.2,"Philadelphia-style, pH 4.5-5.0","Textura densa",0,4.8),
    ("Yogur entero 3.5%","Lácteo",3.5,9.0,4.7,0.0,0.10,0.10,82.8,"Ácido láctico, pH 4.0-4.5","Acidez, frescura",0,4.2),
    ("Suero de leche (whey)","Lácteo",0.3,10.0,5.0,0.0,0.10,0.10,84.7,"Proteínas WPC, funcional","Estructura proteica",0,6.5),
    ("Sacarosa","Azúcar",0.0,0.0,100.0,0.0,1.00,1.00,0.0,"Referencia absoluta POD=PAC=1.0","Base de dulzor",0,7.0),
    ("Dextrosa monohidrato","Azúcar",0.0,0.0,91.0,0.0,0.75,1.90,9.0,"MW=198, PAC=1.9x! Crioscópica potente","Bajar punto congelación",0,7.0),
    ("Glucosa atomizada DE40","Azúcar",0.0,0.0,95.0,0.0,0.50,0.64,5.0,"Antirecristalizante, sinergia con sacarosa","Textura, anti-cristal",0,7.0),
    ("Glucosa atomizada DE60","Azúcar",0.0,0.0,95.0,0.0,0.70,0.90,5.0,"Mayor dulzor que DE40","Balance dulzor/textura",0,7.0),
    ("Fructosa","Azúcar",0.0,0.0,99.5,0.0,1.20,1.90,0.5,"POD>sacarosa en frío, ideal sorbetes","Dulzor potenciado",0,7.0),
    ("Trehalosa","Azúcar",0.0,0.0,99.5,0.0,0.45,0.70,0.5,"Protege proteínas y membranas celulares","Estabilidad, Pacojet",0,7.0),
    ("Isomalt","Azúcar",0.0,0.0,98.5,0.0,0.45,0.70,1.5,"0 caries, bajo IG","Reducir azúcar",0,7.0),
    ("Azúcar invertido","Azúcar",0.0,0.0,75.0,0.0,1.30,1.90,25.0,"Fructosa+glucosa libres, higroscópico","Antirecristalizante",0,7.0),
    ("Miel de abeja","Azúcar",0.0,0.0,80.0,1.0,1.00,1.50,19.0,"Fructosa+glucosa 70%, polifenoles","Dulzor floral",0,3.9),
    ("Eritritol","Azúcar",0.0,0.0,99.5,0.0,0.65,1.30,0.5,"0 cal, buen PAC, refrescante","Low-calorie",0,7.0),
    ("Mango Ataulfo (pulpa)","Fruta tropical",0.4,0.0,14.0,0.8,0.14,0.20,84.8,"Brix 18-22°, pH 3.9, β-caroteno","Sorbete tropical",20,3.9),
    ("Maracuyá (pulpa)","Fruta tropical",0.4,0.0,11.0,1.5,0.11,0.16,87.1,"Filtrada sin semilla, Brix 14-16°","Sorbete limpio",15,3.1),
    ("Guanábana (pulpa)","Fruta tropical",0.3,0.0,13.5,3.5,0.14,0.16,82.7,"Fibra 3.5%, pH 3.5, untuosa","Sorbete cremoso vegano",14,3.5),
    ("Piña Golden (pulpa)","Fruta tropical",0.2,0.0,16.0,0.7,0.16,0.22,83.1,"Bromelina activa, tamizar","Sorbete refrescante",15,3.5),
    ("Banana madura (pulpa)","Fruta tropical",0.3,0.0,17.0,2.8,0.17,0.22,79.9,"Almidón→azúcar, pectina","Cuerpo, dulzor natural",18,4.8),
    ("Leche de coco 17-18%","Fruta tropical",17.5,0.0,3.8,1.5,0.04,0.05,77.2,"Emulsión natural, ácido láurico","Base gelato vegano",0,6.5),
    ("Crema de coco 22-24%","Fruta tropical",23.0,0.0,4.0,2.0,0.04,0.06,71.0,"Ultra-grasa vegetal","Gelato vegano premium",0,6.5),
    ("Aguacate (pulpa)","Fruta tropical",15.0,0.0,0.7,3.0,0.01,0.01,81.3,"66% MG monoins., cremosidad","Gelato vegano untuoso",0,6.3),
    ("Tamarindo (pulpa)","Fruta tropical",0.6,0.0,38.0,5.5,0.38,0.55,55.9,"Muy dulce+ácido, ácido tartárico","Sorbete agridulce",55,3.0),
    ("Lichi (pulpa)","Fruta tropical",0.4,0.0,16.0,0.5,0.16,0.22,83.1,"Aroma floral, pH 4.1","Sorbete floral",16,4.1),
    ("Papaya (pulpa)","Fruta tropical",0.3,0.0,8.3,0.9,0.08,0.11,90.5,"Papaína activa, β-caroteno","Sorbete suave",9,5.8),
    ("Fresa (pulpa fresca)","Fruta europea",0.3,0.0,7.7,0.5,0.08,0.11,91.5,"Antocianos, pH 3.0-3.5, Brix 8-11°","Sorbete clásico",9,3.2),
    ("Frambuesa (pulpa)","Fruta europea",0.7,0.0,5.4,2.8,0.05,0.07,91.1,"Muy ácida pH 2.8-3.2","Sorbete intenso",7,3.0),
    ("Arándano (blueberry)","Fruta europea",0.3,0.0,10.0,0.8,0.10,0.14,88.9,"Antocianos altos, pH 3.1-3.3","Sorbete antioxidante",11,3.2),
    ("Mora (blackberry)","Fruta europea",0.5,0.0,9.6,2.2,0.10,0.13,87.7,"Antocianos, pepitas→tamizar","Sorbete oscuro",10,3.2),
    ("Cereza dulce (pulpa)","Fruta europea",0.2,0.0,12.8,0.5,0.13,0.18,86.5,"Brix 15-19°, pH 3.8-4.2","Sorbete suave",17,4.0),
    ("Durazno/Melocotón","Fruta europea",0.3,0.0,9.5,0.8,0.10,0.13,89.4,"Ácido málico, β-caroteno","Sorbete aromático",10,3.7),
    ("Limón (jugo fresco)","Fruta europea",0.3,0.0,2.5,0.3,0.03,0.04,96.9,"pH 2.0-2.6, ácido cítrico 5-8%","Acidez, equilibrio",9,2.3),
    ("Lima (jugo fresco)","Fruta europea",0.2,0.0,1.7,0.2,0.02,0.03,97.9,"pH 2.0-2.4, aromática","Acidez fina",9,2.2),
    ("Naranja (jugo fresco)","Fruta europea",0.2,0.0,9.4,0.4,0.09,0.13,90.0,"pH 3.5-4.0, hesperidina","Sorbete cítrico",11,3.7),
    ("Naranja sanguina","Fruta europea",0.2,0.0,9.8,0.4,0.10,0.13,89.6,"Antocianos únicos, pH 3.2-3.8","Sorbete visual",11,3.5),
    ("Kiwi (pulpa)","Fruta europea",0.5,0.0,9.0,1.2,0.09,0.12,89.3,"Actinidina (proteasa), pH 3.1","Sorbete vibrante",10,3.1),
    ("Granada (arils)","Fruta europea",1.2,0.0,13.7,0.5,0.14,0.19,84.6,"Punicalagina, pH 3.0","Sorbete rojo vivo",14,3.0),
    ("Pasta pistache (pura)","Pasta frutos secos",45.0,0.0,7.5,20.0,0.08,0.08,27.5,"53% MG insaturada, clorofila","Gelato pistacchio",0,6.5),
    ("Pasta avellana (pura)","Pasta frutos secos",61.0,0.0,4.0,14.0,0.04,0.04,21.0,"Oleico 75%, aroma tostado","Gelato nocciola",0,6.5),
    ("Pasta almendra (pura)","Pasta frutos secos",51.0,0.0,4.5,17.5,0.05,0.05,27.0,"Oleico 70%, amandina","Gelato mandorla",0,6.8),
    ("Cacao polvo alcalino 10%","Cacao/Chocolate",11.0,0.0,0.0,58.0,0.00,0.00,31.0,"pH 7.5-8.5, Dutched, oscuro","Sabor choco suave",0,8.0),
    ("Cacao polvo natural 10%","Cacao/Chocolate",10.0,0.0,0.0,55.0,0.00,0.00,35.0,"pH 5.0-6.0, rojizo, ácido","Sabor choco vivo",0,5.5),
    ("Pasta de cacao 100%","Cacao/Chocolate",54.0,0.0,0.0,18.0,0.00,0.00,28.0,"Manteca 54%, theobromina","Cacao puro profundo",0,5.5),
    ("Cobertura negra 70%","Cacao/Chocolate",42.0,0.0,29.0,16.0,0.29,0.29,13.0,"Form V manteca, temperado","Chunk, base premium",0,5.5),
    ("Cobertura leche 38%","Cacao/Chocolate",35.0,4.0,46.0,8.0,0.46,0.46,7.0,"Leche en polvo, dulce","Gelato latte",0,5.5),
    ("Manteca de cacao","Cacao/Chocolate",99.5,0.0,0.0,0.0,0.00,0.00,0.5,"Grasa pura Form V","Ajuste grasa/textura",0,7.0),
    ("Té matcha ceremonial","Café/Té/Aroma",5.3,0.0,0.0,60.0,0.00,0.00,34.7,"L-teanina, catequinas, clorofila","Gelato matcha",0,6.0),
    ("Café espresso (líquido)","Café/Té/Aroma",0.0,0.0,0.5,1.5,0.01,0.01,98.0,"Clorogénico, cafeína, pH 5.0","Sabor café",0,5.0),
    ("Extracto de vainilla 2x","Café/Té/Aroma",0.0,0.0,0.0,5.0,0.00,0.00,95.0,"200+ aromáticos, vainillina","Aromatizante base",0,5.5),
    ("Ron añejo (40% vol)","Alcohol",0.0,0.0,0.0,0.2,0.00,3.50,57.8,"Etanol PAC=3.5, dosis ≤50g/kg","Aroma, suaviza textura",0,7.0),
    ("Amaretto (28% vol)","Alcohol",0.0,0.0,25.0,0.5,0.25,2.30,74.5,"Almendra amarga + azúcar","Aroma almendra",0,7.0),
    ("Limoncello (30% vol)","Alcohol",0.0,0.0,28.0,0.2,0.28,2.50,71.8,"Limoneno, azúcar alta","Sorbete adulto",0,7.0),
    ("Neutro LBG+Guar+κ-Carr","Estabilizante",0.0,0.0,0.0,99.5,0.00,0.00,0.5,"Dosis 3-5g/kg, sinergia LBG+κ","Estructura, overrun",0,7.0),
    ("Goma Guar","Estabilizante",0.0,0.0,0.0,99.0,0.00,0.00,1.0,"Dosis 0.1-0.2g/kg, soluble en frío","Sorbetes, viscosidad",0,7.0),
    ("Goma Xantana","Estabilizante",0.0,0.0,0.0,99.0,0.00,0.00,1.0,"Dosis 0.1-0.2g/kg, pseudoplástica","Estabilidad universal",0,7.0),
    ("Inulina HP","Estabilizante",0.0,0.0,0.0,94.0,0.00,0.00,6.0,"Prebiótico, reemplaza grasa","Grasa mimética vegana",0,7.0),
    ("Lecitina de girasol","Emulsionante",0.0,0.0,0.0,99.0,0.00,0.00,1.0,"HLB 4, fosfatidilcolina, dosis 2-5g/kg","Emulsión, overrun",0,7.0),
    ("Yema de huevo fresca","Emulsionante",32.0,0.0,0.6,18.0,0.01,0.01,49.4,"Lecitina natural, pasteurizar 72°C","Emulsión perfecta",0,6.5),
    ("Sal marina fina","Funcional",0.0,0.0,0.0,99.5,0.00,2.20,0.5,"NaCl PAC=2.2!, potenciador sabor","Contraste dulce, PAC",0,7.0),
    ("Ácido cítrico (polvo)","Funcional",0.0,0.0,0.0,99.5,0.00,0.00,0.5,"Acidulante, activa pectina HM","Ajuste pH",0,2.0),
    ("Agua destilada","Base",0.0,0.0,0.0,0.0,0.00,0.00,100.0,"Diluyente neutro","Dilución, ajuste",0,7.0),
]

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_connection()
    conn.executescript(SCHEMA)

    # T6: migraciones versionadas — cada versión se aplica exactamente una vez
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

    # Seed de ingredientes si la tabla está vacía
    count = conn.execute("SELECT COUNT(*) FROM ingredients").fetchone()[0]
    if count == 0:
        conn.executemany(
            "INSERT OR IGNORE INTO ingredients "
            "(name,category,fat,msnf,sugars,other_st,pod,pac,water,notes,function,brix,ph) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            DB_DATA
        )
    conn.commit()
    conn.close()

def get_all_ingredients():
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM ingredients ORDER BY category, name"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_ingredient_by_name(name):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM ingredients WHERE name=?", (name,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None

def save_ingredient(data):
    conn = get_connection()
    if data.get('id'):
        conn.execute("""UPDATE ingredients SET name=?,category=?,fat=?,msnf=?,sugars=?,
            other_st=?,pod=?,pac=?,water=?,notes=?,function=?,brix=?,ph=?,
            price_per_kg=?,calories_per_100g=?,zero_calorie=?
            WHERE id=?""",
            (data['name'],data['category'],data['fat'],data['msnf'],data['sugars'],
             data['other_st'],data['pod'],data['pac'],data['water'],
             data['notes'],data['function'],data.get('brix',0),data.get('ph',0),
             data.get('price_per_kg',0),data.get('calories_per_100g',0),
             data.get('zero_calorie',0),data['id']))
    else:
        conn.execute("""INSERT INTO ingredients
            (name,category,fat,msnf,sugars,other_st,pod,pac,water,notes,function,brix,ph,
             price_per_kg,calories_per_100g,zero_calorie)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (data['name'],data['category'],data['fat'],data['msnf'],data['sugars'],
             data['other_st'],data['pod'],data['pac'],data['water'],
             data['notes'],data['function'],data.get('brix',0),data.get('ph',0),
             data.get('price_per_kg',0),data.get('calories_per_100g',0),
             data.get('zero_calorie',0)))
    conn.commit()
    conn.close()

def delete_ingredient(ing_id):
    conn = get_connection()
    conn.execute("DELETE FROM ingredients WHERE id=?", (ing_id,))
    conn.commit(); conn.close()

def get_all_recipes():
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM recipes ORDER BY updated_at DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_recipe(recipe_id):
    conn = get_connection()
    rec = conn.execute("SELECT * FROM recipes WHERE id=?", (recipe_id,)).fetchone()
    if not rec:
        conn.close(); return None
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
    rec_id = data.get('id')
    if rec_id:
        conn.execute("""UPDATE recipes SET name=?,product_type=?,machine=?,base_grams=?,
            notes=?,tasting_notes=?,updated_at=CURRENT_TIMESTAMP WHERE id=?""",
            (data['name'],data['product_type'],data['machine'],data['base_grams'],
             data.get('notes',''),data.get('tasting_notes',''),rec_id))
        conn.execute("DELETE FROM recipe_lines WHERE recipe_id=?", (rec_id,))
    else:
        cur = conn.execute("""INSERT INTO recipes (name,product_type,machine,base_grams,notes,tasting_notes)
            VALUES (?,?,?,?,?,?)""",
            (data['name'],data['product_type'],data['machine'],data['base_grams'],
             data.get('notes',''),data.get('tasting_notes','')))
        rec_id = cur.lastrowid
    for i, line in enumerate(data.get('lines', [])):
        conn.execute("""INSERT INTO recipe_lines (recipe_id,ingredient_name,grams,price_per_kg,sort_order)
            VALUES (?,?,?,?,?)""",
            (rec_id, line['ingredient_name'], line['grams'],
             line.get('price_per_kg', 0), i))
    conn.commit(); conn.close()
    return rec_id

def delete_recipe(recipe_id):
    conn = get_connection()
    conn.execute("DELETE FROM recipes WHERE id=?", (recipe_id,))
    conn.commit(); conn.close()

if __name__ == "__main__":
    init_db()
    print("DB initialized:", DB_PATH)
    ings = get_all_ingredients()
    print(f"Ingredients: {len(ings)}")
