import math
import cmath

def procijeni_performanse_niza(nacin_rada, faza_deg, razmak_lambda):
    if nacin_rada == "broadside":
        gain_dBi = 3.8 + (razmak_lambda - 0.25) * 2.0
        beamwidth_deg = 76.0 if razmak_lambda == 0.25 else 90.0
        fb_ratio = 0.0
        return max(3.0, gain_dBi), beamwidth_deg, fb_ratio
    elif nacin_rada == "christman":
        return 3.65, 158.5, 25.0
    else:
        base_gain = 3.4 + (faza_deg - 90.0) * 0.025
        if razmak_lambda != 0.25:
            base_gain -= abs(razmak_lambda - 0.25) * 4.0
        beamwidth = 169.0 - (faza_deg - 90.0) * 1.05
        fb_ratio = 25.0 - abs(faza_deg - 100.0) * 0.5
        return max(2.5, base_gain), max(120.0, min(190.0, beamwidth)), max(10.0, fb_ratio)

def izracunaj_zracnu_zavojnicu(target_l_nh, promjer_cm, promjer_zice_mm, zracnost_mm):
    if target_l_nh <= 0 or promjer_cm <= 0:
        return 0, 0
    best_n = 1
    best_diff = float('inf')
    best_duljina = 0
    
    pitch_cm = (promjer_zice_mm + zracnost_mm) / 10.0

    for n in range(1, 2000):
        l_namota_cm = n * pitch_cm
        denominator = (18 * promjer_cm) + (40 * l_namota_cm)
        if denominator > 0:
            l_calc_nh = 393.7 * (promjer_cm ** 2) * (n ** 2) / denominator
            diff = abs(l_calc_nh - target_l_nh)
            if diff < best_diff:
                best_diff = diff
                best_n = n
                best_duljina = l_namota_cm

    return best_n, best_duljina

def izracunaj_l_mrezu(r_in, x_in, f_mhz, r_target=50.0):
    omega = 2 * math.pi * (f_mhz * 1e6)
    rezultati = []
    try:
        if r_in <= 0:
            return rezultati

        if r_in < r_target:
            q = math.sqrt((r_target / r_in) - 1.0)
            x_s = q * r_in
            x_p = r_target / q
            
            l_val = (x_s - x_in) / omega * 1e9  # nH
            if l_val < 0: l_val = abs(l_val)
            
            c_val = 1.0 / (omega * x_p) * 1e12  # pF
            topologija = "Serijski L na ulazu, Paralelni C prema izlazu (Step-Up)"
        elif r_in > r_target:
            q = math.sqrt((r_in / r_target) - 1.0)
            x_p = r_in / q
            x_s = q * r_target
            
            l_val = x_p / omega * 1e9           # nH
            c_val = 1.0 / (omega * (x_s + x_in)) * 1e12 if (x_s + x_in) != 0 else 0 # pF
            topologija = "Paralelna zavojnica (L), Serijski C prema izlazu (Step-Down)"
        else:
            if x_in == 0:
                return [("Nema potrebe za prilagodbom (50 Ω čisto)", 0.0, 0.0)]
            else:
                if x_in > 0:
                    c_val = 1.0 / (omega * x_in) * 1e12
                    l_val = 0.0
                    topologija = "Samo serijski kondenzator za poništavanje reaktancije"
                else:
                    l_val = abs(x_in) / omega * 1e9
                    c_val = 0.0
                    topologija = "Samo serijska zavojnica za poništavanje reaktancije"

        rezultati.append((topologija, max(0.0, c_val), max(0.0, l_val)))
    except Exception:
        pass
    return rezultati

def simuliraj_swr_propusnost(f_centar, r_ant, x_ant, nacin_rada):
    print("\n" + "-" * 70)
    print("SIMULACIJA SWR-A NA FREKVENCIJSKOM RASPONU (Direktan spoj):")
    print("-" * 70)
    
    offsets_khz = [-50, -25, 0, 25, 50]
    z0 = 50.0
    
    for offset in offsets_khz:
        f_mhz = f_centar + (offset / 1000.0)
        z_ant_f = complex(r_ant, x_ant * (f_mhz / f_centar))
        
        if nacin_rada == "christman":
            theta = (math.pi / 2.0) * (f_mhz / f_centar) * (84.0 / 90.0)
        else:
            theta = (math.pi / 2.0) * (f_mhz / f_centar)
            
        tan_theta = cmath.tan(theta)
        z_trans_krak = z0 * (z_ant_f + 1j * z0 * tan_theta) / (z0 + 1j * z_ant_f * tan_theta)
        z_tspoj = z_trans_krak / 2.0
        
        gamma = (z_tspoj - z0) / (z_tspoj + z0)
        swr = (1 + abs(gamma)) / (1 - abs(gamma)) if abs(gamma) < 1 else 9.99
        
        oznaka = " <-- CENTAR" if offset == 0 else ""
        print(f"   {f_mhz:7.3f} MHz ({offset:+4d} kHz):  SWR = {swr:.2f}:1{oznaka}")
    print("-" * 70)

