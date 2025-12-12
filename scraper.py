import requests
from bs4 import BeautifulSoup
import time
import re
from database import SessionLocal, Phone, init_db

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

BASE_URL = "https://www.gsmarena.com"


def get_samsung_phone_links():
    """Get links to Samsung phone pages from GSMArena"""
    samsung_phones = []

    # Samsung brand page - multiple pages of phones
    urls = [
        f"{BASE_URL}/samsung-phones-9.php",
        f"{BASE_URL}/samsung-phones-f-9-0-p2.php",
    ]

    for url in urls:
        try:
            response = requests.get(url, headers=HEADERS, timeout=30)
            soup = BeautifulSoup(response.text, 'html.parser')

            # Find phone listings
            phone_list = soup.find('div', class_='makers')
            if phone_list:
                links = phone_list.find_all('a')
                for link in links:
                    phone_url = link.get('href')
                    phone_name = link.find('span')
                    if phone_url and phone_name:
                        name = phone_name.text.strip()
                        # Filter for Galaxy S and A series (flagship and mid-range)
                        if any(series in name for series in ['Galaxy S2', 'Galaxy S1', 'Galaxy A5', 'Galaxy A7', 'Galaxy Z', 'Galaxy Note']):
                            samsung_phones.append({
                                'name': name,
                                'url': f"{BASE_URL}/{phone_url}"
                            })

            time.sleep(2)  # Be respectful to the server

        except Exception as e:
            print(f"Error fetching {url}: {e}")

    # Return unique phones, limited to 30
    seen = set()
    unique_phones = []
    for phone in samsung_phones:
        if phone['name'] not in seen:
            seen.add(phone['name'])
            unique_phones.append(phone)

    return unique_phones[:30]


def extract_spec(soup, spec_name):
    """Extract a specific specification from the phone page"""
    try:
        spec_row = soup.find('td', class_='nfo', attrs={'data-spec': spec_name})
        if spec_row:
            return spec_row.text.strip()

        # Alternative: find by table header
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                th = row.find('th')
                td = row.find('td', class_='nfo')
                if th and td and spec_name.lower() in th.text.lower():
                    return td.text.strip()
    except:
        pass
    return "N/A"


