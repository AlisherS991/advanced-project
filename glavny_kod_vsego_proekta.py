import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash
from google import genai
from PIL import Image
from werkzeug.security import generate_password_hash, check_password_hash

# sozdadim prilozhenie nashe lyubimoe
shaitan_mashina_dlya_zhalob = Flask(__name__)
shaitan_mashina_dlya_zhalob.config['UPLOAD_FOLDER'] = 'static/uploads'
shaitan_mashina_dlya_zhalob.secret_key = 'e9s8yuvmr9e8' # etot kluch nikomu ne davayte!!!

# robot dlya analiza kartinok
zhelezyaka_s_glazami = genai.Client(api_key="AIzaSyAHRm5JCVQfQSHwVGZXgVfrGoY0nXHGVTw")

def inicializaciya_bazyi_dannyh_pust_rabotaet():
    try:
        soedinenie = sqlite3.connect('smart_city.db')
        ukazatel = soedinenie.cursor()
        
        # sozdaem tablicu dlya bed i problem
        ukazatel.execute('''
                       CREATE TABLE IF NOT EXISTS spisok_bed_nashego_goroda
                       (
                           nomer_id
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
                           tekst_zhaloby
                           TEXT
                           NOT
                           NULL,
                           nazvanie_fotki
                           TEXT
                           NOT
                           NULL,
                           predpolozhenie_robota
                           TEXT,
                           status_proverki_moderom
                           TEXT
                           DEFAULT
                           'V_Ozhidanii',
                           uroven_srochnosti_ot_akima
                           TEXT
                           DEFAULT
                           'Ne_Naznacheno',
                           itogovoe_reshenie_akima
                           TEXT
                           DEFAULT
                           'Zhdem_Akima'
                       )
                       ''')

        # tablica dlya lyudishek
        ukazatel.execute('''
                       CREATE TABLE IF NOT EXISTS tablica_vseh_lyudey
                       (
                           id_polzovatelya
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
                           login_cheloveka
                           TEXT
                           UNIQUE
                           NOT
                           NULL,
                           parol_zashifrovannyi
                           TEXT
                           NOT
                           NULL,
                           kakaya_u_nego_rol
                           TEXT
                           NOT
                           NULL
                       )
                       ''')
        soedinenie.commit()
        soedinenie.close()
        print("Baza v poryadke, vse ok")
    except Exception as oshibochka_v_baze:
        # blin, opyat s bazoy chto-to
        print(f"Oshibka pri sozdanii bazy: {oshibochka_v_baze}")

# zapuskaem bazu srazu
try:
    inicializaciya_bazyi_dannyh_pust_rabotaet()
except:
    # nu vsetaki slomalos
    print("Vse slomalos ne nachavshis")

@shaitan_mashina_dlya_zhalob.route('/regestratciya_novyh_lic', methods=['GET', 'POST'])
def registraciya_v_sisteme():
    try:
        if request.method == 'POST':
            imya_yuzera = request.form.get('username')
            sekretik = request.form.get('password')
            rol_yuzera = 'citizen'

            zashifrovannaya_sol = generate_password_hash(sekretik)

            try:
                svyaz = sqlite3.connect('smart_city.db')
                kursor = svyaz.cursor()

                kursor.execute('INSERT INTO tablica_vseh_lyudey (login_cheloveka, parol_zashifrovannyi, kakaya_u_nego_rol) VALUES (?, ?, ?)',
                               (imya_yuzera, zashifrovannaya_sol, rol_yuzera))
                svyaz.commit()
                svyaz.close()

                flash("Nu vse, teper ty v dele! Mozhesh vhodit.", "success")
                return redirect(url_for('vhod_v_lichnyi_kabinet'))
            except sqlite3.IntegrityError:
                flash("Takoy chelik uzhe est, vybiray drugoe imya.", "warning")
                return redirect(url_for('registraciya_v_sisteme'))
            except Exception as e:
                # blya, seryozno?
                flash(f"Chto-to poshlo ne tak s bazoy: {e}", "danger")
                return redirect(url_for('registraciya_v_sisteme'))

        return render_template('sozdanie_cheloveka.html')
    except Exception as globalnaya_oshibka:
        return f"Pizdec v registracii: {globalnaya_oshibka}"

