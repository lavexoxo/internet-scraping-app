import requests
from bs4 import BeautifulSoup
import sqlite3
from datetime import datetime
import time
import re

class SmartPriceScraper:
    def __init__(self, db_name="prices.db"):
        self.db_name = db_name
        self.init_database()
        
        self.price_selectors = [
            '.product-new-price', '.product-price', '.price-new',
            '.Price-current', '.price-current', '.current-price',
            '.product-price-value', '.price-value', '.price',
            '.price-current', '.product-price',
            '[class*="price"]', '[class*="cost"]', '[class*="amount"]',
            '.price', '.cost', '.amount', '.value',
            '[property="product:price:amount"]', '[property="price"]'
        ]
        
        self.title_selectors = [
            'h1', '.product-title', '.product-name', 
            '[property="og:title"]', 'title',
            '.page-title', '.main-title', '.product-heading'
        ]
    
    def init_database(self):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                url TEXT NOT NULL,
                selector TEXT NOT NULL,
                site_name TEXT NOT NULL,
                auto_detected INTEGER DEFAULT 1
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER,
                price REAL,
                date_scraped TEXT,
                FOREIGN KEY (product_id) REFERENCES products (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def extract_price(self, text):
        if not text:
            return None
            
        text = re.sub(r'[^\d.,\s]', '', text)
        
        price_patterns = [
            r'(\d{1,3}(?:[.,]\d{3})*[.,]\d{2})',  
            r'(\d{1,3}(?:[.,]\d{3})+)',           
            r'(\d+[.,]\d{2})',                    
            r'(\d+)'                              
        ]
        
        for pattern in price_patterns:
            matches = re.findall(pattern, text)
            if matches:
                price_str = matches[0].replace(',', '.')
                try:
                    price = float(price_str)
                    if 10 <= price <= 50000: 
                        return price
                except ValueError:
                    continue
        
        return None
    
    def detect_site_name(self, url):
        import urllib.parse
        domain = urllib.parse.urlparse(url).netloc
        
        site_names = {
            'emag.ro': 'eMAG',
            'altex.ro': 'Altex',
            'pcgarage.ro': 'PC Garage',
            'flanco.ro': 'Flanco',
            'cel.ro': 'CEL.ro',
            'dedeman.ro': 'Dedeman',
            'amazon.com': 'Amazon',
            'amazon.co.uk': 'Amazon UK'
        }
        
        for site_domain, site_name in site_names.items():
            if site_domain in domain:
                return site_name
        
        return domain.replace('www.', '').split('.')[0].title()
    
    def get_page_content(self, url):
        """Obtine continutul paginii"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'ro-RO,ro;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            return response.content
            
        except Exception as e:
            print(f"Eroare la accesarea paginii: {e}")
            return None
    
    def detect_product_name(self, soup, url):
        for selector in self.title_selectors:
            try:
                if selector.startswith('['):
                    element = soup.select_one(selector)
                    if element:
                        content = element.get('content') or element.get_text(strip=True)
                        if content and len(content) > 10:
                            return content[:100]  
                else:
                    element = soup.select_one(selector)
                    if element:
                        text = element.get_text(strip=True)
                        if text and len(text) > 5:
                            return text[:100]
            except:
                continue
        
        # Fallback: Incearca sa extraga din URL
        import urllib.parse
        path = urllib.parse.urlparse(url).path
        product_name = path.split('/')[-1].replace('-', ' ').replace('_', ' ')
        if product_name and len(product_name) > 3:
            return product_name[:50]
        
        return f"Produs de pe {self.detect_site_name(url)}"
    
    def detect_price_selector(self, soup):
        emag_selectors = [
            '.product-new-price', '.product-price', '[itemprop="price"]', '[data-product-price]', '[data-price]'
        ]
        cel_selectors = [
            '.pret_n', '.pret', '[itemprop="price"]', '[data-price]'
        ]
        all_selectors = emag_selectors + cel_selectors + self.price_selectors

        for selector in all_selectors:
            try:
                elements = soup.select(selector)
                if selector in ['.product-new-price', '.pret_n']:
                    if elements:
                        price = self.extract_emag_price(elements[0])
                        if price:
                            return selector, price
                    continue  
                for element in elements:
                    price = None
                    if element.has_attr('content'):
                        price = self.extract_price(element['content'])
                    if not price and element.has_attr('data-price'):
                        price = self.extract_price(element['data-price'])
                    if not price and element.has_attr('data-product-price'):
                        price = self.extract_price(element['data-product-price'])
                    if not price:
                        price = self.extract_price(element.get_text(strip=True))
                    if price:
                        return selector, price
            except Exception:
                continue

        return None, None
    
    def auto_add_product(self, url):
        print(f"Analizez pagina: {url}")
        
        content = self.get_page_content(url)
        if not content:
            print(" Nu pot accesa pagina")
            return False
        
        soup = BeautifulSoup(content, 'html.parser')
        
        product_name = self.detect_product_name(soup, url)
        print(f" Produs detectat: {product_name}")
        
        price_selector, detected_price = self.detect_price_selector(soup)
        
        if not price_selector:
            print(" Nu am gasit pretul pe aceasta pagina")
            return False
        
        print(f" Pret detectat: {detected_price} RON (selector: {price_selector})")
        
        site_name = self.detect_site_name(url)
        print(f" Site: {site_name}")
        
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO products (name, url, selector, site_name, auto_detected)
            VALUES (?, ?, ?, ?, 1)
        ''', (product_name, url, price_selector, site_name))
        
        product_id = cursor.lastrowid
        
        cursor.execute('''
            INSERT INTO prices (product_id, price, date_scraped)
            VALUES (?, ?, ?)
        ''', (product_id, detected_price, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        
        print(" Produs adaugat cu succes!")
        return True
    
    def scrape_price(self, url, selector):
        content = self.get_page_content(url)
        if not content:
            return None
        
        soup = BeautifulSoup(content, 'html.parser')
        
        try:
            price_element = soup.select_one(selector)
            if price_element:
                price_text = price_element.get_text(strip=True)
                return self.extract_price(price_text)
        except Exception as e:
            print(f"Eroare la extragerea pretului: {e}")
        
        return None
    
    def scrape_all_products(self):
        """Scrapeaza toate produsele din baza de date"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('SELECT id, name, url, selector, site_name FROM products')
        products = cursor.fetchall()
        
        if not products:
            print("Nu exista produse de monitorizat!")
            conn.close()
            return
        
        print(f"Scrapez {len(products)} produse...")
        
        for product in products:
            product_id, name, url, selector, site_name = product
            print(f"\n {name} ({site_name})")
            
            price = self.scrape_price(url, selector)
            
            if price:
                cursor.execute('''
                    INSERT INTO prices (product_id, price, date_scraped)
                    VALUES (?, ?, ?)
                ''', (product_id, price, datetime.now().isoformat()))
                
                print(f" Pret: {price} RON")
            else:
                print(" Nu s-a gasit pretul")
            
            time.sleep(3)  # Pauza între requests
        
        conn.commit()
        conn.close()
        print("\n Scraping terminat!")
    
    def get_price_history(self, product_name):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT p.name, p.site_name, pr.price, pr.date_scraped
            FROM products p
            JOIN prices pr ON p.id = pr.product_id
            WHERE p.name LIKE ?
            ORDER BY pr.date_scraped DESC
            LIMIT 20
        ''', (f'%{product_name}%',))
        
        results = cursor.fetchall()
        
        if results:
            print(f"\n Istoricul preturilor pentru '{product_name}':")
            print("-" * 60)
            for name, site, price, date in results:
                date_formatted = date[:19].replace('T', ' ')
                print(f"{date_formatted} | {site:15} | {price:8.2f} RON")
        else:
            print(f" Nu exista date pentru '{product_name}'")
        
        conn.close()
    
    def compare_prices(self, product_name):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT p.site_name, 
                   MIN(pr.price) as min_price, 
                   MAX(pr.price) as max_price,
                   AVG(pr.price) as avg_price, 
                   COUNT(*) as count,
                   MAX(pr.date_scraped) as last_update
            FROM products p
            JOIN prices pr ON p.id = pr.product_id
            WHERE p.name LIKE ?
            GROUP BY p.site_name
            ORDER BY min_price ASC
        ''', (f'%{product_name}%',))
        
        results = cursor.fetchall()
        
        if results:
            print(f"\n Comparatie preturi pentru '{product_name}':")
            print("-" * 80)
            print(f"{'Site':<15} | {'Min':<8} | {'Max':<8} | {'Mediu':<8} | {'Ultima'}")
            print("-" * 80)
            
            for site, min_price, max_price, avg_price, count, last_update in results:
                last_date = last_update[:10] if last_update else 'N/A'
                print(f"{site:<15} | {min_price:8.2f} | {max_price:8.2f} | {avg_price:8.2f} | {last_date}")
        else:
            print(f" Nu exista date pentru '{product_name}'")
        
        conn.close()
    
    def list_products(self):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT p.name, p.site_name, p.url, COUNT(pr.id) as price_count,
                   MAX(pr.date_scraped) as last_scrape
            FROM products p
            LEFT JOIN prices pr ON p.id = pr.product_id
            GROUP BY p.id
            ORDER BY last_scrape DESC
        ''')
        products = cursor.fetchall()
        
        if products:
            print("\n Produse monitorizate:")
            print("-" * 80)
            for name, site, url, count, last_scrape in products:
                last_date = last_scrape[:10] if last_scrape else 'Niciodata'
                print(f" {name[:40]:<40} | {site:<12} | {count:3d} preturi | {last_date}")
        else:
            print(" Nu exista produse monitorizate")
        
        conn.close()
    
    def extract_emag_price(self, element):
        try:
            main = element.find(text=True, recursive=False)
            sup = element.find('sup')
            if main:
                main = main.replace('\xa0', '').replace('Lei', '').replace('lei', '').replace('RON', '').strip()
                main = re.sub(r'[^\d]', '', main)
            if sup:
                sup_val = sup.get_text(strip=True)
                price_str = f"{main}.{sup_val}"
            else:
                price_str = main
            return self.extract_price(price_str)
        except Exception:
            return None
def main():
    scraper = SmartPriceScraper()
    
    while True:
        print("\n === APLICATIE SCRAPING PRETURI AUTOMATA ===")
        print("1.  Adauga produs (doar URL)")
        print("2.  Scrapeaza toate produsele")
        print("3.  Vezi istoricul preturilor")
        print("4.   Compara preturi")
        print("5.  Listeaza produse")
        print("0.  Iesire")
        
        choice = input("\n Alegeti o optiune: ")
        
        if choice == '1':
            url = input(" Introduceti URL-ul produsului: ").strip()
            if url:
                scraper.auto_add_product(url)
            else:
                print(" URL invalid!")
        
        elif choice == '2':
            scraper.scrape_all_products()
        
        elif choice == '3':
            scraper.list_products()
            product_name = input("\n Introduceti numele produsului (sau parte din nume): ")
            if product_name:
                scraper.get_price_history(product_name)
        
        elif choice == '4':
            scraper.list_products()
            product_name = input("\n Introduceti numele produsului pentru comparatie: ")
            if product_name:
                scraper.compare_prices(product_name)
        
        elif choice == '5':
            scraper.list_products()
        
        elif choice == '0':
            print(" La revedere!")
            break
        
        else:
            print(" Optiune invalida!")


if __name__ == "__main__":
    main()