import json
import sys

def load_data(filename):
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Fehler: Die Datei '{filename}' wurde nicht gefunden.")
        return None
    except json.JSONDecodeError:
        print(f"Fehler: Die Datei '{filename}' enthält kein gültiges JSON.")
        return None

def main():
    # Daten laden
    data = load_data('data/Dataset_NLPR4E_ID_CARD.json')
    if data is None:
        return

    # Index für schnellen Zugriff erstellen (ID -> Eintrag)
    query_map = {item['id']: item for item in data}

    print("=== SPARQL Query Browser ===")
    print("Anleitung:")
    print("1. Gib die ID (1-100) ein.")
    print("2. Wähle 'q' für die Frage oder 'g' für die Gold Query.")
    print("Tippe 'exit' oder 'quit' zum Beenden.")
    print("-" * 30)

    while True:
        user_input = input("\nGib eine ID ein: ").strip().lower()

        # Beenden-Check
        if user_input in ['exit', 'quit', 'bye']:
            print("Programm beendet. Viel Erfolg!")
            break

        # Validierung der ID
        try:
            target_id = int(user_input)
            if target_id not in query_map:
                print(f"❌ ID {target_id} nicht gefunden. (Verfügbar: 1 bis {len(data)})")
                continue
            
            entry = query_map[target_id]
            
            # Auswahl des Typs
            choice = input("Anzeigen: [q] Frage / [g] Query? ").strip().lower()
            
            if choice == 'q':
                print(f"\n👉 FRAGE (ID {target_id}):")
                print(entry['question'])
            elif choice == 'g':
                print(f"\n🔍 GOLD QUERY (ID {target_id}):")
                print(entry['gold_query'])
            else:
                print("⚠️ Ungültige Auswahl! Bitte nutze 'q' oder 'g'.")

        except ValueError:
            print("⚠️ Bitte gib eine gültige Zahl als ID ein.")

if __name__ == "__main__":
    main()