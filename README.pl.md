# Atmoce MQTT — instalacja przez HACS

Integracja lokalna dla **Home Assistant 2026.11+**, z encjami po angielsku. [Pełna dokumentacja](README.md).

1. W HACS wybierz **⋮ → Repozytoria niestandardowe**.
2. Dodaj `https://github.com/MojitoDevelop/ha-atmoce`, typ **Integracja**.
3. Pobierz **Atmoce MQTT** i uruchom ponownie HA.
4. Wybierz **Ustawienia → Urządzenia i usługi → Dodaj integrację → Atmoce MQTT**.
5. Istniejące MQTT zostanie użyte automatycznie. Jeśli go brakuje, wybierz działający oficjalny dodatek Mosquitto z HA lub wpisz adres brokera, użytkownika i hasło. Dane logowania przechowuje oficjalna integracja MQTT. Automatyczna konfiguracja nie instaluje dodatku Mosquitto; można go zainstalować przez podlinkowany formularz HA.
6. Wybierz instalację znalezioną podczas 10-sekundowego nasłuchu. Jeżeli jej nie ma, wpisz SN bramki. Samo dodanie integracji nie wysyła komend.

Dostępne są odczyty mocy PV, sieci i magazynu, SOC, limity mocy, dobowe i całkowite energie oraz kody stanu i trybu. Czujniki całkowitej energii można dodać do panelu Energia.

## Nastawy magazynu

Wpisz **Requested forced power** w kW i **Requested target state of charge** w %, następnie wybierz **Charge**, **Discharge**, **Automatic** albo **Pause** w **Requested battery control**. Zmiana samych liczb przygotowuje parametry w HA; aby je zastosować, wybierz polecenie. Parametry są zapamiętywane, ale po restarcie nie wysyła się ponownie sterowania.

Komendy są zgodne z działającym flow Node-RED: `0` = ładuj, `1` = rozładuj, `2` = Auto, `99` = pauza. Wysyłka trafia na `/config`, QoS 1, bez retain. Ładowanie i rozładowanie wymagają świeżej telemetrii oraz mocy nie większej od aktualnego limitu Atmoce. Akcja **Atmoce MQTT: Set battery control** pozwala podać tryb, moc i SOC w jednym wywołaniu automatyzacji.

Przed sterowaniem z HA wyłącz wyjście komend dotychczasowego sterownika Atmoce w Node-RED albo ustal jednego nadawcę. Działający flow może nadpisywać nastawy z HA. Odczyt telemetrii może pozostać wspólny.

## Odczyt nastaw

W odnalezionej instrukcji MQTT producenta nie ma opisanego zapytania o nastawy ani osobnego potwierdzenia zapisu. Podany działający `/monitor` raportuje stan, tryb i limity, lecz nie raportuje wymuszonej mocy i docelowego SOC. Dlatego encje **Requested…** pokazują żądanie z HA, a czujniki kodu trybu, kodu stanu i limitów pokazują dane urządzenia. Echo polecenia z `/config` nie jest traktowane jako potwierdzenie.

Opcjonalne, domyślnie wyłączone sensory **Reported…** odczytają nastawy wyłącznie wtedy, gdy firmware rzeczywiście doda pola `batteryForced*` do `/monitor`. Nieobecna wartość pozostaje nieznana. Szczegóły i źródło opisano w [pełnej dokumentacji](README.md#reading-settings-protocol-limitation).

Domyślne wygaszanie telemetrii: **180 s**, zmiana przez **Konfiguruj**. Testy korzystają z rzeczywistego HA 2026.11.1 i symulowanego połączenia MQTT. Uruchomienie na instalacji wymaga weryfikacji fizycznego urządzenia.
