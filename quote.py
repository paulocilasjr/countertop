import sqlite3

def get_countertop_options():
    # Connect to the database
    conn = sqlite3.connect('countertops_and_accessories.db')
    cursor = conn.cursor()

    # Fetch available countertops
    cursor.execute('SELECT id, material_level FROM countertop')
    options = cursor.fetchall()

    conn.close()
    return options

def get_countertop_price(selection_id):
    # Connect to the database
    conn = sqlite3.connect('countertops_and_accessories.db')
    cursor = conn.cursor()

    # Fetch the price for the selected countertop
    cursor.execute('SELECT price FROM countertop WHERE id = ?', (selection_id,))
    price = cursor.fetchone()[0]

    conn.close()
    return price

def get_accessory_options():
    # Connect to the database
    conn = sqlite3.connect('countertops_and_accessories.db')
    cursor = conn.cursor()

    # Fetch available accessories (sinks) - Use 'accessory_model' as per your table definition
    cursor.execute('SELECT id, accessory_model FROM accessories')  # Correct column name 'accessory_model'
    options = cursor.fetchall()

    conn.close()
    return options

def get_accessory_price(selection_id):
    # Connect to the database
    conn = sqlite3.connect('countertops_and_accessories.db')
    cursor = conn.cursor()

    # Fetch the price for the selected accessory
    cursor.execute('SELECT price FROM accessories WHERE id = ?', (selection_id,))
    price = cursor.fetchone()[0]

    conn.close()
    return price

def prompt_countertop():
    # Step 1: Ask for square feet
    square_feet = float(input("How many square feet? "))
    
    # Step 2: Show available countertops
    print("Available countertops:")
    options = get_countertop_options()
    for idx, (countertop_id, material_level) in enumerate(options, start=1):
        print(f"{idx}. {material_level}")
    
    # Ask the user to select a countertop
    selection = int(input("Select the countertop (by number): "))
    selected_countertop = options[selection - 1]  # Get the selected countertop info
    selected_countertop_id = selected_countertop[0]
    selected_countertop_name = selected_countertop[1]
    
    # Step 3: Get the price for the selected countertop
    price = get_countertop_price(selected_countertop_id)

    # Initialize subtotal to ensure it's always defined
    subtotal = 0

    # Step 4: Special condition for certain countertop selections
    if selected_countertop_name in ["granite level 3", "quartz level 2", "quartz level 3"]:
        # Multiply square feet by 10 and store
        special_square_feet = square_feet * 10
        print(f"Special square feet value: {special_square_feet}")
        
        # Ask for the price of the special countertop
        price = float(input(f"Enter the price for {selected_countertop_name}: "))
        
        # Ask for the profit (not percentage, but a fixed value)
        profit = float(input(f"Enter the profit for {selected_countertop_name}: "))
        
        # Sum up the special square feet, price, and profit, then divide by the square feet
        total = special_square_feet + price + profit
        new_price = total / square_feet
        print(f"New price per square foot: ${new_price:.2f}")
        
        # Calculate the final total (new price * original square feet)
        final_total = new_price * square_feet
        print(f"Grand total before confirmation: ${final_total:.2f} (calculated with special square feet: {special_square_feet})")

        # Ask the user if the calculated price is correct or if they want to change the profit
        while True:
            confirmation = input(f"The calculated price is ${new_price:.2f}. Is this correct? (yes/no): ").strip().lower()
            if confirmation == 'yes':
                print(f"Final price per square foot: ${new_price:.2f}")
                print(f"Final total: ${final_total:.2f}")
                return final_total  # Return the final total for this countertop
            elif confirmation == 'no':
                profit = float(input(f"Enter a new profit for {selected_countertop_name}: "))
                total = special_square_feet + price + profit
                new_price = total / square_feet
                final_total = new_price * square_feet
                print(f"New price per square foot: ${new_price:.2f}")
                print(f"Grand total before confirmation: ${final_total:.2f}")
            else:
                print("Invalid input! Please enter 'yes' or 'no'.")
    else:
        # Calculate and display the normal subtotal for regular countertops
        subtotal = price * square_feet
        print(f"Subtotal: ${subtotal:.2f}")
        return subtotal  # Return the subtotal for regular countertops

def prompt_accessories():
    # Show available accessories (sinks)
    print("Available accessories (sinks):")
    options = get_accessory_options()
    for idx, (accessory_id, accessory_model) in enumerate(options, start=1):
        print(f"{idx}. {accessory_model}")  # Display accessory_model, not 'name'

    # Ask the user to select an accessory
    selection = int(input("Select the sink (by number): "))
    selected_accessory = options[selection - 1]  # Get the selected accessory info
    selected_accessory_id = selected_accessory[0]
    selected_accessory_model = selected_accessory[1]

    # Ask for the quantity of the selected sink
    quantity = int(input(f"How many {selected_accessory_model} sinks? "))

    # Get the price for the selected sink
    price = get_accessory_price(selected_accessory_id)
    
    # Calculate the total price for the sinks
    total = price * quantity
    print(f"Total price for {selected_accessory_model} sinks: ${total:.2f}")
    
    return total  # Return the total price for the selected sinks

def main():
    total_price = 0  # Store the total price (sum of all quotes)

    # Loop to handle multiple countertops
    while True:
        countertop_price = prompt_countertop()
        total_price += countertop_price  # Add the countertop price to the total

        more_countertops = input("Is there more countertops? (yes/no): ").strip().lower()
        if more_countertops == 'no':
            break  # Exit the loop if no more countertops

    # Loop to handle accessories (sinks)
    while True:
        accessory_price = prompt_accessories()
        total_price += accessory_price  # Add the accessory price to the total

        more_accessories = input("Is there more accessories? (yes/no): ").strip().lower()
        if more_accessories == 'no':
            break  # Exit the loop if no more accessories

    # Final total price
    print(f"Final total price (countertops + accessories): ${total_price:.2f}")

# Run the program
main()