def simuliraj_swr_usporedba_realno(f_centar, r_ant_centar, x_ant_centar, c_pF, l_nH, nacin_rada):
    print("\n" + "-" * 90)
    print("REALISTIČNA ŠIRA SIMULACIJA SWR-A PREKO BANDA (3.500 - 3.800 MHz):")
    print("Napomena: Uključuje promjenu impedancije antene preko frekvencije.")
    print("-" * 90)
    print(f"{'Frekvencija':<15} | {'Realna Z antene (R+jX)':<25} | {'Sirovi SWR':<15} | {'SWR s L-mrežom':<15}")
    print("-" * 90)
    
    frekvencije = [3.500, 3.550, 3.600, 3.650, 3.700, 3.750, 3.800]
    z0 = 50.0
    
    C_farad = c_pF * 1e-12
    L_henry = l_nH * 1e-9
    
    for f_mhz in frekvencije:
        delta_f = f_mhz - f_centar
        # Realniji model: kako frekvencija raste, antena postaje električki dulja (raste X i R)
        r_f = r_ant_centar + delta_f * 25.0  # blagi porast otpora s frekvencijom
        x_f = x_ant_centar + delta_f * 180.0 # brži porast induktivne reaktancije
        z_ant_f = complex(max(10.0, r_f), x_f)
        
        omega = 2 * math.pi * (f_mhz * 1e6)
        
        if nacin_rada == "christman":
            theta = (math.pi / 2.0) * (f_mhz / f_centar) * (84.0 / 90.0)
        else:
            theta = (math.pi / 2.0) * (f_mhz / f_centar)
            
        tan_theta = cmath.tan(theta)
        z_trans_krak = z0 * (z_ant_f + 1j * z0 * tan_theta) / (z0 + 1j * z_ant_f * tan_theta)
        z_tspoj = z_trans_krak / 2.0
        
        gamma_raw = (z_tspoj - z0) / (z_tspoj + z0)
        swr_raw = (1 + abs(gamma_raw)) / (1 - abs(gamma_raw)) if abs(gamma_raw) < 1 else 9.99
        
        z_uz_l = z_tspoj + 1j * omega * L_henry
        y_uz_l = 1.0 / z_uz_l if z_uz_l != 0 else 0
        y_c = 1j * omega * C_farad
        y_ukupno = y_uz_l + y_c
        z_izlaz = 1.0 / y_ukupno if y_ukupno != 0 else complex(0, 0)
        
        gamma_match = (z_izlaz - z0) / (z_izlaz + z0)
        swr_match = (1 + abs(gamma_match)) / (1 - abs(gamma_match)) if abs(gamma_match) < 1 else 9.99
        
        oznaka = " <-- CENTAR" if abs(f_mhz - f_centar) < 0.001 else ""
        z_str = f"{z_ant_f.real:5.1f} + j({z_ant_f.imag:5.1f})Ω"
        print(f" {f_mhz:7.3f} MHz       | {z_str:<25} |   {swr_raw:5.2f}:1      |   {swr_match:5.2f}:1 {oznaka}")
    print("-" * 90)

