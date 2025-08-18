from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
import hashlib
import smtplib
import secrets
import config
from email.message import EmailMessage

app = Flask(__name__)
app.secret_key = config.SECRET_KEY
@app.template_filter('format_python_code')
def format_python_code(text):
    if not text:
        return text
    
    lines = text.split('\n')
    formatted_lines = []
    
    for line in lines:
        leading_spaces = len(line) - len(line.lstrip(' '))
        
        if leading_spaces > 0:
            indent = '&nbsp;' * leading_spaces
            content = line.lstrip(' ')
            formatted_line = indent + content
        else:
            formatted_line = line
        
        formatted_lines.append(formatted_line)
    
    return '<br>'.join(formatted_lines)

# Filtre pour les options simples
@app.template_filter('format_simple_text')
def format_simple_text(text):
    if not text:
        return text
    return text.replace('\n', '<br>')

SMTP_HOST = config.SMTP_HOST
SMTP_PORT = config.SMTP_PORT
SMTP_USER = config.SMTP_USER
SMTP_PASS = config.SMTP_PASS
FROM_EMAIL = config.FROM_EMAIL
TO_EMAIL   = config.TO_EMAIL

DATABASE = 'etudiants.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn

def init_db():
    conn = get_db_connection()
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS etudiants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            mot_de_passe TEXT NOT NULL,
            date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chapitre INTEGER NOT NULL,
            texte_question TEXT NOT NULL,
            option_a TEXT NOT NULL,
            option_b TEXT NOT NULL,
            option_c TEXT NOT NULL,
            option_d TEXT NOT NULL,
            bonne_reponse CHAR(1) NOT NULL,
            points INTEGER DEFAULT 10
        )
    ''')
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS tentatives_qcm (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            etudiant_id INTEGER NOT NULL,
            chapitre INTEGER NOT NULL,
            score INTEGER NOT NULL,
            total_questions INTEGER NOT NULL,
            date_tentative TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (etudiant_id) REFERENCES etudiants (id)
        )
    ''')
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS reponses_etudiant (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tentative_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            reponse_selectionnee CHAR(1) NOT NULL,
            est_correcte BOOLEAN NOT NULL,
            FOREIGN KEY (tentative_id) REFERENCES tentatives_qcm (id),
            FOREIGN KEY (question_id) REFERENCES questions (id)
        )
    ''')
    
    conn.execute('''
        CREATE INDEX IF NOT EXISTS ix_tentatives_etudiant 
        ON tentatives_qcm(etudiant_id)
    ''')
    
    conn.execute('''
        CREATE UNIQUE INDEX IF NOT EXISTS ux_reponses_tentative_question
        ON reponses_etudiant(tentative_id, question_id)
    ''')
    
    conn.commit()
    conn.close()

def hash_password(password):
    salt = secrets.token_hex(32)
    password_with_salt = password + salt
    hash_obj = hashlib.sha256(password_with_salt.encode())
    return salt + ':' + hash_obj.hexdigest()

def verify_password(password, stored_hash):
    try:
        salt, hash_part = stored_hash.split(':')
        password_with_salt = password + salt
        hash_obj = hashlib.sha256(password_with_salt.encode())
        return hash_obj.hexdigest() == hash_part
    except ValueError:
        return stored_hash == hashlib.sha256(password.encode()).hexdigest()

def init_chapter1_questions():
    conn = get_db_connection()
    
    existing = conn.execute('SELECT COUNT(*) FROM questions WHERE chapitre = 1').fetchone()[0]
    if existing > 0:
        conn.close()
        return
    
    questions_ch1 = [
        {
            'question': 'Laquelle utilise correctement une f-string pour afficher nom et age ? (si nom = "Alice" et age = 20)',
            'a': 'print("Bonjour {nom}, vous avez {age} ans")',
            'b': 'print(f"Bonjour {nom}, vous avez {age} ans")',
            'c': 'print(f"Bonjour {nom}, vous avez " + {age} + " ans")',
            'd': 'print(f\'Bonjour {nom}, vous avez {age} ans")',
            'correct': 'B'
        },
        {
            'question': 'Que retourne toujours input() ?',
            'a': 'int (nombre entier)',
            'b': 'float (nombre à virgule)',
            'c': 'str (chaîne de caractères)',
            'd': 'Le type dépend de ce que tape l\'utilisateur',
            'correct': 'C'
        },
        {
            'question': 'Quelle instruction demande un entier à l\'utilisateur et le convertit correctement ?',
            'a': 'age = input("Votre âge : ")',
            'b': 'age = int(input("Votre âge : "))',
            'c': 'int = input("Votre âge : ")',
            'd': 'age = input(int("Votre âge : "))',
            'correct': 'B'
        },
        {
            'question': 'L\'utilisateur saisit 1.75. Quel code affiche correctement la taille en cm ?',
            'a': 'taille = input("Votre taille en m : ")\nprint("Votre taille en cm est", taille*100)',
            'b': 'taille = float(input("Votre taille en m : "))\nprint("Votre taille en cm est", taille*100)',
            'c': 'taille = int(input("Votre taille en m : "))\nprint("Votre taille en cm est", taille*100)',
            'd': 'taille = float(input("Votre taille en m : "))\nprint("Votre taille en cm est " + taille*100)',
            'correct': 'B'
        },
        {
            'question': 'Que va exactement afficher le code suivant ?\nnom = "Alice"\nage = 20\nprint("Bonjour", nom, ", vous avez", age, "ans")',
            'a': 'Bonjour Alice, vous avez 20 ans',
            'b': 'Bonjour Alice , vous avez 20 ans',
            'c': 'Bonjour Alice ,vous avez 20 ans',
            'd': 'Bonjour Alice vous avez 20 ans',
            'correct': 'B'
        },
        {
            'question': 'Quelle séquence demande le prénom puis affiche "Bonjour [prénom]" ?',
            'a': 'nom = input("Votre prénom : ")\nprint("Bonjour", nom)',
            'b': 'nom = input("Votre prénom : ")\nprint("Bonjour " nom)',
            'c': 'print("Bonjour", input)',
            'd': 'nom = input\nprint("Bonjour", nom)',
            'correct': 'A'
        },
        {
            'question': 'Quel code affiche un même caractère saisi répété n fois ?',
            'a': 'char = input("Caractère ? ")\nn = int(input("Combien de fois ? "))\nprint(char * n)',
            'b': 'char = input("Caractère ? ")\nn = int(input("Combien de fois ? "))\nprint(char + n)',
            'c': 'char = input("Caractère ? ")\nn = int(input("Combien de fois ? "))\nprint(char * n + char)',
            'd': 'char = input("Caractère ? ")\nn = int(input("Combien de fois ? "))\nprint(char * (n - 1))',
            'correct': 'A'
        },
        {
            'question': 'Pour demander un nombre décimal à l\'utilisateur, quelle écriture est correcte ?',
            'a': 'x = input("Nombre : ")',
            'b': 'x = int(input("Nombre : "))',
            'c': 'x = float(input("Nombre : "))',
            'd': 'x = str(input("Nombre : "))',
            'correct': 'C'
        },
        {
            'question': 'Quel code affiche correctement "12 + 5 = 17" à partir de deux saisies ?',
            'a': 'a = input("Premier nombre : ")\nb = input("Deuxième nombre : ")\nprint(f"{a} + {b} = {a+b}")',
            'b': 'a = int(input("Premier nombre : "))\nb = int(input("Deuxième nombre : "))\nprint(f"{a} + {b} = {a+b}")',
            'c': 'a = input("Premier nombre : ")\nb = input("Deuxième nombre : ")\nprint(a, " + ", b, " = ", a - b)',
            'd': 'a = float(input("Premier nombre : "))\nb = float(input("Deuxième nombre : "))\nprint(f"{a} + {b} = {a*b}")',
            'correct': 'B'
        },
        {
            'question': 'Vous lisez un prix en CHF et devez l\'afficher en EUR avec le taux 1 CHF = 0.92 EUR. Quelle option est correcte ?',
            'a': 'chf = input("Prix en CHF : ")\neur = chf * 0.92\nprint(eur)',
            'b': 'chf = float(input("Prix en CHF : "))\neur = chf * 0.92\nprint(f"{chf} CHF = {eur} EUR")',
            'c': 'chf = int(input("Prix en CHF : "))\neur = str(chf * 0.92)\nprint("CHF en EUR =", eur)',
            'd': 'chf = float(input("Prix en CHF : "))\neur = chf + 0.92\nprint(f"{eur} EUR")',
            'correct': 'B'
        }
    ]
    
    for q in questions_ch1:
        conn.execute('''
            INSERT INTO questions (chapitre, texte_question, option_a, option_b, option_c, option_d, bonne_reponse)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (1, q['question'], q['a'], q['b'], q['c'], q['d'], q['correct']))
    
    conn.commit()
    conn.close()

