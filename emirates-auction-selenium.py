from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service as ChromeService
import time
import os
from datetime import datetime
import clickhouse_connect

from decimal import Decimal


def convert_to_uint16(distance_str):
    # Remove commas from the string
    cleaned_distance = distance_str.replace(',', '')

    # Convert to an integer
    distance = int(cleaned_distance)

    # Validate the range for UInt16 (0 to 65,535)
    if 0 <= distance <= 65535:
        return distance
    else:
        raise ValueError(f"Value {distance} is out of range for UInt16")



def convert_price(price_str):
    # Remove commas from the string
    cleaned_price = price_str.replace(',', '')

    # Convert to Decimal and format to two decimal places
    decimal_price = Decimal(cleaned_price).quantize(Decimal('0.01'))
    
    return decimal_price

def init_driver():
    """
    Scrape Emirates Auction using refined selectors
    """
    
    client = clickhouse_connect.get_client(host='localhost', username='default', password='password')

    # URL of the page
    url = "https://www.emiratesauction.com/motors?makes=&withoutmileages=true&pricesfrom=15000&pricesto=317300&yearsfrom=2015&yearsto=2025&withoutyears=true&k=honda"
    
    # Setup Chrome options
    chrome_options = Options()
        
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--headless")  # Enable headless mode        
    chrome_options.add_argument("--disable-gpu")  # Disable GPU (optional for most systems)
    
    # Create a new Chrome driver using WebDriver Manager
    service = ChromeService(ChromeDriverManager().install())
    
    # Create a new Chrome driver
    driver = webdriver.Chrome(service=service, options=chrome_options)

    # Navigate to the page
    driver.get(url)
    return [driver, client]

def parse_to_seconds(time_str):
    # Initialize total seconds
    total_seconds = 0

    # Check and parse days
    if 'd' in time_str:
        days_part = time_str.split('d')[0].strip()
        days = int(days_part)
        total_seconds += days * 24 * 60 * 60
        time_str = time_str.split('d')[1]  # Remove the processed days part

    # Check and parse hours
    if 'h' in time_str:
        hours_part = time_str.split('h')[0].strip()
        hours = int(hours_part.split()[-1])  # Get only the numeric part
        total_seconds += hours * 60 * 60
        time_str = time_str.split('h')[1]  # Remove the processed hours part

    # Check and parse minutes
    if 'm' in time_str:
        minutes_part = time_str.split('m')[0].strip()
        minutes = int(minutes_part.split()[-1])  # Get only the numeric part
        total_seconds += minutes * 60
        time_str = time_str.split('m')[1]  # Remove the processed minutes part

    # Check and parse seconds
    if 's' in time_str:
        seconds_part = time_str.split('s')[0].strip()
        seconds = int(seconds_part.split()[-1])  # Get only the numeric part
        total_seconds += seconds

    return total_seconds

def scrape_emirates_auction(driver,client):
    try:

        # Wait for the page to load
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
        )
        
        # Scroll to trigger lazy loading
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        
        # Wait for dynamic content to load
        time.sleep(10)
        
        # Find all list card containers
        list_card_containers = driver.find_elements(By.CLASS_NAME, "list-card-container")
        
        print(f"Found {len(list_card_containers)} vehicles:")
        
        # Extract details for each vehicle
        for index, container in enumerate(list_card_containers, 1):
            try:
                data = container.text.split('\n')
                title=data[0]
                lot_number = data[1].split('Lot #')[1]
                distance = data[2]
                end_date = datetime.strptime(data[4], f"%b %d, %I:%M %p").replace(year = datetime.now().year)
                time_left =parse_to_seconds(data[6])
                bids = data[8]
                price = data[10]

                

                



                print(f"{index}. Title: {title}")
                print(f"   Price: {price}")                
                print(f"   Distance: {distance}")
                print(f"   Lot Number: {lot_number}")
                print(f"   end_date: {end_date}")
                print(f"   time_left: {time_left}")
                print(f"   bids: {bids}")
                print("---")
                
                client.insert('EA1', [(lot_number, 
                                       title, 
                                       convert_price(price), 
                                       distance,
                                       end_date,
                                       time_left,
                                       bids,  
                                       datetime.now())], 
                        column_names=['lot','title','price','distance','end_date','time_left','bids','time'])
            
            except Exception as card_error:
                print(f"Error extracting details for card {index}: {card_error}")
    
    except Exception as e:
        print(f"An error occurred: {e}")
    


def continuous_scrape(interval=30):
    """
    Continuously scrape the Emirates Auction website at specified intervals
    
    :param interval: Time between scrapes in seconds (default 30)
    """
    

    try:
        while True:            
            print(f"\n--- Scraping at {datetime.now()} ---")
            scrape_emirates_auction(driver,client)
            print(f"\nWaiting {interval} seconds before next scrape...")
            time.sleep(interval)
            driver.refresh();
    
    except KeyboardInterrupt:
        print("\nScraping stopped by user.")

    finally:
        # Always close the driver
        driver.quit()

if __name__ == "__main__":
    [driver, client] = init_driver();
    # Single scrape
    #scrape_emirates_auction(driver,client)
    
    # Uncomment for continuous scraping
    continuous_scrape()