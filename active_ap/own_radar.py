import serial
import matplotlib.pyplot as plt
import numpy as np

# USTAWIENIA - Dopasuj do swoich!
PORT = 'COM3'  # Port Twojego ESP32-CAM
BAUD = 921600
MAC = '98:A3:16:8E:4D:AC' # MAC Twojego ESP32-C6

print(f"Łączenie z portem {PORT}...")
try:
    # Trik na to, by Python NIE resetował płytki przy łączeniu
    ser = serial.Serial()
    ser.port = PORT
    ser.baudrate = BAUD
    ser.dtr = False # Zapobiega wejściu w tryb wgrywania
    ser.rts = False # Zapobiega trzymaniu płytki w resecie
    ser.open()
except Exception as e:
    print(f"Błąd portu: {e}. Upewnij się, że idf.py monitor jest wyłączony w innym oknie!")
    exit()

# Przygotowanie wykresu na żywo
plt.ion()
fig, ax = plt.subplots()
ax.set_title("Odcisk radiowy CSI (1 Podnośna)")
ax.set_ylim(0, 100) # Oś Y - Amplituda, można zwiększyć jeśli dane będą wykraczać
ax.set_ylabel("Amplituda")
ax.set_xlabel("Czas (kolejne pakiety)")

# Będziemy rysować 100 ostatnich pomiarów dla jednej podnośnej
history_len = 100
data_history = [0] * history_len
line_plot, = ax.plot(data_history, color='blue')

print("Radar włączony! Czekam na dane CSI z Twojego nadajnika...")

while True:
    try:
        # Odczyt bezpośrednio z kabla USB, ignorowanie ewentualnych śmieci z kabla
        line = ser.readline().decode('utf-8', errors='ignore').strip()
        
        # Opcjonalnie: odkomentuj poniższą linijkę, jeśli chcesz widzieć każdy odebrany pakiet w konsoli
        # print(line) 

        # Filtrujemy tylko pakiety CSI od naszego nadajnika (ESP32-C6)
        if "CSI_DATA" in line and MAC in line:
            # Wyciągamy surowe dane z nawiasów kwadratowych [...]
            data_str = line.split('[')[1].split(']')[0]
            
            # Zamiana na liczby
            raw_data = []
            for x in data_str.split():
                try:
                    raw_data.append(int(x))
                except ValueError:
                    pass 
            
            # Struktura to pary (część urojona, część rzeczywista)
            # Obliczamy amplitudę dla wybranej podnośnej (np. z indeksów 20 i 21)
            if len(raw_data) > 20:
                imaginary = raw_data[20]
                real = raw_data[21]
                
                # Wzór na amplitudę z liczby zespolonej: sqrt(Re^2 + Im^2)
                amplitude = np.sqrt(imaginary**2 + real**2)
                
                # Aktualizacja historii danych do wykresu
                data_history.append(amplitude)
                data_history.pop(0)
                
                # Aktualizacja samego wykresu na ekranie
                line_plot.set_ydata(data_history)
                fig.canvas.draw()
                fig.canvas.flush_events()
                
    except KeyboardInterrupt:
        print("Zakończono przez użytkownika.")
        break
    except Exception:
        pass # Ignoruj uszkodzone ramki