def init_chapter2_questions():
    conn = get_db_connection()
    
    existing = conn.execute('SELECT COUNT(*) FROM questions WHERE chapitre = 2').fetchone()[0]
    if existing > 0:
        conn.close()
        return
    
    questions_ch2 = [
        {
            'question': 'Avec le code suivant, si age = 18, quel(s) message(s) s\'affiche(nt) ?\nage = 18\nif age >= 18:\n    print("Vous êtes majeur !")\n    print("Vous pouvez voter.")\nprint("Ce message s\'affiche toujours quel que soit ton âge.")',
            'a': 'Rien',
            'b': 'Seulement « Vous êtes majeur ! »',
            'c': '« Vous êtes majeur ! », « Vous pouvez voter. », puis le message final',
            'd': 'Seulement le message final',
            'correct': 'C'
        },
        {
            'question': 'Avec le code suivant, quel message s\'affiche ?\nage = 16\nif age >= 18:\n    print("Vous êtes majeur !")\n    print("Vous pouvez voter.")\nprint("Ce message s\'affiche toujours quel que soit ton âge.")',
            'a': '« Vous êtes majeur ! »',
            'b': '« Vous pouvez voter. »',
            'c': '« Vous êtes majeur ! » et « Vous pouvez voter. »',
            'd': '« Ce message s\'affiche toujours quel que soit ton âge. »',
            'correct': 'D'
        },
        {
            'question': 'Pour proposer une alternative lorsque la condition est fausse, quel schéma est correct ?',
            'a': 'if ... elif ...',
            'b': 'if ... else ...',
            'c': 'else ... if ...',
            'd': 'if ... then ... else ...',
            'correct': 'B'
        },
        {
            'question': 'Avec le code suivant et note = 5.5, quel message est affiché ?\nnote = 5.5\n\nif note >= 6:\n    print("Excellent ! Félicitations !")\nelif note >= 5.5:\n    print("Très bien !")\nelif note >= 5:\n    print("Bien !")\nelif note >= 4.5:\n    print("Assez bien.")\nelif note >= 4:\n    print("Passable.")\nelse:\n    print("Insuffisant...")',
            'a': '« Excellent ! Félicitations ! »',
            'b': '« Très bien ! »',
            'c': '« Bien ! »',
            'd': '« Assez bien. »',
            'correct': 'B'
        },
        {
            'question': 'Quel opérateur exprime « différent de » en Python ?',
            'a': '==',
            'b': '!=',
            'c': '>=',
            'd': '<=',
            'correct': 'B'
        },
        {
            'question': 'Quelle condition exige simultanément age >= 18 et argent >= 30 ?',
            'a': 'if age >= 18 or argent >= 30:',
            'b': 'if not age >= 18 and argent >= 30:',
            'c': 'if age > 30 and argent >= 18:',
            'd': 'if age >= 18 and argent >= 30:',
            'correct': 'D'
        },
        {
            'question': 'Quelle écriture teste correctement que jour est samedi ou dimanche ?',
            'a': 'if jour == ("samedi" or "dimanche"):',
            'b': 'if jour == "samedi" or jour == "dimanche":',
            'c': 'if jour in "samedi, dimanche":',
            'd': 'if jour == "samedi" and jour == "dimanche":',
            'correct': 'B'
        },
        {
            'question': 'Avec le code suivant, quel message s\'affiche ?\nage = 20\nargent = 25\n\nif age >= 18 and argent >= 30:\n    print("Achat autorisé")\nelse:\n    print("Fonds insuffisants")',
            'a': '« Achat autorisé »',
            'b': '« Fonds insuffisants »',
            'c': 'Aucun message',
            'd': '« Achat autorisé » puis « Fonds insuffisants »',
            'correct': 'B'
        },
        {
            'question': 'Quelle condition est correcte pour tester si age vaut exactement 18 ?',
            'a': 'if age = 18:',
            'b': 'if age == 18:',
            'c': 'if 18 => age:',
            'd': 'if age != 18:',
            'correct': 'B'
        },
        {
            'question': 'Quelle instruction tire un entier au hasard de 1 à 6 (inclus) ?',
            'a': 'random.random()',
            'b': 'random.randint(0, 6)',
            'c': 'random.randint(1, 6)',
            'd': 'random.randrange(1, 6)',
            'correct': 'C'
        }
    ]
    
    for q in questions_ch2:
        conn.execute('''
            INSERT INTO questions (chapitre, texte_question, option_a, option_b, option_c, option_d, bonne_reponse)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (2, q['question'], q['a'], q['b'], q['c'], q['d'], q['correct']))
    
    conn.commit()
    conn.close()

def init_chapter3_questions():
    conn = get_db_connection()
    
    existing = conn.execute('SELECT COUNT(*) FROM questions WHERE chapitre = 3').fetchone()[0]
    if existing > 0:
        conn.close()
        return
    
    questions_ch3 = [
        {
            'question': 'Avec le code suivant, quel message s\'affiche ?\nfor i in range(5):\n    if i == 3:\n        print(f"Tour numéro {i}")',
            'a': '« Tour numéro 0 »',
            'b': '« Tour numéro 3 »',
            'c': '« Tour numéro 4 »',
            'd': 'Aucun message',
            'correct': 'B'
        },
        {
            'question': 'Avec le code suivant, quel message s\'affiche ?\nfor i in range(2, 6):\n    if i == 5:\n        print(i)',
            'a': '2',
            'b': '5',
            'c': '6',
            'd': 'Aucun message',
            'correct': 'B'
        },
        {
            'question': 'Avec le code suivant, quels messages s\'affichent ?\nfor i in range(0, 10, 2):\n    print(i)',
            'a': '1, 3, 5, 7, 9',
            'b': '0, 2, 4, 6, 8',
            'c': '0, 2, 4, 6, 8, 10',
            'd': '2, 4, 6, 8, 10',
            'correct': 'B'
        },
        {
            'question': 'Laquelle de ces boucles affiche 10, 9, 8, …, 1 ?\nA.\nfor i in range(10, 0, -1):\n    print(i)\n\nB.\nfor i in range(10):\n    print(i)\n\nC.\nfor i in range(10, 1, -1):\n    print(i)\n\nD.\nfor i in range(1, 10, -1):\n    print(i)',
            'a': 'A.',
            'b': 'B.',
            'c': 'C.',
            'd': 'D.',
            'correct': 'A'
        },
        {
            'question': 'Avec le code suivant, quels messages s\'affichent ?\nmot = "Python"\nfor lettre in mot:\n    print(f"Lettre : {lettre}")',
            'a': '« Lettre : P », « Lettre : y », …, « Lettre : n »',
            'b': '« Lettre : P », « Lettre : y », « Lettre : t » seulement',
            'c': '« Lettre : Python » sur une seule ligne',
            'd': 'Rien',
            'correct': 'A'
        },
        {
            'question': 'Avec le code suivant, quel message s\'affiche ?\nfor i in range(3):\n    if i == 1:\n        print("OK")',
            'a': '« OK »',
            'b': '« 1 »',
            'c': '« OK » puis « 1 »',
            'd': 'Aucun message',
            'correct': 'A'
        },
        {
            'question': 'Laquelle de ces solutions calcule correctement la somme des éléments de nombres puis l\'affiche ?\nnombres = [10, 20, 30, 40, 50]\n\nA.\ntotal = 0\nfor n in nombres:\n    total = n\nprint(f"Somme totale : {total}")\n\nB.\ntotal = 0\nfor n in nombres:\n    total += n\nprint(f"Somme totale : {total}")\n\nC.\nfor n in nombres:\n    total += n\nprint(f"Somme totale : {total}")\n\nD.\ntotal = 0\nfor n in nombres:\n    print(f"Somme totale : {total + n}")',
            'a': 'A.',
            'b': 'B.',
            'c': 'C.',
            'd': 'D.',
            'correct': 'B'
        },
        {
            'question': 'Combien de lignes sont affichées par le code suivant ?\nfor x in range(4):\n    for y in range(4):\n        print((x, y))',
            'a': '8',
            'b': '12',
            'c': '16',
            'd': '20',
            'correct': 'C'
        },
        {
            'question': 'Laquelle des propositions affiche exactement les lignes ci-dessous, dans cet ordre ?\n(0, 1)\n(0, 2)\n(1, 2)\n\nA.\nfor x in range(3):\n    for y in range(3):\n        if x < y:\n            print((x, y))\n\nB.\nfor x in range(3):\n    for y in range(x, 3):\n        print((x, y))\n\nC.\nfor x in range(1, 3):\n    for y in range(3):\n        if x < y:\n            print((x, y))\n\nD.\nfor x in range(3):\n    for y in range(3):\n        if x <= y:\n            print((x, y))',
            'a': 'A.',
            'b': 'B.',
            'c': 'C.',
            'd': 'D.',
            'correct': 'A'
        },
        {
            'question': 'Laquelle de ces boucles affiche 30, 28, 26, …, 12 ?\nA.\nfor i in range(30, 12, -2):\n    print(i)\n\nB.\nfor i in range(30, 10, -2):\n    print(i)\n\nC.\nfor i in range(12, 30, -2):\n    print(i)\n\nD.\nfor i in range(30, 10, 2):\n    print(i)',
            'a': 'A.',
            'b': 'B.',
            'c': 'C.',
            'd': 'D.',
            'correct': 'B'
        }
    ]
    
    for q in questions_ch3:
        conn.execute('''
            INSERT INTO questions (chapitre, texte_question, option_a, option_b, option_c, option_d, bonne_reponse)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (3, q['question'], q['a'], q['b'], q['c'], q['d'], q['correct']))
    
    conn.commit()
    conn.close()