def scrape_phone_details(url, name):
    """Scrape detailed specifications for a single phone"""
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        soup = BeautifulSoup(response.text, 'html.parser')

        specs = {
            'model_name': name,
            'url': url,
            'release_date': 'N/A',
            'display': 'N/A',
            'battery': 'N/A',
            'camera': 'N/A',
            'ram': 'N/A',
            'storage': 'N/A',
            'price': 'N/A',
            'chipset': 'N/A',
            'os': 'N/A',
            'body': 'N/A'
        }

        # First, try to get quick specs from the highlight section (data-spec attributes)
        # Battery from quick specs
        batsize = soup.find('span', attrs={'data-spec': 'batsize-hl'})
        if batsize:
            battery_mah = batsize.text.strip()
            battype = soup.find('div', attrs={'data-spec': 'battype-hl'})
            if battype:
                specs['battery'] = f"{battery_mah} mAh, {battype.text.strip()}"
            else:
                specs['battery'] = f"{battery_mah} mAh"

        # RAM from quick specs
        ramsize = soup.find('span', attrs={'data-spec': 'ramsize-hl'})
        if ramsize:
            specs['ram'] = f"{ramsize.text.strip()} GB"

        # Chipset from quick specs
        chipset_hl = soup.find('div', attrs={'data-spec': 'chipset-hl'})
        if chipset_hl:
            specs['chipset'] = chipset_hl.text.strip()

        # Display from quick specs
        displaysize = soup.find('span', attrs={'data-spec': 'displaysize-hl'})
        displayres = soup.find('div', attrs={'data-spec': 'displayres-hl'})
        if displaysize or displayres:
            display_parts = []
            if displaysize:
                display_parts.append(displaysize.text.strip())
            if displayres:
                display_parts.append(displayres.text.strip())
            specs['display'] = ', '.join(display_parts)

        # Camera from quick specs
        camerapixels = soup.find('span', attrs={'data-spec': 'camerapixels-hl'})
        if camerapixels:
            specs['camera'] = f"{camerapixels.text.strip()} MP main"

        # Storage from quick specs
        storage_hl = soup.find('span', attrs={'data-spec': 'storage-hl'})
        if storage_hl:
            specs['storage'] = storage_hl.text.strip()

        # Release date from quick specs
        released_hl = soup.find('span', attrs={'data-spec': 'released-hl'})
        if released_hl:
            specs['release_date'] = released_hl.text.strip()

        # OS from quick specs
        os_hl = soup.find('span', attrs={'data-spec': 'os-hl'})
        if os_hl:
            specs['os'] = os_hl.text.strip()

        # Body from quick specs
        body_hl = soup.find('span', attrs={'data-spec': 'body-hl'})
        if body_hl:
            specs['body'] = body_hl.text.strip()

        # Find all spec tables for additional/fallback data
        spec_tables = soup.find_all('table')

        for table in spec_tables:
            rows = table.find_all('tr')
            for row in rows:
                header = row.find('td', class_='ttl')
                value = row.find('td', class_='nfo')

                if header and value:
                    header_text = header.text.strip().lower()
                    value_text = value.text.strip()

                    if ('announced' in header_text or 'status' in header_text) and specs['release_date'] == 'N/A':
                        specs['release_date'] = value_text
                    elif 'size' in header_text and specs['display'] == 'N/A':
                        if 'inch' in value_text.lower() or '"' in value_text:
                            specs['display'] = value_text
                    elif 'type' in header_text and ('amoled' in value_text.lower() or 'lcd' in value_text.lower() or 'dynamic' in value_text.lower()):
                        if specs['display'] == 'N/A' or ('amoled' in value_text.lower() and 'amoled' not in specs['display'].lower()):
                            # Append display type to existing display info
                            if specs['display'] != 'N/A':
                                specs['display'] = f"{specs['display']}, {value_text}"
                            else:
                                specs['display'] = value_text
                    elif 'battery' in header_text or 'capacity' in header_text:
                        if 'mah' in value_text.lower() and specs['battery'] == 'N/A':
                            specs['battery'] = value_text
                    elif 'internal' in header_text:
                        if specs['storage'] == 'N/A':
                            specs['storage'] = value_text
                        # Extract RAM from storage info if not already set
                        if specs['ram'] == 'N/A':
                            ram_match = re.search(r'(\d+)\s*GB\s*RAM', value_text)
                            if ram_match:
                                specs['ram'] = f"{ram_match.group(1)} GB"
                    elif 'chipset' in header_text and specs['chipset'] == 'N/A':
                        specs['chipset'] = value_text
                    elif 'os' in header_text and specs['os'] == 'N/A':
                        specs['os'] = value_text
                    elif 'dimensions' in header_text and specs['body'] == 'N/A':
                        specs['body'] = value_text
                    elif 'price' in header_text:
                        specs['price'] = value_text

        # Get camera info from specific sections if not already set or incomplete
        if specs['camera'] == 'N/A' or 'main' not in specs['camera'].lower():
            camera_info = []
            for table in spec_tables:
                table_header = table.find_previous('th')
                if table_header and 'camera' in table_header.text.lower():
                    rows = table.find_all('tr')
                    for row in rows:
                        value = row.find('td', class_='nfo')
                        if value and ('mp' in value.text.lower() or 'video' in value.text.lower()):
                            camera_info.append(value.text.strip())
            if camera_info:
                specs['camera'] = ' | '.join(camera_info[:3])

        # Try to get price from price section
        price_section = soup.find('td', class_='nfo', attrs={'data-spec': 'price'})
        if price_section:
            specs['price'] = price_section.text.strip()

        return specs

    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return None


