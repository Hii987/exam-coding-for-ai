"""Lance l'interface : python -m app   (puis http://127.0.0.1:8000)"""
import argparse
import threading
import webbrowser

from analyst import config
from analyst.cleaning import load_clean
from analyst.llm import make_llm
from app.server import App, make_server

ROOT = config.ROOT


def main() -> None:
    p = argparse.ArgumentParser(description="Interface web de l'analyste avec arbitre")
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--no-browser", action="store_true", help="ne pas ouvrir le navigateur")
    a = p.parse_args()
    if not config.CLEAN_CSV.exists():
        raise SystemExit("Données absentes : lancez d'abord python scripts/prepare_data.py")
    print("Chargement des données…")
    app = App(load_clean(config.CLEAN_CSV), make_llm, ROOT / "bench" / "results",
              ROOT / "bench" / "expected.json", config.CLEANING_LOG)
    threading.Thread(target=app.data, daemon=True).start()  # calcule les IC en avance
    server = make_server(app, port=a.port)
    url = f"http://127.0.0.1:{a.port}"
    print(f"Interface prête : {url}   (Ctrl+C pour arrêter)")
    if not a.no_browser:
        threading.Timer(0.6, webbrowser.open, args=(url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nArrêt.")


if __name__ == "__main__":
    main()