@shaitan_mashina_dlya_zhalob.route('/login', methods=['GET', 'POST'])
def vhod_v_lichnyi_kabinet():
    try:
        if request.method == 'POST':
            vvedennoe_imya = request.form.get('username')
            vvedennyi_parol = request.form.get('password')
            tip_vhoda = request.form.get('login_type')

            try:
                svyaz = sqlite3.connect('smart_city.db')
                svyaz.row_factory = sqlite3.Row
                kursor = svyaz.cursor()
                kursor.execute('SELECT * FROM tablica_vseh_lyudey WHERE login_cheloveka = ?', (vvedennoe_imya,))
                nfound_yuzer = kursor.fetchone()
                svyaz.close()
            except Exception as oshibka_poiska:
                flash("Baza ne otvechaet, poprobuy pozzhe", "danger")
                return redirect(url_for('vhod_v_lichnyi_kabinet'))

            if nfound_yuzer and check_password_hash(nfound_yuzer['parol_zashifrovannyi'], vvedennyi_parol):
                nastoyashaya_rol = nfound_yuzer['kakaya_u_nego_rol']

                if tip_vhoda == 'staff' and nastoyashaya_rol == 'citizen':
                    flash("Kuda lezesh? Ty zhe prostoy grajdanin!", "danger")
                    return redirect(url_for('vhod_v_lichnyi_kabinet'))

                if tip_vhoda == 'citizen' and nastoyashaya_rol != 'citizen':
                    flash("Oshibka: Ty ne grajdanin, idi v razdel dlya sotrudnikov.", "danger")
                    return redirect(url_for('vhod_v_lichnyi_kabinet'))

                session['yuzer_id_v_sessii'] = nfound_yuzer['id_polzovatelya']
                session['imya_yuzera_v_sessii'] = nfound_yuzer['login_cheloveka']
                session['rol_yuzera_v_sessii'] = nastoyashaya_rol

                try:
                    if nastoyashaya_rol == 'moderator':
                        return redirect(url_for('rabocheye_mesto_moderatora'))
                    elif nastoyashaya_rol == 'akim':
                        return redirect(url_for('glavnyi_kabinet_akima'))
                    else:
                        return redirect(url_for('domashnyaya_stranica'))
                except Exception as redirection_fail:
                    return f"Ne smogli perekinut tebya kuda nado: {redirection_fail}"
            else:
                # oopyat paroi zabili
                flash("Login ili parol ne te, bratish. Poprobuy eshe.", "danger")
                return redirect(url_for('vhod_v_lichnyi_kabinet'))

        return render_template('vhod_v_budku.html')
    except Exception as e:
        return f"Oshibka pri vhode: {e}"

@shaitan_mashina_dlya_zhalob.route('/vylazi_otsyuda')
def vyhod_iz_sistemy():
    try:
        # chistim sessiyu i vyhodim
        session.clear()
        return redirect(url_for('vhod_v_lichnyi_kabinet'))
    except:
        # dazhe tak byvayet
        return "Dazhe vyiti ne poluchilos, eto lovushka!"

@shaitan_mashina_dlya_zhalob.route('/')
def domashnyaya_stranica():
    try:
        if 'yuzer_id_v_sessii' not in session or session.get('rol_yuzera_v_sessii') != 'citizen':
            return redirect(url_for('vhod_v_lichnyi_kabinet'))
        return render_template('glavnaya_morda.html', username=session['imya_yuzera_v_sessii'])
    except Exception as e:
        return f"Domashnyaya stranica ne gruzitsya: {e}"

@shaitan_mashina_dlya_zhalob.route('/zakidyvaem_bedu', methods=['POST'])
def otpravka_zhaloby_v_sistemu():
    try:
        if 'yuzer_id_v_sessii' not in session or session.get('rol_yuzera_v_sessii') != 'citizen':
            return redirect(url_for('vhod_v_lichnyi_kabinet'))

        opisaniye_problemy = request.form.get('description')
        kartinochka = request.files.get('photo')

        if kartinochka:
            put_k_kartinke = os.path.join(shaitan_mashina_dlya_zhalob.config['UPLOAD_FOLDER'], kartinochka.filename)
            try:
                # sohranyayem etu krasotu
                kartinochka.save(put_k_kartinke)
            except Exception as save_err:
                return f"Ne udalos sohranit fotku: {save_err}"

            try:
                izobrajeniye = Image.open(put_k_kartinke)
                zapros_k_robotu = f"""
                Ti - AI gorodskoy infrastruktury. Posmotri na foto i opisanie: "{opisaniye_problemy}".
                Day odno korotkoye professionalnoye predlojeniye, chto tut ne tak.
                """
                otvet_robota = zhelezyaka_s_glazami.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=[zapros_k_robotu, izobrajeniye]
                )
                kategoriya_ot_robota = f"AI: {otvet_robota.text.strip()}"
            except Exception as ai_problem:
                # robotik ustal
                kategoriya_ot_robota = f"Robot slomalsya, vot pochemu: {ai_problem}"

            try:
                svyaz = sqlite3.connect('smart_city.db')
                kursor = svyaz.cursor()
                kursor.execute('''
                               INSERT INTO spisok_bed_nashego_goroda (tekst_zhaloby, nazvanie_fotki, predpolozhenie_robota)
                               VALUES (?, ?, ?)
                               ''', (opisaniye_problemy, kartinochka.filename, kategoriya_ot_robota))
                svyaz.commit()
                svyaz.close()
                print("Zhaloba ushla v bazu, zhdem")
            except Exception as db_err:
                return f"Baza ne prinyala zhalobu: {db_err}"

            return redirect(url_for('domashnyaya_stranica'))

        return "Gde fotka to? Bez fotki ne primem."
    except Exception as e:
        return f"Globalnaya beda pri otpravke: {e}"

