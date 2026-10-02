"""
Initialise PostgreSQL et insère les cultures + maladies de départ.
À lancer UNE FOIS au début du projet : python init_db.py
"""
from pathlib import Path

from db import DATABASE_URL, get_conn

SCHEMA_PATH = Path(__file__).parent / "data" / "db" / "schema.sql"

# (crop, disease_name, class_label, symptoms, causes, prevention, treatment, severity, doc_source)
DISEASES = [
    ("tomate", "Mildiou", "tomato_mildiou",
     "Taches brunes irrégulières avec halo jaune, duvet blanc au revers des feuilles.",
     "Champignon favorisé par l'humidité élevée et les températures douces.",
     "Aérer les plants, éviter l'aspersion, rotation des cultures.",
     "Bouillie bordelaise (cuivre) en préventif, fongicide systémique si sévère.",
     "haute", "tomate_mildiou.md"),
    ("tomate", "Alternariose", "tomato_alternariose",
     "Taches brunes en anneaux concentriques, jaunissement autour.",
     "Champignon du sol, alternance pluie/chaleur.",
     "Paillage, fertilisation équilibrée, rotation 2-3 ans.",
     "Suppression des feuilles atteintes, fongicide cuivre/chlorothalonil.",
     "moyenne", "tomate_alternariose.md"),
    ("pomme de terre", "Mildiou", "potato_mildiou",
     "Taches brun-vert huileuses, feutrage blanc au revers, tubercules tachés.",
     "Même agent que le mildiou de la tomate, favorisé par le froid humide.",
     "Plants certifiés, buttage, espacement suffisant.",
     "Cuivre en préventif, fongicide systémique en curatif.",
     "haute", "pomme_terre_mildiou.md"),
    ("olivier", "Œil de paon", "olive_oeil_de_paon",
     "Taches circulaires brun-noir avec halo jaune, chute prématurée des feuilles.",
     "Champignon conservé sur feuilles tombées, favorisé par l'humidité hivernale.",
     "Taille pour aérer, ramassage des feuilles mortes.",
     "Traitement cuivre en automne avant les pluies.",
        "moyenne", "olivier_oeil_paon.md"),
        ("concombre", "Oïdium", "cucumber_powdery_mildew",
        "Feutrage blanc poudreux sur les feuilles, jaunissement et perte de vigueur.",
        "Humidité élevée, écarts de température et circulation d'air insuffisante.",
        "Espacer les plants, aérer, arroser au pied et éviter l'excès d'azote.",
        "Produit fongicide autorisé pour le concombre, selon l'étiquette.",
        "moyenne", "concombre_oidium.md"),
        ("vigne", "Mildiou", "grape_downy_mildew",
        "Taches jaune-vert sur les feuilles, duvet blanc au revers et dessèchement des jeunes baies.",
        "Oomycète favorisé par les pluies, l'humidité persistante et les tissus jeunes.",
        "Favoriser l'aération, limiter l'humidité du feuillage et surveiller après les pluies.",
        "Produit autorisé pour la vigne, selon l'étiquette et les recommandations locales.",
        "haute", "vigne_mildiou.md"),
]

CROPS = sorted({d[0] for d in DISEASES})


def main():
    with get_conn() as conn:
        cur = conn.cursor()
        for statement in SCHEMA_PATH.read_text(encoding="utf-8").split(";"):
            statement = statement.strip()
            if statement:
                cur.execute(statement)

        crop_ids = {}
        for crop in CROPS:
            cur.execute(
                "INSERT INTO crops (name) VALUES (%s) ON CONFLICT (name) DO NOTHING",
                (crop,),
            )
            cur.execute("SELECT id FROM crops WHERE name = %s", (crop,))
            crop_ids[crop] = cur.fetchone()["id"]

        for (crop, name, class_label, symptoms, causes, prevention,
             treatment, severity, doc_source) in DISEASES:
            cur.execute(
                """INSERT INTO diseases
                   (crop_id, name, class_label, symptoms, causes, prevention,
                    treatment, severity, doc_source)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                   ON CONFLICT (class_label) DO NOTHING""",
                (crop_ids[crop], name, class_label, symptoms, causes,
                 prevention, treatment, severity, doc_source),
            )

        conn.commit()
    print(f"Base PostgreSQL créée / mise à jour : {DATABASE_URL}")
    print(f"   Cultures insérées : {CROPS}")
    print(f"   Maladies insérées : {[d[2] for d in DISEASES]}")


if __name__ == "__main__":
    main()
