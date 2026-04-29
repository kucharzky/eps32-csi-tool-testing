import re
import sys

# ==========================================
# USTAWIENIA
# ==========================================
INPUT_FILE = 'first_test_no_movement.csv'  # Nazwa Twojego uszkodzonego pliku
OUTPUT_FILE = 'naprawiony_test.csv'        # Nazwa nowego, czystego pliku

def main():
    print(f"Wczytywanie pliku: {INPUT_FILE}...")
    
    # Krok 1: Wczytanie całego pliku (z obsługą kodowania PowerShell i CMD)
    try:
        with open(INPUT_FILE, 'r', encoding='utf-16') as f:
            content = f.read()
    except UnicodeError:
        try:
            with open(INPUT_FILE, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except FileNotFoundError:
            print(f"BŁĄD: Nie znaleziono pliku '{INPUT_FILE}'.")
            sys.exit(1)

    oryginalna_dlugosc = len(content)
    print("Skanowanie i naprawianie sklejonych linii... (to może potrwać kilka sekund)")

    # Krok 2: Naprawa błędu 1 - Jest nawias ']', ale nie ma nowej linii przed 'CSI_DATA'
    # Szukamy: znaku ']', ewentualnych spacji, a potem 'CSI_DATA'
    # Zamieniamy na: ']\nCSI_DATA'
    content, count1 = re.subn(r'\]\s*(CSI_DATA)', r']\n\1', content)

    # Krok 3: Naprawa błędu 2 - Brakuje nawiasu ']' ORAZ nowej linii
    # Szukamy: cyfry (0-9) na końcu pomiarów, ewentualnych spacji, a potem 'CSI_DATA'
    # Zamieniamy na: '[cyfra] ]\nCSI_DATA'
    content, count2 = re.subn(r'([0-9])\s*(CSI_DATA)', r'\1 ]\n\2', content)

    # Opcjonalnie: Naprawa podwójnych minusów (częsty błąd z kabla)
    content, count3 = re.subn(r'--', r'-', content)

    # Krok 4: Zapis naprawionego pliku do standardowego formatu UTF-8
    print(f"Zapisywanie czystego pliku: {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(content)

    # --- PODSUMOWANIE ---
    print("\n" + "="*40)
    print("RAPORT Z NAPRAWY:")
    print(f"Rozdzielono linii z brakującym '\\n': {count1}")
    print(f"Dodano brakujący nawias ']' i '\\n': {count2}")
    print(f"Naprawiono podwójne minusy:           {count3}")
    print("="*40)
    print(f"Gotowe! Użyj pliku '{OUTPUT_FILE}' do dalszej analizy i wykresów.")

if __name__ == "__main__":
    main()