def izracunaj_fazni_sustav():
    print("=" * 70)
    print("   KALKULATOR FAZNOG NIZA, PRILAGODBE I ZRAČNIH ZAVOJNICA   ")
    print("=" * 70)

    kablovi_50 = {
        "1": ("RG-58 / RG-213 / RG-8 (Solid PE)", 0.66),
        "2": ("RG-8X / RG-213 Foam", 0.80),
        "3": ("Aircell 7 / Ultraflex 7 / EcoFlex", 0.83),
        "4": ("PTFE / Teflon", 0.70)
    }

    print("\n1. Odaberite tip 50 Ω KABELA za linije:")
    for kljuc, (naziv, vf_val) in kablovi_50.items():
        print(f"  [{kljuc}] {naziv}  (VF = {vf_val})")
    print("  [5] Unesite prilagođeni (Custom) VF za kabel")

    izbor = input("\nVaš izbor (1-5): ").strip()
    if izbor in kablovi_50:
        naziv_kabela, vf_50 = kablovi_50[izbor]
    elif izbor == "5":
        vf_50 = float(input("Unesite željeni faktor brzine (VF) za kabel [npr. 0.75]: "))
    else:
        vf_50 = 0.83

    try:
        print("\n2. Odaberite način rada niza:")
        print("  [1] End-Fire (Standardni usmjereni rad - prilagođeni fazni pomak)")
        print("  [2] Broadside (Bočno zračenje - dvosmjerna 'osmica', 0° faza)")
        print("  [3] Christmanov niz (71° fazni kabel + 84° napojne linije)")
        izbor_naclina = input("Vaš izbor načina rada (1-3): ").strip()
        
        if izbor_naclina == "2":
            nacin_rada = "broadside"
            faza_deg = 0.0
        elif izbor_naclina == "3":
            nacin_rada = "christman"
            faza_deg = 71.0
        else:
            nacin_rada = "endfire"
            faza_deg = float(input("\nUnesite željeni fazni pomak (°) [npr. 100 ili 110]: "))

        f_mhz = float(input("\nUnesite frekvenciju (MHz) [npr. 3.550]: "))
        
        r_ant = float(input("Unesite radni otpor R antene (Ω) [npr. 32.0]: "))
        x_ant = float(input("Unesite reaktanciju X antene (Ω) [npr. -4.0]: "))
        z_ant = complex(r_ant, x_ant)

        print("\nRazmak između vertikala u valnim duljinama (λ):")
        print("  [1] 1/4 λ (0.25 λ) - Standardni preporučeni razmak")
        print("  [2] 1/8 λ (0.125 λ)")
        print("  [3] Prilagođeni razmak (ručni unos u λ)")
        
        izbor_razmaka = input("Vaš izbor razmaka (1-3): ").strip()
        razmak_lambda = 0.25 if izbor_razmaka == "1" else (0.125 if izbor_razmaka == "2" else float(input("Unesite razmak u λ: ")))

        if nacin_rada == "christman":
            print("\nOdaberite metodu prilagodbe impedancije na 50 Ω (Christman):")
            print("  [1] LC mreža (L-match unutar fazne kutije)")
            print("  [2] Bez dodatne prilagodbe (direktan spoj - preporučeno)")
            izbor_prilagodbe_raw = input("Vaš izbor prilagodbe (1-2): ").strip()
            izbor_prilagodbe = "2" if izbor_prilagodbe_raw == "1" else "3"
        else:
            print("\nOdaberite metodu prilagodbe impedancije na 50 Ω:")
            print("  [1] 75 Ω koaksijalni Q-transformator (1/4 λ dionica)")
            print("  [2] LC mreža (L-match unutar fazne kutije)")
            print("  [3] Bez dodatne prilagodbe (direktan spoj)")
            izbor_prilagodbe = input("Vaš izbor prilagodbe (1-3): ").strip()

        c_light = 299.792458
        lambda_m = c_light / f_mhz

        udaljenost_vertikala_m = lambda_m * razmak_lambda
        
        if nacin_rada == "christman":
            duljina_fazni_koaks_m = lambda_m * (71.0 / 360.0) * vf_50
            duljina_q_line_m = lambda_m * (84.0 / 360.0) * vf_50
        elif nacin_rada == "endfire":
            duljina_fazni_koaks_m = lambda_m * (faza_deg / 360.0) * vf_50
            duljina_q_line_m = lambda_m * 0.25 * vf_50
        else:
            duljina_fazni_koaks_m = 0.0
            duljina_q_line_m = lambda_m * 0.25 * vf_50

        z0_50 = 50.0
        z_trans_krak = (z0_50 ** 2) / z_ant
        z_tspoj = z_trans_krak / 2.0

        gamma = (z_tspoj - z0_50) / (z_tspoj + z0_50)
        swr_50 = (1 + abs(gamma)) / (1 - abs(gamma)) if abs(gamma) < 1 else float('inf')

        gain_dBi, beamwidth_deg, fb_db = procijeni_performanse_niza(nacin_rada, faza_deg, razmak_lambda)

        print("\n" + "=" * 70)
        print(f"REZULTATI IZRAČUNA I PERFORMANSI ({nacin_rada.upper()} NAČIN):")
        print("=" * 70)
        print(f"  Frekvencija:                {f_mhz:.3f} MHz")
        print(f"  Geometrijski razmak:        {udaljenost_vertikala_m:.3f} m ({udaljenost_vertikala_m*100:.1f} cm) [{razmak_lambda} λ]")
        print("-" * 70)
        print(f"  PROCJENA USMJERENOSTI:")
        print(f"    - Usmjereno pojačanje:    ~{gain_dBi:.2f} dBi")
        if nacin_rada == "broadside":
            print(f"    - Širina glavnog snopa:   ~{beamwidth_deg:.1f}° (Dvosmjerna 'osmica')")
        else:
            print(f"    - Širina glavnog snopa:   ~{beamwidth_deg:.1f}° (-3 dB)")
            print(f"    - Odnos naprijed-natrag:  ~{fb_db:.1f} dB (F/B)")
        print("-" * 70)
        print(f"  DULJINE KOAKSIJALNIH KABELA (VF = {vf_50}):")
        if nacin_rada == "christman":
            print(f"    - Fazni kabel (71°):      {duljina_fazni_koaks_m:.3f} m ({duljina_fazni_koaks_m*100:.1f} cm)")
            print(f"    - Napojne linije (84°):   {duljina_q_line_m:.3f} m ({duljina_q_line_m*100:.1f} cm) (svaka vertikala)")
        elif nacin_rada == "endfire":
            print(f"    - Fazni kabel za {faza_deg}°:     {duljina_fazni_koaks_m:.3f} m ({duljina_fazni_koaks_m*100:.1f} cm)")
            print(f"    - 1/4 λ linije do antena: {duljina_q_line_m:.3f} m ({duljina_q_line_m*100:.1f} cm) (svaka vertikala)")
        else:
            print(f"    - Fazni kabel:            NEMA (simetrično napajanje u fazi 0°)")
            print(f"    - 1/4 λ linije do antena: {duljina_q_line_m:.3f} m ({duljina_q_line_m*100:.1f} cm) (svaka vertikala)")
        print("-" * 70)
        print(f"  IMPEDANCIJA na T-SPOJU:     {z_tspoj.real:.2f} + j({z_tspoj.imag:.2f}) Ω")
        print(f"  Početni SWR na 50 Ω:        {swr_50:.2f}:1")
        print("=" * 70)

        if izbor_prilagodbe == "2": # LC mreža
            l_rezultati = izracunaj_l_mrezu(z_tspoj.real, z_tspoj.imag, f_mhz, 50.0)
            if l_rezultati:
                for topologija, c_val, l_val in l_rezultati:
                    print(f"\n" + "#" * 70)
                    print(f"ANALITIČKI IZRAČUN L-MREŽE ({topologija}):")
                    print("#" * 70)
                    print(f"  - Serijska zavojnica (L):     {l_val:.2f} nH")
                    print(f"  - Paralelni kondenzator (C):  {c_val:.2f} pF")

                    izbor_zavojnice = input("\nŽelite li izračunati fizičke dimenzije zračne zavojnice za ovaj induktivitet? (d/n): ").strip().lower()
                    if izbor_zavojnice in ["d", "da", "y", "yes"]:
                        promjer = float(input("  Unesite unutarnji promjer tijela zavojnice (cm) [npr. 4.0]: "))
                        promjer_zice = float(input("  Unesite promjer bakrene žice (mm) [npr. 1.5]: "))
                        zracnost = float(input("  Unesite zračnost/razmak između zavoja (mm) [npr. 1.0]: "))
                        
                        n_zavoja, duljina_namota = izracunaj_zracnu_zavojnicu(l_val, promjer, promjer_zice, zracnost)
                        print(f"\n  --------------------------------------------------")
                        print(f"  REZULTATI ZA ZRAČNU ZAVOJNICU (L = {l_val:.1f} nH):")
                        print(f"    - Broj zavoja (N):          {n_zavoja}")
                        print(f"    - Unutarnji promjer:        {promjer:.1f} cm")
                        print(f"    - Promjer žice / razmak:    {promjer_zice} mm / {zracnost} mm")
                        print(f"    - Ukupna duljina namota:    {duljina_namota:.2f} cm")
                        print(f"  --------------------------------------------------")
                    print("#" * 70)
            
            simuliraj_swr_usporedba_realno(f_mhz, r_ant, x_ant, c_val, l_val, nacin_rada)
        else:
            simuliraj_swr_propusnost(f_mhz, r_ant, x_ant, nacin_rada)

    except ValueError:
        print("\n[Greška] Molimo unesite ispravne brojevne vrijednosti.")

if __name__ == "__main__":
    izracunaj_fazni_sustav()