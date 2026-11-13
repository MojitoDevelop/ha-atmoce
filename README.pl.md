# Atmoce dla Home Assistant

[![Dodaj do HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=MojitoDevelop&repository=ha-atmoce&category=integration)
[![Najnowsze wydanie](https://img.shields.io/github/v/release/MojitoDevelop/ha-atmoce)](https://github.com/MojitoDevelop/ha-atmoce/releases)

Lokalna integracja systemów fotowoltaicznych i magazynów energii Atmoce z Home Assistant. Umożliwia odczyt produkcji PV, wymiany energii z siecią, stanu i przepływów magazynu oraz sterowanie ładowaniem i rozładowaniem przez MQTT. Nie wymaga konta w chmurze Atmoce.

[Full documentation in English](README.md)

## Możliwości

- Moc PV, sieci i magazynu, SOC oraz aktualne limity mocy.
- Dobowe i całkowite liczniki energii zgodne z panelem Energia.
- Ładowanie, rozładowanie, tryb automatyczny i pauza, z nastawą mocy oraz docelowego SOC.
- Wykrywanie bramek, wybór instalacji lub ręczne wpisanie SN.
- Wykorzystanie MQTT skonfigurowanego w HA, automatyczna konfiguracja działającego Mosquitto albo ręczne podanie brokera i danych logowania.
- Angielskie nazwy encji, kontrola dostępności i dane diagnostyczne.

## Wymagania i instalacja

Wymagany jest **Home Assistant 2026.10.0 lub nowszy** oraz bramka Atmoce publikująca dane do tego samego brokera MQTT co HA. Integracja została przetestowana na HA 2026.10.0 i 2026.11.1.

1. Kliknij **Dodaj do HACS**, pobierz **Atmoce** i uruchom ponownie HA. Link działa z HACS w HA 2026.10 oraz z Marketplace w HA 2026.11+.
2. Otwórz **Ustawienia → Urządzenia i usługi → Dodaj integrację → Atmoce**.
3. Istniejące połączenie MQTT zostanie użyte automatycznie. Jeżeli go brakuje, wybierz działający oficjalny dodatek Mosquitto albo podaj adres brokera, port, użytkownika i hasło. Można włączyć TLS ze sprawdzaniem certyfikatu.
4. Wybierz instalację znalezioną podczas 10-sekundowego nasłuchu. Jeżeli jej nie ma, wpisz **numer seryjny bramki (SN)**.

Ręczne dodawanie repozytorium w HACS / Marketplace: **⋮ → Repozytoria niestandardowe**, adres `https://github.com/MojitoDevelop/ha-atmoce`, typ **Integracja**.

Bez HACS można rozpakować `atmoce_mqtt.zip` z wydania do `/config/custom_components/atmoce_mqtt/`, a następnie ponownie uruchomić HA. Plik `manifest.json` powinien znajdować się bezpośrednio w tym katalogu.

Samo dodanie integracji nie wysyła komend. Automatyczna konfiguracja MQTT nie instaluje brokera i nie zmienia ustawień bramki. Obsługiwana telemetria używa pól `systemTime`, `gridActivePower`, mocy w kW i energii w kWh.

## Odczyty i panel Energia

Każda bramka tworzy urządzenie `Atmoce <SN>`, z encjami po angielsku. Dostępne są moce, SOC, limity mocy, dobowe i całkowite energie oraz opisowe stany i tryby pracy. **Battery status** pokazuje `charging`, `discharging` albo `idle`; **Battery operating mode** — `self consumption`, `time of use` albo `remote control`; **Plant status** — `normal` albo `fault`. Opisy są po angielsku, małymi literami. Nieznany kod pozostawia stan nieznany, a numer jest dostępny w atrybucie `raw_code`.

Aktualizacja zachowuje identyfikatory encji i historię. Dotychczasowe identyfikatory zakończone na `_code` nadal działają. W automatyzacjach tryby pracy mają stany `self_consumption`, `time_of_use` i `remote_control`.

W panelu **Energia** wybierz całkowite liczniki produkcji PV, importu i eksportu oraz ładowania i rozładowania magazynu. Pełna lista encji znajduje się w [dokumentacji angielskiej](README.md#entities).

Domyślny czas ważności danych to **180 sekund**, zmieniany przez **Konfiguruj**. Po utracie MQTT lub wygaśnięciu telemetrii odczyty stają się niedostępne. Brakujące wartości pozostają nieznane.

## Sterowanie magazynem

1. Ustaw **Requested forced power** w kW.
2. Ustaw **Requested target state of charge** w pełnych procentach.
3. Wybierz **Charge**, **Discharge**, **Automatic** albo **Pause** w **Requested battery control**.

Zmiana samych liczb przygotowuje parametry w HA. Aby je zastosować, wybierz polecenie. Parametry są zapamiętywane, ale po restarcie sterowanie nie jest wysyłane ponownie.

Ładowanie i rozładowanie wymagają świeżej telemetrii oraz mocy nieprzekraczającej bieżącego limitu urządzenia. Akcja **Atmoce: Set battery control** pozwala podać tryb, moc i SOC w jednym wywołaniu automatyzacji. Dla jednej bramki należy używać jednego aktywnego sterownika, aby polecenia nie były wzajemnie nadpisywane.

Encje **Requested…** pokazują żądania z HA. Opisy trybu, stanu i limity pokazują dane urządzenia. Interfejs MQTT nie opisuje osobnego zapytania o nastawy ani potwierdzenia zapisu. Opcjonalne sensory **Reported…** dostarczą odczyt nastaw wyłącznie wtedy, gdy firmware rzeczywiście publikuje odpowiednie pola w telemetrii; domyślnie są wyłączone.

## Wydania i aktualizacje

Wydania mają numery **vMAJOR.MINOR.PATCH**, np. **v0.1.1**, zgodne z wersją w manifeście integracji. Wybierz wydanie w HACS / Marketplace, zainstaluj aktualizację i uruchom ponownie HA.

Każde wydanie zawiera paczkę `atmoce_mqtt.zip`, sumę SHA-256 oraz [opis zmian](CHANGELOG.md). Nowe wydanie powstaje automatycznie po zmianie numeru wersji, uzupełnieniu changelogu i przejściu testów, Hassfest oraz walidacji HACS.

Działanie na fizycznym urządzeniu wymaga potwierdzenia na instalacji. Zacznij od sprawdzenia odczytów, a potem zweryfikuj sterowanie z niewielką mocą.
