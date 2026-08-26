import requests
from bs4 import BeautifulSoup

def decode_secret_message(url):
    # Fetch the HTML content from the Google Doc
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Locate the table and extract all rows, skipping the header
    rows = soup.find_all('tr')[1:]
    
    grid_data = {}
    max_x = 0
    max_y = 0
    
    # Parse the coordinate and character data
    for row in rows:
        cols = row.find_all('td')
        if len(cols) >= 3:
            x = int(cols[0].text.strip())
            char = cols[1].text.strip()
            y = int(cols[2].text.strip())
            
            grid_data[(x, y)] = char
            
            # Keep track of the grid's maximum boundaries
            max_x = max(max_x, x)
            max_y = max(max_y, y)
            
    # Print the resulting grid
    # y decrements from max_y down to 0 so the image isn't upside down
    for y in range(max_y, -1, -1):
        line = ""
        for x in range(max_x + 1):
            line += grid_data.get((x, y), " ")
        print(line)