def populate_with_sample_data():
    """Populate database with sample Samsung phone data (fallback if scraping fails)"""
    sample_phones = [
        {
            "model_name": "Samsung Galaxy S25 Ultra",
            "release_date": "February 2025",
            "display": "6.9 inches, Dynamic AMOLED 2X, 120Hz, 1440 x 3120 pixels",
            "battery": "5000 mAh, 45W wired charging, 15W wireless",
            "camera": "200 MP main | 50 MP periscope telephoto | 10 MP telephoto | 12 MP ultrawide",
            "ram": "12/16 GB",
            "storage": "256GB/512GB/1TB",
            "price": "$1299 / €1449",
            "chipset": "Snapdragon 8 Elite",
            "os": "Android 15, One UI 7",
            "body": "162.8 x 77.6 x 8.2 mm, 218g, Titanium frame",
            "url": "https://www.gsmarena.com/samsung_galaxy_s25_ultra-13322.php"
        },
        {
            "model_name": "Samsung Galaxy S25+",
            "release_date": "February 2025",
            "display": "6.7 inches, Dynamic AMOLED 2X, 120Hz, 1440 x 3120 pixels",
            "battery": "4900 mAh, 45W wired charging, 15W wireless",
            "camera": "50 MP main | 10 MP telephoto | 12 MP ultrawide",
            "ram": "12 GB",
            "storage": "256GB/512GB",
            "price": "$999 / €1149",
            "chipset": "Snapdragon 8 Elite",
            "os": "Android 15, One UI 7",
            "body": "158.4 x 75.8 x 7.3 mm, 190g",
            "url": "https://www.gsmarena.com/samsung_galaxy_s25+-13323.php"
        },
        {
            "model_name": "Samsung Galaxy S25",
            "release_date": "February 2025",
            "display": "6.2 inches, Dynamic AMOLED 2X, 120Hz, 1080 x 2340 pixels",
            "battery": "4000 mAh, 25W wired charging, 15W wireless",
            "camera": "50 MP main | 10 MP telephoto | 12 MP ultrawide",
            "ram": "12 GB",
            "storage": "128GB/256GB/512GB",
            "price": "$799 / €899",
            "chipset": "Snapdragon 8 Elite",
            "os": "Android 15, One UI 7",
            "body": "146.9 x 70.5 x 7.2 mm, 162g",
            "url": "https://www.gsmarena.com/samsung_galaxy_s25-13324.php"
        },
        {
            "model_name": "Samsung Galaxy S24 Ultra",
            "release_date": "January 2024",
            "display": "6.8 inches, Dynamic AMOLED 2X, 120Hz, 1440 x 3120 pixels",
            "battery": "5000 mAh, 45W wired charging, 15W wireless",
            "camera": "200 MP main | 50 MP periscope telephoto | 10 MP telephoto | 12 MP ultrawide",
            "ram": "12 GB",
            "storage": "256GB/512GB/1TB",
            "price": "$1299 / €1449",
            "chipset": "Snapdragon 8 Gen 3",
            "os": "Android 14, One UI 6.1",
            "body": "162.3 x 79 x 8.6 mm, 232g, Titanium frame",
            "url": "https://www.gsmarena.com/samsung_galaxy_s24_ultra-12771.php"
        },
        {
            "model_name": "Samsung Galaxy S24+",
            "release_date": "January 2024",
            "display": "6.7 inches, Dynamic AMOLED 2X, 120Hz, 1440 x 3120 pixels",
            "battery": "4900 mAh, 45W wired charging, 15W wireless",
            "camera": "50 MP main | 10 MP telephoto | 12 MP ultrawide",
            "ram": "12 GB",
            "storage": "256GB/512GB",
            "price": "$999 / €1149",
            "chipset": "Snapdragon 8 Gen 3 / Exynos 2400",
            "os": "Android 14, One UI 6.1",
            "body": "158.5 x 75.9 x 7.7 mm, 196g",
            "url": "https://www.gsmarena.com/samsung_galaxy_s24+-12732.php"
        },
        {
            "model_name": "Samsung Galaxy S24",
            "release_date": "January 2024",
            "display": "6.2 inches, Dynamic AMOLED 2X, 120Hz, 1080 x 2340 pixels",
            "battery": "4000 mAh, 25W wired charging, 15W wireless",
            "camera": "50 MP main | 10 MP telephoto | 12 MP ultrawide",
            "ram": "8 GB",
            "storage": "128GB/256GB",
            "price": "$799 / €899",
            "chipset": "Snapdragon 8 Gen 3 / Exynos 2400",
            "os": "Android 14, One UI 6.1",
            "body": "147 x 70.6 x 7.6 mm, 167g",
            "url": "https://www.gsmarena.com/samsung_galaxy_s24-12733.php"
        },
        {
            "model_name": "Samsung Galaxy S23 Ultra",
            "release_date": "February 2023",
            "display": "6.8 inches, Dynamic AMOLED 2X, 120Hz, 1440 x 3088 pixels",
            "battery": "5000 mAh, 45W wired charging, 15W wireless",
            "camera": "200 MP main | 10 MP periscope telephoto | 10 MP telephoto | 12 MP ultrawide",
            "ram": "8/12 GB",
            "storage": "256GB/512GB/1TB",
            "price": "$1199 / €1399",
            "chipset": "Snapdragon 8 Gen 2",
            "os": "Android 13, One UI 5.1",
            "body": "163.4 x 78.1 x 8.9 mm, 234g",
            "url": "https://www.gsmarena.com/samsung_galaxy_s23_ultra-12024.php"
        },
        {
            "model_name": "Samsung Galaxy S23+",
            "release_date": "February 2023",
            "display": "6.6 inches, Dynamic AMOLED 2X, 120Hz, 1080 x 2340 pixels",
            "battery": "4700 mAh, 45W wired charging, 15W wireless",
            "camera": "50 MP main | 10 MP telephoto | 12 MP ultrawide",
            "ram": "8 GB",
            "storage": "256GB/512GB",
            "price": "$999 / €1119",
            "chipset": "Snapdragon 8 Gen 2",
            "os": "Android 13, One UI 5.1",
            "body": "157.8 x 76.2 x 7.6 mm, 196g",
            "url": "https://www.gsmarena.com/samsung_galaxy_s23+-12083.php"
        },
        {
            "model_name": "Samsung Galaxy S23",
            "release_date": "February 2023",
            "display": "6.1 inches, Dynamic AMOLED 2X, 120Hz, 1080 x 2340 pixels",
            "battery": "3900 mAh, 25W wired charging, 15W wireless",
            "camera": "50 MP main | 10 MP telephoto | 12 MP ultrawide",
            "ram": "8 GB",
            "storage": "128GB/256GB",
            "price": "$799 / €949",
            "chipset": "Snapdragon 8 Gen 2",
            "os": "Android 13, One UI 5.1",
            "body": "146.3 x 70.9 x 7.6 mm, 168g",
            "url": "https://www.gsmarena.com/samsung_galaxy_s23-12082.php"
        },
        {
            "model_name": "Samsung Galaxy S22 Ultra",
            "release_date": "February 2022",
            "display": "6.8 inches, Dynamic AMOLED 2X, 120Hz, 1440 x 3088 pixels",
            "battery": "5000 mAh, 45W wired charging, 15W wireless",
            "camera": "108 MP main | 10 MP periscope telephoto | 10 MP telephoto | 12 MP ultrawide",
            "ram": "8/12 GB",
            "storage": "128GB/256GB/512GB/1TB",
            "price": "$1199 / €1249",
            "chipset": "Snapdragon 8 Gen 1 / Exynos 2200",
            "os": "Android 12, One UI 4.1",
            "body": "163.3 x 77.9 x 8.9 mm, 228g",
            "url": "https://www.gsmarena.com/samsung_galaxy_s22_ultra_5g-11251.php"
        },
        {
            "model_name": "Samsung Galaxy S22+",
            "release_date": "February 2022",
            "display": "6.6 inches, Dynamic AMOLED 2X, 120Hz, 1080 x 2340 pixels",
            "battery": "4500 mAh, 45W wired charging, 15W wireless",
            "camera": "50 MP main | 10 MP telephoto | 12 MP ultrawide",
            "ram": "8 GB",
            "storage": "128GB/256GB",
            "price": "$999 / €1049",
            "chipset": "Snapdragon 8 Gen 1 / Exynos 2200",
            "os": "Android 12, One UI 4.1",
            "body": "157.4 x 75.8 x 7.6 mm, 196g",
            "url": "https://www.gsmarena.com/samsung_galaxy_s22+-11252.php"
        },
        {
            "model_name": "Samsung Galaxy S22",
            "release_date": "February 2022",
            "display": "6.1 inches, Dynamic AMOLED 2X, 120Hz, 1080 x 2340 pixels",
            "battery": "3700 mAh, 25W wired charging, 15W wireless",
            "camera": "50 MP main | 10 MP telephoto | 12 MP ultrawide",
            "ram": "8 GB",
            "storage": "128GB/256GB",
            "price": "$799 / €849",
            "chipset": "Snapdragon 8 Gen 1 / Exynos 2200",
            "os": "Android 12, One UI 4.1",
            "body": "146 x 70.6 x 7.6 mm, 168g",
            "url": "https://www.gsmarena.com/samsung_galaxy_s22_5g-11253.php"
        },
        {
            "model_name": "Samsung Galaxy S21 Ultra",
            "release_date": "January 2021",
            "display": "6.8 inches, Dynamic AMOLED 2X, 120Hz, 1440 x 3200 pixels",
            "battery": "5000 mAh, 25W wired charging, 15W wireless",
            "camera": "108 MP main | 10 MP periscope telephoto | 10 MP telephoto | 12 MP ultrawide",
            "ram": "12/16 GB",
            "storage": "128GB/256GB/512GB",
            "price": "$1199 / €1399",
            "chipset": "Snapdragon 888 / Exynos 2100",
            "os": "Android 11, One UI 3.1",
            "body": "165.1 x 75.6 x 8.9 mm, 227g",
            "url": "https://www.gsmarena.com/samsung_galaxy_s21_ultra_5g-10596.php"
        },
        {
            "model_name": "Samsung Galaxy Z Fold 6",
            "release_date": "July 2024",
            "display": "7.6 inches foldable, Dynamic AMOLED 2X, 120Hz, 1856 x 2160 pixels",
            "battery": "4400 mAh, 25W wired charging, 15W wireless",
            "camera": "50 MP main | 10 MP telephoto | 12 MP ultrawide",
            "ram": "12 GB",
            "storage": "256GB/512GB/1TB",
            "price": "$1899 / €1999",
            "chipset": "Snapdragon 8 Gen 3",
            "os": "Android 14, One UI 6.1.1",
            "body": "153.5 x 132.6 x 5.6 mm (unfolded), 239g",
            "url": "https://www.gsmarena.com/samsung_galaxy_z_fold6-12784.php"
        },
        {
            "model_name": "Samsung Galaxy Z Fold 5",
            "release_date": "July 2023",
            "display": "7.6 inches foldable, Dynamic AMOLED 2X, 120Hz, 1812 x 2176 pixels",
            "battery": "4400 mAh, 25W wired charging, 15W wireless",
            "camera": "50 MP main | 10 MP telephoto | 12 MP ultrawide",
            "ram": "12 GB",
            "storage": "256GB/512GB/1TB",
            "price": "$1799 / €1899",
            "chipset": "Snapdragon 8 Gen 2",
            "os": "Android 13, One UI 5.1.1",
            "body": "154.9 x 129.9 x 6.1 mm (unfolded), 253g",
            "url": "https://www.gsmarena.com/samsung_galaxy_z_fold5-12418.php"
        },
        {
            "model_name": "Samsung Galaxy Z Fold 4",
            "release_date": "August 2022",
            "display": "7.6 inches foldable, Dynamic AMOLED 2X, 120Hz, 1812 x 2176 pixels",
            "battery": "4400 mAh, 25W wired charging, 15W wireless",
            "camera": "50 MP main | 10 MP telephoto | 12 MP ultrawide",
            "ram": "12 GB",
            "storage": "256GB/512GB/1TB",
            "price": "$1799 / €1799",
            "chipset": "Snapdragon 8+ Gen 1",
            "os": "Android 12L, One UI 4.1.1",
            "body": "155.1 x 130.1 x 6.3 mm (unfolded), 263g",
            "url": "https://www.gsmarena.com/samsung_galaxy_z_fold4-11737.php"
        },
        {
            "model_name": "Samsung Galaxy Z Flip 6",
            "release_date": "July 2024",
            "display": "6.7 inches foldable, Dynamic AMOLED 2X, 120Hz, 1080 x 2640 pixels",
            "battery": "4000 mAh, 25W wired charging, 15W wireless",
            "camera": "50 MP main | 12 MP ultrawide",
            "ram": "12 GB",
            "storage": "256GB/512GB",
            "price": "$1099 / €1199",
            "chipset": "Snapdragon 8 Gen 3",
            "os": "Android 14, One UI 6.1.1",
            "body": "165.1 x 71.9 x 6.9 mm (unfolded), 187g",
            "url": "https://www.gsmarena.com/samsung_galaxy_z_flip6-12785.php"
        },
        {
            "model_name": "Samsung Galaxy Z Flip 5",
            "release_date": "July 2023",
            "display": "6.7 inches foldable, Dynamic AMOLED 2X, 120Hz, 1080 x 2640 pixels",
            "battery": "3700 mAh, 25W wired charging, 15W wireless",
            "camera": "12 MP main | 12 MP ultrawide",
            "ram": "8 GB",
            "storage": "256GB/512GB",
            "price": "$999 / €1199",
            "chipset": "Snapdragon 8 Gen 2",
            "os": "Android 13, One UI 5.1.1",
            "body": "165.1 x 71.9 x 6.9 mm (unfolded), 187g",
            "url": "https://www.gsmarena.com/samsung_galaxy_z_flip5-12419.php"
        },
        {
            "model_name": "Samsung Galaxy Z Flip 4",
            "release_date": "August 2022",
            "display": "6.7 inches foldable, Dynamic AMOLED 2X, 120Hz, 1080 x 2640 pixels",
            "battery": "3700 mAh, 25W wired charging, 15W wireless",
            "camera": "12 MP main | 12 MP ultrawide",
            "ram": "8 GB",
            "storage": "128GB/256GB/512GB",
            "price": "$999 / €1099",
            "chipset": "Snapdragon 8+ Gen 1",
            "os": "Android 12, One UI 4.1.1",
            "body": "165.2 x 71.9 x 6.9 mm (unfolded), 187g",
            "url": "https://www.gsmarena.com/samsung_galaxy_z_flip4-11738.php"
        },
        {
            "model_name": "Samsung Galaxy A54 5G",
            "release_date": "March 2023",
            "display": "6.4 inches, Super AMOLED, 120Hz, 1080 x 2340 pixels",
            "battery": "5000 mAh, 25W wired charging",
            "camera": "50 MP main | 12 MP ultrawide | 5 MP macro",
            "ram": "8 GB",
            "storage": "128GB/256GB",
            "price": "$449 / €489",
            "chipset": "Exynos 1380",
            "os": "Android 13, One UI 5.1",
            "body": "158.2 x 76.7 x 8.2 mm, 202g",
            "url": "https://www.gsmarena.com/samsung_galaxy_a54_5g-12070.php"
        },
        {
            "model_name": "Samsung Galaxy A53 5G",
            "release_date": "March 2022",
            "display": "6.5 inches, Super AMOLED, 120Hz, 1080 x 2400 pixels",
            "battery": "5000 mAh, 25W wired charging",
            "camera": "64 MP main | 12 MP ultrawide | 5 MP macro | 5 MP depth",
            "ram": "6/8 GB",
            "storage": "128GB/256GB",
            "price": "$449 / €449",
            "chipset": "Exynos 1280",
            "os": "Android 12, One UI 4.1",
            "body": "159.6 x 74.8 x 8.1 mm, 189g",
            "url": "https://www.gsmarena.com/samsung_galaxy_a53_5g-11268.php"
        },
        {
            "model_name": "Samsung Galaxy A34 5G",
            "release_date": "March 2023",
            "display": "6.6 inches, Super AMOLED, 120Hz, 1080 x 2340 pixels",
            "battery": "5000 mAh, 25W wired charging",
            "camera": "48 MP main | 8 MP ultrawide | 5 MP macro",
            "ram": "6/8 GB",
            "storage": "128GB/256GB",
            "price": "$399 / €389",
            "chipset": "MediaTek Dimensity 1080",
            "os": "Android 13, One UI 5.1",
            "body": "161.3 x 78.1 x 8.2 mm, 199g",
            "url": "https://www.gsmarena.com/samsung_galaxy_a34_5g-12074.php"
        },
        {
            "model_name": "Samsung Galaxy A73 5G",
            "release_date": "April 2022",
            "display": "6.7 inches, Super AMOLED Plus, 120Hz, 1080 x 2400 pixels",
            "battery": "5000 mAh, 25W wired charging",
            "camera": "108 MP main | 12 MP ultrawide | 5 MP macro | 5 MP depth",
            "ram": "6/8 GB",
            "storage": "128GB/256GB",
            "price": "$499 / €509",
            "chipset": "Snapdragon 778G",
            "os": "Android 12, One UI 4.1",
            "body": "163.7 x 76.1 x 7.6 mm, 181g",
            "url": "https://www.gsmarena.com/samsung_galaxy_a73_5g-11429.php"
        },
        {
            "model_name": "Samsung Galaxy Note 20 Ultra",
            "release_date": "August 2020",
            "display": "6.9 inches, Dynamic AMOLED 2X, 120Hz, 1440 x 3088 pixels",
            "battery": "4500 mAh, 25W wired charging, 15W wireless",
            "camera": "108 MP main | 12 MP periscope telephoto | 12 MP ultrawide",
            "ram": "12 GB",
            "storage": "128GB/512GB",
            "price": "$1299 / €1299",
            "chipset": "Snapdragon 865+ / Exynos 990",
            "os": "Android 10, One UI 2.5",
            "body": "164.8 x 77.2 x 8.1 mm, 208g, S Pen included",
            "url": "https://www.gsmarena.com/samsung_galaxy_note20_ultra-10261.php"
        },
        {
            "model_name": "Samsung Galaxy Note 20",
            "release_date": "August 2020",
            "display": "6.7 inches, Super AMOLED Plus, 60Hz, 1080 x 2400 pixels",
            "battery": "4300 mAh, 25W wired charging, 15W wireless",
            "camera": "64 MP main | 12 MP ultrawide | 12 MP telephoto",
            "ram": "8 GB",
            "storage": "128GB/256GB",
            "price": "$999 / €949",
            "chipset": "Snapdragon 865+ / Exynos 990",
            "os": "Android 10, One UI 2.5",
            "body": "161.6 x 75.2 x 8.3 mm, 192g, S Pen included",
            "url": "https://www.gsmarena.com/samsung_galaxy_note20-10338.php"
        },
        {
            "model_name": "Samsung Galaxy S20 Ultra",
            "release_date": "March 2020",
            "display": "6.9 inches, Dynamic AMOLED 2X, 120Hz, 1440 x 3200 pixels",
            "battery": "5000 mAh, 45W wired charging, 15W wireless",
            "camera": "108 MP main | 48 MP periscope telephoto | 12 MP ultrawide",
            "ram": "12/16 GB",
            "storage": "128GB/256GB/512GB",
            "price": "$1399 / €1349",
            "chipset": "Snapdragon 865 / Exynos 990",
            "os": "Android 10, One UI 2.0",
            "body": "166.9 x 76 x 8.8 mm, 220g",
            "url": "https://www.gsmarena.com/samsung_galaxy_s20_ultra_5g-10040.php"
        },
        {
            "model_name": "Samsung Galaxy S20+",
            "release_date": "March 2020",
            "display": "6.7 inches, Dynamic AMOLED 2X, 120Hz, 1440 x 3200 pixels",
            "battery": "4500 mAh, 25W wired charging, 15W wireless",
            "camera": "64 MP main | 12 MP ultrawide | 12 MP telephoto",
            "ram": "8/12 GB",
            "storage": "128GB/256GB/512GB",
            "price": "$1199 / €1099",
            "chipset": "Snapdragon 865 / Exynos 990",
            "os": "Android 10, One UI 2.0",
            "body": "161.9 x 73.7 x 7.8 mm, 186g",
            "url": "https://www.gsmarena.com/samsung_galaxy_s20+-10100.php"
        },
        {
            "model_name": "Samsung Galaxy S20",
            "release_date": "March 2020",
            "display": "6.2 inches, Dynamic AMOLED 2X, 120Hz, 1440 x 3200 pixels",
            "battery": "4000 mAh, 25W wired charging, 15W wireless",
            "camera": "64 MP main | 12 MP ultrawide | 12 MP telephoto",
            "ram": "8/12 GB",
            "storage": "128GB",
            "price": "$999 / €899",
            "chipset": "Snapdragon 865 / Exynos 990",
            "os": "Android 10, One UI 2.0",
            "body": "151.7 x 69.1 x 7.9 mm, 163g",
            "url": "https://www.gsmarena.com/samsung_galaxy_s20-10081.php"
        },
        {
            "model_name": "Samsung Galaxy A55 5G",
            "release_date": "March 2024",
            "display": "6.6 inches, Super AMOLED, 120Hz, 1080 x 2340 pixels",
            "battery": "5000 mAh, 25W wired charging",
            "camera": "50 MP main | 12 MP ultrawide | 5 MP macro",
            "ram": "8/12 GB",
            "storage": "128GB/256GB",
            "price": "$449 / €479",
            "chipset": "Exynos 1480",
            "os": "Android 14, One UI 6.1",
            "body": "161.1 x 77.4 x 8.2 mm, 213g",
            "url": "https://www.gsmarena.com/samsung_galaxy_a55-12824.php"
        },
        {
            "model_name": "Samsung Galaxy A35 5G",
            "release_date": "March 2024",
            "display": "6.6 inches, Super AMOLED, 120Hz, 1080 x 2340 pixels",
            "battery": "5000 mAh, 25W wired charging",
            "camera": "50 MP main | 8 MP ultrawide | 5 MP macro",
            "ram": "6/8 GB",
            "storage": "128GB/256GB",
            "price": "$399 / €369",
            "chipset": "Exynos 1380",
            "os": "Android 14, One UI 6.1",
            "body": "161.7 x 78.0 x 8.2 mm, 209g",
            "url": "https://www.gsmarena.com/samsung_galaxy_a35-12707.php"
        }
    ]

    return sample_phones