def init_chapter4_questions():
    conn = get_db_connection()
    
    existing = conn.execute('SELECT COUNT(*) FROM questions WHERE chapitre = 4').fetchone()[0]
    if existing > 0:
        conn.close()
        return
    
    questions_ch4 = [
        {
            'question': 'Combien de fois la ligne print("Etape n°", i) s\'exécute ?\ni = 1\nwhile i <= 3:\n    print("Etape n°", i)\n    i = i + 1',
            'a': '2',
            'b': '3',
            'c': '4',
            'd': '0',
            'correct': 'B'
        },
        {
            'question': 'Quelle condition fait répéter la boucle tant que l\'utilisateur tape exactement "oui" ?\nreponse = "oui"\nwhile ???:\n    reponse = input("Continuer ? (oui/non) : ")',
            'a': 'reponse = "oui"',
            'b': 'reponse != "oui"',
            'c': 'reponse == "oui"',
            'd': '"oui" in reponse',
            'correct': 'C'
        },
        {
            'question': 'Quelle ligne remplace ??? pour éviter une boucle infinie ?\ni = 0\nwhile i < 5:\n    print(i)\n    ???',
            'a': 'i = i',
            'b': 'i = i + 1',
            'c': 'print(i + 1)',
            'd': 'i = 0',
            'correct': 'B'
        },
        {
            'question': 'Avec le code suivant, quel message s\'affiche en dernier ?\ni = 1\nwhile i <= 10:\n    print(i)\n    i = i + 1',
            'a': '9',
            'b': '10',
            'c': '11',
            'd': '0',
            'correct': 'B'
        },
        {
            'question': 'Quel code affiche 10, 9, 8, …, 1 ?\nA.\ni = 10\nwhile i >= 1:\n    print(i)\n    i = i - 1\n\nB.\ni = 1\nwhile i <= 10:\n    print(i)\n    i = i + 1\n\nC.\ni = 10\nwhile i > 1:\n    print(i)\n    i = i + 1\n\nD.\ni = 1\nwhile i >= 10:\n    print(i)',
            'a': 'A.',
            'b': 'B.',
            'c': 'C.',
            'd': 'D.',
            'correct': 'A'
        },
        {
            'question': 'Saisie jusqu\'au signe "=" : tant que l\'utilisateur n\'a pas saisi "=", on redemande une entrée.\nQuelle condition doit-on mettre dans le while ?\ns = input("Entrez un nombre ou \'=\' : ")\nwhile ???:\n    s = input("Entrez un nombre ou \'=\' : ")\nprint("Fin")',
            'a': 's == "="',
            'b': 's != "="',
            'c': 's = "="',
            'd': '"=" in s',
            'correct': 'B'
        },
        {
            'question': 'Validation : on veut un entier ≥ 0. Quelle option est correcte ?\nA.\nn = int(input("n ? "))\nwhile n < 0:\n    print("Entrée valide")\n\nB.\nn = int(input("n ? "))\nwhile n < 0:\n    n = int(input("Recommence (>=0) : "))\n\nC.\nwhile n < 0:\n    n = int(input("Recommence (>=0) : "))\n\nD.\nn = int(input("n ? "))\nwhile n <= 0:\n    n = 0',
            'a': 'A.',
            'b': 'B.',
            'c': 'C.',
            'd': 'D.',
            'correct': 'B'
        },
        {
            'question': 'Somme jusqu\'à dépasser 1000 : quelle version est correcte ?\nA.\ntotal, n = 0, 1\nwhile total <= 1000:\n    total += n\n    n += 1\n\nB.\ntotal, n = 0, 1\nwhile n <= 1000:\n    total += n\n\nC.\ntotal, n = 1, 0\nwhile total <= 1000:\n    n += total\n\nD.\ntotal, n = 0, 1\nwhile total < 1000:\n    n = n + total\n    total = total + 1',
            'a': 'A.',
            'b': 'B.',
            'c': 'C.',
            'd': 'D.',
            'correct': 'A'
        },
        {
            'question': 'Mot de passe : on donne au plus 3 essais et on redemande tant que la saisie est incorrecte.\nQuelle condition met-on dans le while ?\nmdp = "python"\nsaisie = input("Mot de passe : ")\ntentatives = 1\nwhile ???:\n    saisie = input("Mot de passe : ")\n    tentatives += 1',
            'a': 'saisie == mdp and tentatives < 3',
            'b': 'saisie != mdp and tentatives < 3',
            'c': 'saisie != mdp or tentatives < 3',
            'd': 'tentatives <= 3',
            'correct': 'B'
        },
        {
            'question': 'Devinette : répéter tant que la proposition est différente du secret. Quelle ligne complète la boucle ?\nimport random\nsecret = random.randint(1, 100)\nproposition = int(input("Devine : "))\nwhile ???:\n    proposition = int(input("Devine : "))\nprint("Bravo !")',
            'a': 'proposition = secret',
            'b': 'proposition != secret',
            'c': 'secret != 0',
            'd': 'proposition == secret',
            'correct': 'B'
        }
    ]
    
    for q in questions_ch4:
        conn.execute('''
            INSERT INTO questions (chapitre, texte_question, option_a, option_b, option_c, option_d, bonne_reponse)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (4, q['question'], q['a'], q['b'], q['c'], q['d'], q['correct']))
    
    conn.commit()
    conn.close()

def init_chapter5_questions():
    conn = get_db_connection()
    
    existing = conn.execute('SELECT COUNT(*) FROM questions WHERE chapitre = 5').fetchone()[0]
    if existing > 0:
        conn.close()
        return
    
    questions_ch5 = [
        {
            'question': 'Quelle instruction crée une liste vide puis l\'affiche ?\nA.\nma_liste = []\nprint(ma_liste)\n\nB.\nma_liste = {}\nprint(ma_liste)\n\nC.\nma_liste = ()\nprint(ma_liste)\n\nD.\nma_liste = ""\nprint(ma_liste)',
            'a': 'A.',
            'b': 'B.',
            'c': 'C.',
            'd': 'D.',
            'correct': 'A'
        },
        {
            'question': 'Après ces instructions, quelle est la liste obtenue ?\nsalutations = ["Bonjour", "Bonsoir", "Salut"]\nsalutations.append("Yo")',
            'a': '["Bonjour", "Bonsoir"]',
            'b': '["Bonjour", "Bonsoir", "Yo"]',
            'c': '["Yo", "Bonjour", "Bonsoir", "Salut"]',
            'd': '["Bonjour", "Bonsoir", "Salut", "Yo"]',
            'correct': 'D'
        },
        {
            'question': 'Après ces instructions, quelle est la liste obtenue ?\nma_liste = [1, 2, 3, 4]\nma_liste.remove(3)',
            'a': '[1, 2, 4]',
            'b': '[1, 2, 3]',
            'c': '[1, 4]',
            'd': '[2, 3, 4]',
            'correct': 'A'
        },
        {
            'question': 'Quelle ligne affiche la taille de ma_liste ?',
            'a': 'print(size(ma_liste))',
            'b': 'print(length(ma_liste))',
            'c': 'print(len(ma_liste))',
            'd': 'print(count(ma_liste))',
            'correct': 'C'
        },
        {
            'question': 'Avec :\nsalutations = ["Bonjour", "Bonsoir", "Salut"]\nQue va afficher :\nprint(salutations[1])',
            'a': 'Bonjour',
            'b': 'Bonsoir',
            'c': 'Salut',
            'd': 'Provoque une erreur',
            'correct': 'B'
        },
        {
            'question': 'Quel index désigne le premier élément d\'une liste en Python ?',
            'a': '0',
            'b': '1',
            'c': '-1',
            'd': '2',
            'correct': 'A'
        },
        {
            'question': 'Combien de lignes sont affichées ?\nitems = ["a", "b", "c", "d"]\nfor i in range(len(items)):\n    print("A l\'index", i, "il y a", items[i])',
            'a': '3',
            'b': '4',
            'c': '5',
            'd': '0',
            'correct': 'B'
        },
        {
            'question': 'Quelle condition vérifie correctement que "Fargo" est dans la liste series ?',
            'a': 'if "Fargo" of series:',
            'b': 'if "Fargo" inside series:',
            'c': 'if "Fargo" == series:',
            'd': 'if "Fargo" in series:',
            'correct': 'D'
        },
        {
            'question': 'Quel est le résultat affiché par le code suivant ?\ningredients_dessert = ["chocolat", "ananas", "sucre"]\ningredients_dessert.append("oeuf")\ningredients_dessert.remove("ananas")\nprint(len(ingredients_dessert))',
            'a': '2',
            'b': '3',
            'c': '4',
            'd': '5',
            'correct': 'B'
        },
        {
            'question': 'Quel code tire au hasard un élément de maliste (après l\'import correct) ?\nmaliste = ["rouge", "vert", "bleu"]\n\nA.\nimport random\nchoice = random.choice(maliste)\n\nB.\nimport random\nchoice = random.pick(maliste)\n\nC.\nfrom random import randint\nchoice = randint(maliste)\n\nD.\nfrom random import shuffle\nchoice = shuffle(maliste)',
            'a': 'A.',
            'b': 'B.',
            'c': 'C.',
            'd': 'D.',
            'correct': 'A'
        }
    ]
    
    for q in questions_ch5:
        conn.execute('''
            INSERT INTO questions (chapitre, texte_question, option_a, option_b, option_c, option_d, bonne_reponse)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (5, q['question'], q['a'], q['b'], q['c'], q['d'], q['correct']))
    
    conn.commit()
    conn.close()

