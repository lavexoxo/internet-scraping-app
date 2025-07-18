import requests
from bs4 import BeautifulSoup
import sqlite3
from datetime import datetime
import time
import re
from urllib.parse import urljoin, urlparse

class PhoneForumScraper:
    def __init__(self, db_name="scraper_data.db"):
        self.db_name = db_name
        self.init_forum_database()
        
        # Forumuri predefinite legate de telefoane
        self.predefined_forums = [
            {
                'name': 'GSMArena Forum',
                'url': 'https://www.gsmarena.com/forum/',
                'post_selector': '.post-content',
                'title_selector': '.post-title h3',
                'author_selector': '.post-author',
                'keywords': ['iphone', 'samsung', 'android', 'review', 'specs']
            },
            {
                'name': 'XDA Developers',
                'url': 'https://forum.xda-developers.com/c/mobile-phones.12/',
                'post_selector': 'article[data-content="structItem"]',
                'title_selector': '.structItem-title a',
                'author_selector': '.username',
                'keywords': ['custom rom', 'root', 'android', 'development']
            },
            {
                'name': 'Reddit Mobile Phones',
                'url': 'https://www.reddit.com/r/phones/',
                'post_selector': '.Post',
                'title_selector': 'h3[data-testid="post-content-title"]',
                'author_selector': '[data-testid="post_author_link"]',
                'keywords': ['phone recommendation', 'review', 'comparison']
            }
        ]
        
        # Simulam date pentru demo (in loc de scraping real)
        self.demo_posts = {
            'GSMArena Forum': [
                {
                    'title': 'iPhone 15 Pro Review - Camera Performance Analysis',
                    'author': 'TechReviewer2024',
                    'content': 'After testing the iPhone 15 Pro for 2 weeks, the camera improvements are significant. The new 48MP sensor delivers excellent detail in daylight conditions...',
                    'date': '2024-12-20',
                    'keywords_found': ['iphone', 'review']
                },
                {
                    'title': 'Samsung Galaxy S24 Ultra vs iPhone 15 Pro Max Comparison',
                    'author': 'MobileExpert',
                    'content': 'Detailed comparison between the two flagship phones. Samsung wins in display quality and S Pen functionality, while iPhone excels in video recording...',
                    'date': '2024-12-19',
                    'keywords_found': ['samsung', 'iphone', 'comparison']
                },
                {
                    'title': 'Best Android Phones Under $500 in 2024',
                    'author': 'BudgetPhoneFan',
                    'content': 'Here are the top Android phones that offer excellent value for money. Google Pixel 7a leads the pack with its camera performance...',
                    'date': '2024-12-18',
                    'keywords_found': ['android', 'review']
                }
            ],
            'XDA Developers': [
                {
                    'title': 'LineageOS 21 Now Available for Samsung Galaxy S23',
                    'author': 'DevMaster',
                    'content': 'The latest LineageOS 21 build is now available for Galaxy S23 users. This custom ROM brings Android 14 features with improved battery life...',
                    'date': '2024-12-20',
                    'keywords_found': ['custom rom', 'android', 'samsung']
                },
                {
                    'title': 'Root Method for iPhone 15 Using checkm8 Exploit',
                    'author': 'iOSHacker',
                    'content': 'New jailbreak method discovered for iPhone 15 series. This method uses the checkm8 bootrom exploit and works on iOS 17.1...',
                    'date': '2024-12-19',
                    'keywords_found': ['root', 'iphone', 'development']
                }
            ],
            'Reddit Mobile Phones': [
                {
                    'title': 'What phone should I buy for photography?',
                    'author': 'PhotoEnthusiast',
                    'content': 'Looking for a phone with the best camera for under $800. I mainly shoot landscapes and portraits. Any recommendations?',
                    'date': '2024-12-20',
                    'keywords_found': ['phone recommendation']
                },
                {
                    'title': 'OnePlus 12 Review - 6 months later',
                    'author': 'LongTermUser',
                    'content': 'After using the OnePlus 12 for 6 months, here are my thoughts on performance, battery life, and overall experience...',
                    'date': '2024-12-19',
                    'keywords_found': ['review']
                }
            ]
        }
    
    def init_forum_database(self):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS phone_forums (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                url TEXT NOT NULL,
                keywords TEXT,
                last_check TEXT,
                active INTEGER DEFAULT 1
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS phone_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                forum_id INTEGER,
                title TEXT,
                author TEXT,
                content TEXT,
                post_date TEXT,
                keywords_found TEXT,
                scraped_date TEXT,
                FOREIGN KEY (forum_id) REFERENCES phone_forums (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def setup_predefined_forums(self):
        """Adauga forumurile predefinite in baza de date"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        # sterge forumurile existente pentru a evita duplicate
        cursor.execute('DELETE FROM phone_forums')
        cursor.execute('DELETE FROM phone_posts')
        
        for forum in self.predefined_forums:
            keywords_str = ','.join(forum['keywords'])
            cursor.execute('''
                INSERT INTO phone_forums (name, url, keywords, last_check)
                VALUES (?, ?, ?, ?)
            ''', (forum['name'], forum['url'], keywords_str, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        
        print("Forumuri predefinite adaugate cu succes!")
        print("Forumuri disponibile:")
        for forum in self.predefined_forums:
            print(f"- {forum['name']}: {', '.join(forum['keywords'])}")
    
    def simulate_forum_scraping(self):
        """Simuleaza scraping-ul forumurilor cu date demo"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        # Obtine ID-urile forumurilor
        cursor.execute('SELECT id, name FROM phone_forums')
        forums = cursor.fetchall()
        
        if not forums:
            print("Nu exista forumuri! Ruleaza mai intai setup_predefined_forums()")
            conn.close()
            return
        
        print("Simulez scraping-ul forumurilor de telefoane...")
        
        total_new_posts = 0
        
        for forum_id, forum_name in forums:
            print(f"\nScrapez: {forum_name}")
            
            # Obtine postarile demo pentru acest forum
            demo_posts = self.demo_posts.get(forum_name, [])
            
            for post in demo_posts:
                keywords_str = ','.join(post['keywords_found'])
                
                cursor.execute('''
                    INSERT INTO phone_posts 
                    (forum_id, title, author, content, post_date, keywords_found, scraped_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    forum_id, post['title'], post['author'], post['content'], 
                    post['date'], keywords_str, datetime.now().isoformat()
                ))
                
                total_new_posts += 1
                print(f"  + {post['title'][:50]}...")
            
            # Actualizeaza ultima verificare
            cursor.execute('UPDATE phone_forums SET last_check = ? WHERE id = ?', 
                          (datetime.now().isoformat(), forum_id))
            
            time.sleep(1)  
        
        conn.commit()
        conn.close()
        
        print(f"\nScraping terminat! Adaugate {total_new_posts} postari noi.")
    
    def search_phone_discussions(self, keyword):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT f.name, p.title, p.author, p.content, p.post_date, p.keywords_found
            FROM phone_posts p
            JOIN phone_forums f ON p.forum_id = f.id
            WHERE p.title LIKE ? OR p.content LIKE ? OR p.keywords_found LIKE ?
            ORDER BY p.post_date DESC
            LIMIT 10
        ''', (f'%{keyword}%', f'%{keyword}%', f'%{keyword}%'))
        
        results = cursor.fetchall()
        
        if results:
            print(f"\nRezultate pentru '{keyword}':")
            print("=" * 80)
            
            for forum_name, title, author, content, post_date, keywords in results:
                print(f"Forum: {forum_name}")
                print(f"Titlu: {title}")
                print(f"Autor: {author} | Data: {post_date}")
                print(f"Keywords: {keywords}")
                print(f"Preview: {content[:150]}...")
                print("-" * 80)
        else:
            print(f"Nu am gasit discutii despre '{keyword}'")
        
        conn.close()
    
    def get_phone_recommendations(self):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT f.name, p.title, p.author, p.content, p.post_date
            FROM phone_posts p
            JOIN phone_forums f ON p.forum_id = f.id
            WHERE p.keywords_found LIKE '%phone recommendation%' 
            OR p.title LIKE '%recommendation%'
            OR p.title LIKE '%should I buy%'
            OR p.title LIKE '%best phone%'
            ORDER BY p.post_date DESC
        ''')
        
        results = cursor.fetchall()
        
        if results:
            print("\nRecomandari de telefoane din forumuri:")
            print("=" * 80)
            
            for forum_name, title, author, content, post_date in results:
                print(f"Forum: {forum_name}")
                print(f"intrebare: {title}")
                print(f"De la: {author} | {post_date}")
                print(f"Detalii: {content[:200]}...")
                print("-" * 80)
        else:
            print("Nu am gasit recomandari de telefoane")
        
        conn.close()
    
    def get_phone_reviews(self):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT f.name, p.title, p.author, p.content, p.post_date
            FROM phone_posts p
            JOIN phone_forums f ON p.forum_id = f.id
            WHERE p.keywords_found LIKE '%review%'
            OR p.title LIKE '%review%'
            OR p.title LIKE '%analysis%'
            ORDER BY p.post_date DESC
        ''')
        
        results = cursor.fetchall()
        
        if results:
            print("\nReview-uri de telefoane:")
            print("=" * 80)
            
            for forum_name, title, author, content, post_date in results:
                print(f"Forum: {forum_name}")
                print(f"Review: {title}")
                print(f"Reviewer: {author} | {post_date}")
                print(f"Preview: {content[:200]}...")
                print("-" * 80)
        else:
            print("Nu am gasit review-uri")
        
        conn.close()
    
    def get_forum_stats(self):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT f.name, COUNT(p.id) as posts_count,
                   MAX(p.post_date) as latest_post
            FROM phone_forums f
            LEFT JOIN phone_posts p ON f.id = p.forum_id
            GROUP BY f.id
            ORDER BY posts_count DESC
        ''')
        
        results = cursor.fetchall()
        
        if results:
            print("\nStatistici forumuri telefoane:")
            print("=" * 60)
            
            total_posts = 0
            for forum_name, posts_count, latest_post in results:
                total_posts += posts_count
                latest = latest_post or 'Niciodata'
                print(f"{forum_name:<25} | {posts_count:3d} postari | {latest}")
            
            print("=" * 60)
            print(f"Total postari colectate: {total_posts}")
        
        conn.close()
    
    def list_forums(self):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('SELECT name, url, keywords FROM phone_forums')
        forums = cursor.fetchall()
        
        if forums:
            print("\nForumuri telefoane configurate:")
            print("=" * 80)
            for name, url, keywords in forums:
                print(f"Nume: {name}")
                print(f"URL: {url}")
                print(f"Keywords: {keywords}")
                print("-" * 80)
        else:
            print("Nu sunt forumuri configurate")
        
        conn.close()


def show_forum_menu():
    print("\n" + "="*50)
    print("=== FORUM SCRAPER TELEFOANE ===")
    print("1. Configureaza forumurile predefinite")
    print("2. Simuleaza scraping forumuri")
    print("3. Cauta discutii despre telefoane")
    print("4. Gaseste recomandari de telefoane")
    print("5. Gaseste review-uri telefoane")
    print("6. Vezi statistici forumuri")
    print("7. Listeaza forumuri configurate")
    print("0. Iesire")
    print("="*50)

def main_phone_forums():
    scraper = PhoneForumScraper()
    
    show_forum_menu()
    
    while True:
        choice = input("\nAlegeti o optiune: ")
        
        if choice == '1':
            scraper.setup_predefined_forums()
            show_forum_menu()
        
        elif choice == '2':
            scraper.simulate_forum_scraping()
            show_forum_menu()
        
        elif choice == '3':
            keyword = input("Cauta dupa (ex: iPhone, Samsung, Android): ")
            if keyword:
                scraper.search_phone_discussions(keyword)
            show_forum_menu()
        
        elif choice == '4':
            scraper.get_phone_recommendations()
            show_forum_menu()
        
        elif choice == '5':
            scraper.get_phone_reviews()
            show_forum_menu()
        
        elif choice == '6':
            scraper.get_forum_stats()
            show_forum_menu()
        
        elif choice == '7':
            scraper.list_forums()
            show_forum_menu()
        
        elif choice == '0':
            break
        
        else:
            print("Optiune invalida!")
            show_forum_menu()


if __name__ == "__main__":
    main_phone_forums()