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

def find_lot_number(divs):
    # Iterate over all <div> elements
    for div in divs:
        text = div.text.strip()  # Get the text of the div
        #print(div.get_attribute("outerHTML"));
        if text.startswith("Lot #"):  # Check if it starts with "Lot #"
            # Extract the number following "Lot #"
            #print(text)
            #print(div.get_attribute("outerHTML"))
            data = text.split('\n')
            lot_number=data[0].split('Lot #')[1]            
            mileage=data[1].split();
            distance=mileage[0];
  
            unit=mileage[1];
            
            



            return [lot_number, distance, unit]
    
    print("No Lot Number found.")
    return None

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
                title_element=container.find_elements(By.CSS_SELECTOR, "h3")[0]

                # Extract and print details
                title = title_element.text.strip()

                y=container.find_elements(By.CSS_SELECTOR, "[id^='CARD_PRICE']")[0]

                price=y.find_elements(By.CSS_SELECTOR,"span")[1].text.strip();

                z=container.find_elements(By.CSS_SELECTOR,"div")
                [lot_number, distance, unit]=find_lot_number(z)



                print(f"{index}. Title: {title}")
                print(f"   Price: {price}")
                print(f"   Distance Unit: {unit}")
                print(f"   Distance: {distance}")
                print(f"   Lot Number: {lot_number}")
                print("---")
                
                client.insert('EA1', [(lot_number, title, convert_price(price), convert_to_uint16(distance), unit, datetime.now())], 
                        column_names=['lot','title','price','distance','unit','time'])
            
            except Exception as card_error:
                print(f"Error extracting details for card {index}: {card_error}")
    
    except Exception as e:
        print(f"An error occurred: {e}")
    


def continuous_scrape(interval=5):
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