def init_chapter6_questions():
    conn = get_db_connection()
    
    existing = conn.execute('SELECT COUNT(*) FROM questions WHERE chapitre = 6').fetchone()[0]
    if existing > 0:
        conn.close()
        return
    
    questions_ch6 = [
        {
            'question': 'Quel appel de fonction affiche le texte Bonjour ?',
            'a': 'print("Bonjour")',
            'b': 'input("Bonjour")',
            'c': 'int("Bonjour")',
            'd': 'print = ("Bonjour")',
            'correct': 'A'
        },
        {
            'question': 'Quel appel de fonction convertit la chaîne "35" en entier ?',
            'a': 'str("35")',
            'b': 'int("35")',
            'c': 'float("35")',
            'd': 'int(35.0)',
            'correct': 'B'
        },
        {
            'question': 'Quel en-tête définit correctement une fonction avec deux paramètres ?',
            'a': 'def nom_fonction param1, param2:',
            'b': 'def nom_fonction(param1, param2):',
            'c': 'def nom_fonction[param1, param2]:',
            'd': 'function nom_fonction(param1, param2):',
            'correct': 'B'
        },
        {
            'question': 'Avec le code suivant, quel nombre est affiché ?\ndef cube(nombre):\n    return nombre ** 3\n\nprint(cube(5))',
            'a': '15',
            'b': '25',
            'c': '125',
            'd': '243',
            'correct': 'C'
        },
        {
            'question': 'Quel code renvoie un résultat (plutôt que d\'afficher directement) ?\nA.\ndef bonjour():\n    print("Salut !")\n\nB.\ndef carre(n):\n    return n * n\n\nC.\ndef donne_un_nombre():\n    print(42)\n\nD.\ndef cube(n):\n    print(n ** 3)',
            'a': 'A.',
            'b': 'B.',
            'c': 'C.',
            'd': 'D.',
            'correct': 'B'
        },
        {
            'question': 'Quel appel affiche 42 avec la fonction ci-dessous ?\ndef donne_un_nombre():\n    return 42',
            'a': 'donne_un_nombre()',
            'b': 'print(donne_un_nombre())',
            'c': 'return donne_un_nombre()',
            'd': 'print(42)',
            'correct': 'B'
        },
        {
            'question': 'Portée des variables : que se passe-t-il à la dernière ligne ?\nx = 10\n\ndef ma_fonction():\n    y = 5\n    print(x)\n    print(y)\n\nma_fonction()\nprint(x)\nprint(y)  # ← cette ligne',
            'a': 'Une NameError se produit (y est locale et n\'existe pas ici).',
            'b': 'Affiche 5.',
            'c': 'Affiche 0.',
            'd': 'Affiche None.',
            'correct': 'A'
        },
        {
            'question': 'Quelle implémentation renvoie la chaîne "dans" si n est entre a et b (inclus), sinon "hors" ?\nA.\ndef verifier(n, a, b):\n    if a <= n <= b:\n        return "dans"\n    else:\n        return "hors"\n\nB.\ndef verifier(n, a, b):\n    if a <= n <= b:\n        print("dans")\n    else:\n        print("hors")\n\nC.\ndef verifier(n, a, b):\n    if a < n < b:\n        return "dans"\n\nD.\ndef verifier(n, a, b):\n    return ["dans", "hors"]',
            'a': 'A.',
            'b': 'B.',
            'c': 'C.',
            'd': 'D.',
            'correct': 'A'
        },
        {
            'question': 'Que va afficher ce code ?\ndef carre(n): return n * n\ndef cube(n): return n * carre(n)\nprint(cube(3))',
            'a': '6',
            'b': '9',
            'c': '18',
            'd': '27',
            'correct': 'D'
        },
        {
            'question': 'Quel appel affiche 32 avec la fonction suivante ?\ndef puissance(base, exposant):\n    return base ** exposant\n\nprint( ??? )',
            'a': 'puissance(2, 5)',
            'b': 'puissance(5, 2)',
            'c': 'puissance(2 ^ 5)',
            'd': 'puissance(base = 2*5)',
            'correct': 'A'
        }
    ]
    
    for q in questions_ch6:
        conn.execute('''
            INSERT INTO questions (chapitre, texte_question, option_a, option_b, option_c, option_d, bonne_reponse)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (6, q['question'], q['a'], q['b'], q['c'], q['d'], q['correct']))
    
    conn.commit()
    conn.close()

# Initialiser la base de données au démarrage
def initialize_database():
    init_db()
    init_chapter1_questions()
    init_chapter2_questions()
    init_chapter3_questions()
    init_chapter4_questions()
    init_chapter5_questions()
    init_chapter6_questions()

initialize_database()

@app.route('/')
def index():
    return render_template('cours.html')

@app.route('/cours')
def cours():
    return render_template('cours.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        subject = request.form.get("subject", "").strip()
        message = request.form.get("message", "").strip()

        if not (name and email and subject and message):
            flash("Veuillez remplir tous les champs.", "error")
            return redirect(url_for("contact"))

        try:
            body = f"De: {name} <{email}>\nSujet: {subject}\n\n{message}"

            msg = EmailMessage()
            msg["Subject"] = f"[Contact Site Python] {subject}"
            msg["From"] = FROM_EMAIL
            msg["To"] = TO_EMAIL
            msg["Reply-To"] = email
            msg.set_content(body)

            with smtplib.SMTP_SSL(config.SMTP_HOST, config.SMTP_PORT) as s:
                s.login(config.SMTP_USER, config.SMTP_PASS)
                s.send_message(msg)

            flash("Message envoyé avec succès ! Merci pour votre message.", "success")
            return redirect(url_for("contact"))

        except Exception as e:
            print(e)  # Affiche l'erreur dans la console
            flash("Erreur lors de l'envoi du message. Veuillez réessayer plus tard.", "error")
            return redirect(url_for("contact"))

    return render_template('contact.html')

@app.route('/professeur')
def professeur():
    return render_template('professeur.html')

@app.route('/detail-cours')
def detail_cours():
    return render_template('detail-cours.html')

@app.route('/chapitre1')
def chapitre1():
    if 'user_id' not in session:
        flash('Vous devez être connecté pour accéder aux chapitres.', 'error')
        return redirect(url_for('connexion'))
    return render_template('chapitre1.html')

@app.route('/chapitre2')
def chapitre2():
    if 'user_id' not in session:
        flash('Vous devez être connecté pour accéder aux chapitres.', 'error')
        return redirect(url_for('connexion'))
    return render_template('chapitre2.html')

@app.route('/chapitre3')
def chapitre3():
    if 'user_id' not in session:
        flash('Vous devez être connecté pour accéder aux chapitres.', 'error')
        return redirect(url_for('connexion'))
    return render_template('chapitre3.html')

@app.route('/chapitre4')
def chapitre4():
    if 'user_id' not in session:
        flash('Vous devez être connecté pour accéder aux chapitres.', 'error')
        return redirect(url_for('connexion'))
    return render_template('chapitre4.html')

@app.route('/chapitre5')
def chapitre5():
    if 'user_id' not in session:
        flash('Vous devez être connecté pour accéder aux chapitres.', 'error')
        return redirect(url_for('connexion'))
    return render_template('chapitre5.html')

@app.route('/chapitre6')
def chapitre6():
    if 'user_id' not in session:
        flash('Vous devez être connecté pour accéder aux chapitres.', 'error')
        return redirect(url_for('connexion'))
    return render_template('chapitre6.html')

@app.route('/connexion', methods=['GET', 'POST'])
def connexion():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM etudiants WHERE email = ?', (email,)).fetchone()
        conn.close()
        
        if user and verify_password(password, user['mot_de_passe']):
            session['user_id'] = user['id']
            session['user_email'] = user['email']
            flash('Connexion réussie !', 'success')
            return redirect(url_for('cours'))
        else:
            flash('Email ou mot de passe incorrect.', 'error')
    
    return render_template('connexion.html')

@app.route('/inscription', methods=['GET', 'POST'])
def inscription():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        # Vérifier que les mots de passe correspondent
        if password != confirm_password:
            flash('Les mots de passe ne correspondent pas.', 'error')
            return render_template('inscription.html')
        
        # Vérifier si l'email existe déjà
        conn = get_db_connection()
        existing_user = conn.execute('SELECT * FROM etudiants WHERE email = ?', (email,)).fetchone()
        
        if existing_user:
            flash('Cette adresse email est déjà utilisée.', 'error')
            conn.close()
            return render_template('inscription.html')
        
        # Créer le nouveau compte étudiant
        hashed_password = hash_password(password)
        cursor = conn.execute('INSERT INTO etudiants (email, mot_de_passe) VALUES (?, ?)', 
                    (email, hashed_password))
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Connexion automatique après inscription
        session['user_id'] = user_id
        session['user_email'] = email
        return redirect(url_for('cours'))
    
    return render_template('inscription.html')

@app.route('/tableau-de-bord')
def tableau_de_bord():
    if 'user_id' not in session:
        flash('Vous devez être connecté pour accéder à cette page.', 'error')
        return redirect(url_for('connexion'))
    
    # Récupérer l'historique complet des QCM de l'étudiant
    conn = get_db_connection()
    quiz_history = conn.execute('''
        SELECT chapitre, score, total_questions, date_tentative,
               ROW_NUMBER() OVER (PARTITION BY chapitre ORDER BY score DESC, date_tentative DESC) as rank
        FROM tentatives_qcm 
        WHERE etudiant_id = ? 
        ORDER BY chapitre, date_tentative DESC
    ''', (session['user_id'],)).fetchall()
    
    # Organiser les données pour l'affichage
    best_scores = {}
    all_attempts = []
    
    for attempt in quiz_history:
        chapitre = attempt['chapitre']
        all_attempts.append(attempt)
        
        # Garder seulement le meilleur score par chapitre
        if chapitre not in best_scores or attempt['score'] > best_scores[chapitre]['score']:
            best_scores[chapitre] = attempt
    
    conn.close()
    
    return render_template('tableau_de_bord.html', 
                         best_scores=best_scores, 
                         all_attempts=all_attempts)

@app.route('/deconnexion')
def deconnexion():
    session.clear()
    flash('Vous avez été déconnecté.', 'info')
    return redirect(url_for('index'))

@app.route('/qcm/<int:chapitre>')
def qcm(chapitre):
    if 'user_id' not in session:
        flash('Vous devez être connecté pour accéder aux QCM.', 'error')
        return redirect(url_for('connexion'))
    
    # Vérifier que le chapitre est valide (1 à 6)
    if chapitre < 1 or chapitre > 6:
        flash('Chapitre non valide.', 'error')
        return redirect(url_for('cours'))
    
    # Récupérer toutes les questions du chapitre demandé
    conn = get_db_connection()
    questions = conn.execute(
        'SELECT * FROM questions WHERE chapitre = ? ORDER BY id', 
        (chapitre,)
    ).fetchall()
    conn.close()
    
    if not questions:
        flash(f'Aucune question disponible pour le chapitre {chapitre}.', 'error')
        return redirect(url_for('cours'))
    
    return render_template('qcm.html', questions=questions, chapitre=chapitre)

@app.route('/qcm/<int:chapitre>/submit', methods=['POST'])
def qcm_submit(chapitre):
    if 'user_id' not in session:
        flash('Vous devez être connecté.', 'error')
        return redirect(url_for('connexion'))
    
    conn = get_db_connection()
    
    # Récupérer toutes les questions du chapitre
    questions = conn.execute(
        'SELECT * FROM questions WHERE chapitre = ? ORDER BY id', 
        (chapitre,)
    ).fetchall()
    
    if not questions:
        flash('Erreur: Aucune question trouvée.', 'error')
        conn.close()
        return redirect(url_for('cours'))
    
    # Initialiser les variables pour le calcul du score
    correct_answers = 0
    total_questions = len(questions)
    
    # Créer une nouvelle tentative dans la base de données
    cursor = conn.execute(
        'INSERT INTO tentatives_qcm (etudiant_id, chapitre, score, total_questions) VALUES (?, ?, ?, ?)',
        (session['user_id'], chapitre, 0, total_questions)
    )
    attempt_id = cursor.lastrowid
    
    # Traiter chaque réponse de l'étudiant
    for question in questions:
        question_id = question['id']
        selected_answer = request.form.get(f'question_{question_id}', '').upper()
        
        # Valider que la réponse est une option valide (A, B, C, D)
        if selected_answer not in ['A', 'B', 'C', 'D']:
            selected_answer = 'X'  # Réponse non donnée ou invalide
        
        # Vérifier si la réponse est correcte
        is_correct = selected_answer == question['bonne_reponse']
        if is_correct:
            correct_answers += 1
        
        # Enregistrer la réponse dans la base de données
        try:
            conn.execute(
                'INSERT INTO reponses_etudiant (tentative_id, question_id, reponse_selectionnee, est_correcte) VALUES (?, ?, ?, ?)',
                (attempt_id, question_id, selected_answer, is_correct)
            )
        except sqlite3.IntegrityError:
            # Doublon détecté, ignorer (sécurité)
            pass
    
    # Calculer le score final en pourcentage
    final_score = int((correct_answers / total_questions) * 100)
    
    # Mettre à jour le score de la tentative
    conn.execute(
        'UPDATE tentatives_qcm SET score = ? WHERE id = ?',
        (final_score, attempt_id)
    )
    
    conn.commit()
    conn.close()
    
    return redirect(url_for('qcm_resultat', chapitre=chapitre, attempt_id=attempt_id))

@app.route('/qcm/<int:chapitre>/resultat/<int:attempt_id>')
def qcm_resultat(chapitre, attempt_id):
    if 'user_id' not in session:
        flash('Vous devez être connecté.', 'error')
        return redirect(url_for('connexion'))
    
    conn = get_db_connection()
    
    # Récupérer les détails de cette tentative spécifique
    attempt = conn.execute(
        'SELECT * FROM tentatives_qcm WHERE id = ? AND etudiant_id = ?',
        (attempt_id, session['user_id'])
    ).fetchone()
    
    if not attempt:
        flash('Résultat non trouvé.', 'error')
        conn.close()
        return redirect(url_for('cours'))
    
    # Récupérer les détails de chaque réponse avec les questions correspondantes
    answers_details = conn.execute('''
        SELECT re.*, q.texte_question, q.option_a, q.option_b, q.option_c, q.option_d, q.bonne_reponse
        FROM reponses_etudiant re
        JOIN questions q ON re.question_id = q.id
        WHERE re.tentative_id = ?
        ORDER BY q.id
    ''', (attempt_id,)).fetchall()
    
    conn.close()
    
    # Déterminer le message d'encouragement selon le score
    score = attempt['score']
    if score >= 90:
        message = "🎉 Excellent ! Parfaite maîtrise du chapitre !"
        message_class = "success"
    elif score >= 80:
        message = "👍 Très bien ! Bonne compréhension du chapitre !"
        message_class = "success"
    elif score >= 70:
        message = "👌 Bien ! Quelques révisions conseillées."
        message_class = "warning"
    elif score >= 60:
        message = "⚠️ Passable, revoyez certains points."
        message_class = "warning"
    else:
        message = "❌ Insuffisant, relisez attentivement le chapitre."
        message_class = "error"
    
    return render_template('qcm_resultat.html', 
                         attempt=attempt, 
                         answers_details=answers_details,
                         chapitre=chapitre,
                         message=message,
                         message_class=message_class)

# Gestionnaire d'erreur 404
@app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html'), 404

if __name__ == '__main__':
    app.run(debug=True)