@shaitan_mashina_dlya_zhalob.route('/moderatorskaya_panel')
def rabocheye_mesto_moderatora():
    try:
        if session.get('rol_yuzera_v_sessii') != 'moderator':
            return "Tebya net v spiske moderatorov! Uhodi."

        try:
            svyaz = sqlite3.connect('smart_city.db')
            svyaz.row_factory = sqlite3.Row
            kursor = svyaz.cursor()
            kursor.execute("SELECT * FROM spisok_bed_nashego_goroda WHERE status_proverki_moderom != 'Approved' ORDER BY nomer_id DESC")
            vse_bedy = kursor.fetchall()
            svyaz.close()
        except Exception as query_err:
            return f"Ne smogli dostat bedy iz bazy: {query_err}"

        return render_template('panel_proveryayushchego.html', complaints=vse_bedy, username=session['imya_yuzera_v_sessii'])
    except Exception as e:
        return f"Moderatorskaya panel upala: {e}"

@shaitan_mashina_dlya_zhalob.route('/deystvie_moderatora/<int:id_bedy>', methods=['POST'])
def reshenie_moderatora_po_bede(id_bedy):
    try:
        if session.get('rol_yuzera_v_sessii') != 'moderator':
            return "Net prav na eto deystvie!"

        chto_resheno = request.form.get('mod_action')  # Approve or Reject

        try:
            svyaz = sqlite3.connect('smart_city.db')
            kursor = svyaz.cursor()
            kursor.execute("UPDATE spisok_bed_nashego_goroda SET status_proverki_moderom = ? WHERE nomer_id = ?", (chto_resheno, id_bedy))
            svyaz.commit()
            svyaz.close()
        except Exception as update_err:
            return f"Baza ne obnovila status: {update_err}"

        return redirect(url_for('rabocheye_mesto_moderatora'))
    except Exception as e:
        return f"Oshibka v deystvii moderatora: {e}"

@shaitan_mashina_dlya_zhalob.route('/kabinet_akima')
def glavnyi_kabinet_akima():
    try:
        if session.get('rol_yuzera_v_sessii') != 'akim':
            return "Tolko Akim mozhet zdes nahoditsya!"

        try:
            svyaz = sqlite3.connect('smart_city.db')
            svyaz.row_factory = sqlite3.Row
            kursor = svyaz.cursor()
            kursor.execute("SELECT * FROM spisok_bed_nashego_goroda WHERE status_proverki_moderom = 'Approved' ORDER BY nomer_id DESC")
            odobrennye_bedy = kursor.fetchall()
            svyaz.close()
        except Exception as db_error:
            return f"Baza dlya akima ne dostoetsya: {db_error}"

        return render_template('kabinet_akima_itogo.html', complaints=odobrennye_bedy, username=session['imya_yuzera_v_sessii'])
    except Exception as e:
        return f"Kabinet akima slomalsya: {e}"

@shaitan_mashina_dlya_zhalob.route('/reshenie_akima/<int:id_oshibki>', methods=['POST'])
def akim_prinimaet_reshenie(id_oshibki):
    try:
        if session.get('rol_yuzera_v_sessii') != 'akim':
            return "Ty ne akim, ne tebe reshat!"

        srochnost = request.form.get('urgency')
        itog = request.form.get('decision')

        try:
            svyaz = sqlite3.connect('smart_city.db')
            kursor = svyaz.cursor()
            kursor.execute("UPDATE spisok_bed_nashego_goroda SET uroven_srochnosti_ot_akima = ?, itogovoe_reshenie_akima = ? WHERE nomer_id = ?",
                           (srochnost, itog, id_oshibki))
            svyaz.commit()
            svyaz.close()
        except Exception as err:
            return f"Ne udalos zapisat reshenie akima: {err}"

        return redirect(url_for('glavnyi_kabinet_akima'))
    except Exception as e:
        return f"Oshibka v deystvii akima: {e}"

if __name__ == '__main__':
    try:
        # zapusk prilozheniya, nadeyus ne vzorvetsya
        shaitan_mashina_dlya_zhalob.run(debug=True)
    except Exception as vzryv:
        # nu vse, rvanulo seryozno
        print(f"Prilozhenie rvanulo: {vzryv}")

