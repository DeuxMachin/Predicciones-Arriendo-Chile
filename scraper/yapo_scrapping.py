import requests
from bs4 import BeautifulSoup
import time
import json
import os


os.makedirs('./DB', exist_ok=True)

# URL Yapo.cl
BASE_URL = "https://www.yapo.cl/region-metropolitana/arrendar?o={page}"

# Encabezados para emular un navegador y evitar bloqueos
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Accept-Language": "es-CL,es;q=0.9"
}


OUTPUT_FILE = './DB/datos_brutos.json'


def fetch_listings(page: int = 1) -> list:
    """
    Hace una petición HTTP a la página especificada y retorna la lista de bloques de anuncios.
    :param page: Número de página a scrapear
    :return: lista de tags BeautifulSoup correspondientes a anuncios
    """
    url = BASE_URL.format(page=page)
    print(f"Consultando URL: {url}")
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "lxml")
    
    
    # Los anuncios ahora están en elementos con clase d3-ad-tile
    listings = soup.find_all("div", class_="d3-ad-tile")
    print(f"Anuncios encontrados: {len(listings)}")
    return listings


def parse_listing(listing) -> dict:
    """
    Extrae campos clave de un anuncio.
    :param listing: Tag BeautifulSoup de un anuncio
    :return: dict con datos crudos (strings)
    """
    result = {
        "precio": None,
        "comuna": None,
        "area": None,
        "habitaciones": None
    }
    
    # Extraer precio
    precio_element = listing.find("div", class_="d3-ad-tile__price")
    if precio_element:
        result["precio"] = precio_element.get_text(strip=True).split("\n")[0]
    
    # Extraer comuna
    comuna_element = listing.find("div", class_="d3-ad-tile__location")
    if comuna_element and comuna_element.span:
        result["comuna"] = comuna_element.span.get_text(strip=True)
    
    # Extraer detalles (área y habitaciones)
    details_items = listing.find_all("li", class_="d3-ad-tile__details-item")
    for detail in details_items:
        text = detail.get_text(strip=True)
        # Detectar área (m²)
        if "m²" in text:
            result["area"] = text
        # Detectar habitaciones (si solo hay un número, suele ser el número de habitaciones)
        elif len(text.strip()) == 1 and text.isdigit():
            # Verificar si el ícono es de cama (contiene "bed" en su use xlink)
            svg = detail.find("svg")
            if svg and svg.find("use") and "bed" in svg.find("use").get("xlink:href", ""):
                result["habitaciones"] = text
    
    return result


def scrape_pages(max_pages: int = 5, delay: float = 2) -> list:
    """
    Recorre un número de páginas y devuelve lista de anuncios parseados.
    :param max_pages: Cantidad de páginas a scrapear
    :param delay: Tiempo en segundos a esperar entre peticiones
    :return: Lista de dicts con datos de anuncios
    """
    results = []
    for page in range(1, max_pages + 1):
        print(f"Scrapeando página {page}...")
        try:
            listings = fetch_listings(page)
            for item in listings:
                try:
                    data = parse_listing(item)
                    # Solo agregar si hay datos relevantes
                    if any(data.values()):
                        results.append(data)
                except Exception as e:
                    print(f"Error parseando anuncio en página {page}: {e}")
        except Exception as e:
            print(f"Error fetch_listings página {page}: {e}")
        time.sleep(delay)
    return results


if __name__ == "__main__":
    # Ejecutar el scraping y guardar resultados en JSON
    datos = scrape_pages(max_pages=3)
    try:
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)
        print(f"Datos guardados exitosamente en {OUTPUT_FILE}")
        print(f"Total de anuncios obtenidos: {len(datos)}")
    except Exception as e:
        print(f"Error al guardar el archivo JSON: {e}")