def run_scraper(force_refresh=False):
    """Main function to run the scraper and populate the database"""
    print("Initializing database...")
    init_db()

    db = SessionLocal()

    try:
        # Check if we already have data
        existing_count = db.query(Phone).count()
        if existing_count >= 20 and not force_refresh:
            print(f"Database already has {existing_count} phones. Skipping scrape.")
            return

        # Clear existing data if force refresh
        if force_refresh and existing_count > 0:
            print(f"Clearing {existing_count} existing phones...")
            db.query(Phone).delete()
            db.commit()

        print("Attempting to scrape from GSMArena...")
        phone_links = get_samsung_phone_links()

        phones_added = 0

        if phone_links:
            print(f"Found {len(phone_links)} Samsung phones to scrape")

            for phone in phone_links:
                if phones_added >= 25:
                    break

                print(f"Scraping: {phone['name']}")
                specs = scrape_phone_details(phone['url'], phone['name'])

                if specs:
                    # Check if phone already exists
                    existing = db.query(Phone).filter(Phone.model_name == specs['model_name']).first()
                    if not existing:
                        new_phone = Phone(**specs)
                        db.add(new_phone)
                        db.commit()
                        phones_added += 1
                        print(f"  Added: {specs['model_name']}")
                    else:
                        print(f"  Skipped (exists): {specs['model_name']}")

                time.sleep(3)  # Rate limiting

        # If scraping didn't get enough data, use sample data
        if phones_added < 20:
            print("\nUsing sample data to ensure complete dataset...")
            sample_phones = populate_with_sample_data()

            for phone_data in sample_phones:
                existing = db.query(Phone).filter(Phone.model_name == phone_data['model_name']).first()
                if not existing:
                    new_phone = Phone(**phone_data)
                    db.add(new_phone)
                    phones_added += 1

            db.commit()

        final_count = db.query(Phone).count()
        print(f"\nScraping complete! Total phones in database: {final_count}")

    except Exception as e:
        print(f"Error during scraping: {e}")
        db.rollback()

        # Fallback to sample data
        print("\nFalling back to sample data...")
        sample_phones = populate_with_sample_data()

        for phone_data in sample_phones:
            existing = db.query(Phone).filter(Phone.model_name == phone_data['model_name']).first()
            if not existing:
                new_phone = Phone(**phone_data)
                db.add(new_phone)

        db.commit()
        print(f"Added {db.query(Phone).count()} phones from sample data")

    finally:
        db.close()


if __name__ == "__main__":
    import sys
    force = '--force' in sys.argv or '-f' in sys.argv
    if force:
        print("Force refresh mode enabled - will clear existing data")
    run_scraper(force_refresh=force)
