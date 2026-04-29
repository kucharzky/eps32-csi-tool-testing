import matplotlib.pyplot as plt
import numpy as np
import re
import sys

# ==========================================
# USTAWIENIA SKRYPTU
# ==========================================
FILE_PATH = 'naprawiony_test.csv' 
MAC_FILTER = '98:A3:16:8E:4D:AC' # MAC Twojego nadajnika ESP32-C6

def wczytaj_zawartosc(sciezka):
    """Odczyt całego pliku jako jeden tekst, ignorując uszkodzone znaki"""
    try:
        with open(sciezka, 'r', encoding='utf-16') as f:
            return f.read()
    except UnicodeError:
        with open(sciezka, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()

def main():
    print(f"Wczytywanie i naprawianie danych z pliku: {FILE_PATH}...")
    
    try:
        content = wczytaj_zawartosc(FILE_PATH)
    except FileNotFoundError:
        print(f"BŁĄD: Nie znaleziono pliku '{FILE_PATH}'.")
        sys.exit(1)

    # NAPRAWA 1: Zmieniamy podwójne minusy na pojedyncze (błąd sprzętowy kabla USB)
    content = content.replace('--', '-')

    # Liczymy dla celów diagnostycznych, ile razy w ogóle padło słowo CSI_DATA
    stat_csi_lines = content.count("CSI_DATA")
    
    # NAPRAWA 2: REGEX (Wyrażenia regularne)
    # Wzór: szukamy Twojego MAC, następnie ignorujemy wszystko aż do '[', 
    # a potem wyciągamy wszystkie liczby aż do zamknięcia ']'
    pattern = re.compile(MAC_FILTER + r'[^\[]{1,100}\[([^\]]+)\]')
    matches = pattern.findall(content)
    
    csi_matrix = []
    
    for data_str in matches:
        raw_data = []
        # Konwersja tekstu na liczby całkowite
        for x in data_str.split():
            try:
                raw_data.append(int(x))
            except ValueError:
                pass
        
        amplitudes = []
        # ESP32 wysyła pary: Część Urojona, Część Rzeczywista. Zmieniamy na Amplitudę.
        for i in range(0, len(raw_data) - 1, 2):
            amp = np.sqrt(raw_data[i]**2 + raw_data[i+1]**2)
            amplitudes.append(amp)
        
        # Prawidłowa ramka dla pasma 20MHz ma minimum 64 podnośne
        if len(amplitudes) >= 64:
            # Ucinamy do 64, by mieć idealnie równy prostokąt na heatmapie
            csi_matrix.append(amplitudes[:64])
            
    stat_parsed_ok = len(csi_matrix)

    # --- RAPORT DIAGNOSTYCZNY ---
    print("-" * 40)
    print("RAPORT ODCZYTU (WERSJA AGRESYWNA):")
    print(f"1. Znaleziono tagów CSI_DATA:      {stat_csi_lines}")
    print(f"2. Przetworzonych poprawnie ramek: {stat_parsed_ok}")
    print("-" * 40)

    if stat_parsed_ok == 0:
        print("BŁĄD: Mimo naprawy nie udało się odczytać macierzy.")
        sys.exit(1)

    # Oś Y to podnośne, Oś X to czas
    csi_matrix_np = np.array(csi_matrix).T

    # --- ANALIZA RUCHU ---
    # Uśredniamy najczulsze podnośne na środku pasma (20-40)
    mean_amplitude = np.mean(csi_matrix_np[20:40, :], axis=0) 
    wariancja = np.var(mean_amplitude)
    
    print("ANALIZA SYGNAŁU:")
    print(f"Zmienność sygnału (Wariancja): {wariancja:.2f}")
    
    # Próg 1.5 jest przykładowy, możesz go dostosować po analizie swoich wykresów
    if wariancja > 1.5:
        print("=> DIAGNOZA: Wykryto znaczne zakłócenia sygnału (Prawdopodobny RUCH).")
    else:
        print("=> DIAGNOZA: Sygnał statyczny (Brak ruchu / pusty pokój).")
    print("-" * 40)

    # --- RYSOWANIE WYKRESÓW ---
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 9))

    # HEATMAPA
    im = ax1.imshow(csi_matrix_np, aspect='auto', cmap='jet', origin='lower')
    fig.colorbar(im, ax=ax1, label='Amplituda')
    ax1.set_title(f'Heatmapa CSI - {FILE_PATH}')
    ax1.set_ylabel('Numer podnośnej (0-63)')
    ax1.set_xlabel('Czas (Numer pakietu)')

    # WYKRES LINIOWY
    ax2.plot(mean_amplitude, color='blue', linewidth=1)
    ax2.set_title(f'Uśredniona amplituda (Podnośne 20-40) | Wariancja: {wariancja:.2f}')
    ax2.set_ylabel('Amplituda')
    ax2.set_xlabel('Czas (Numer pakietu)')
    ax2.grid(True)

    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    main()