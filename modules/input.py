


def user_input():
    print("Welcome to EDASS (Elite Dangerous Automatic System Survey)!")
    print("This tool helps you find uncolonised systems in Elite Dangerous.")
    print("Please enter the search parameters below.")
    centre = input("Enter the name of the central system (e.g., 'Sol'): ").strip()
    while not centre:
        print("System name cannot be empty. Please try again.")
        centre = input("Enter the name of the central system (e.g., 'Sol'): ").strip()
    
    radius_str = input("Enter the search radius in light-years (e.g., '20'): ").strip()
    while True:
        try:
            radius = float(radius_str)
            if radius <= 0:
                raise ValueError
            if radius >= 100:
                print("Warning: Large radius may result in long wait times.")
            break
        except ValueError:
            print("Invalid radius. Please enter a positive number.")
            radius_str = input("Enter the search radius in light-years (e.g., '20'): ").strip()
    
    min_planets_str = input("Enter the minimum number of planets required (default 0): ").strip()
    if not min_planets_str:
        min_planets = 0
    else:
        while True:
            try:
                min_planets = int(min_planets_str)
                if min_planets < 0:
                    raise ValueError
                break
            except ValueError:
                print("Invalid number. Please enter a non-negative integer.")
                min_planets_str = input("Enter the minimum number of planets required (default 0): ").strip()
    
    return centre, radius, min_planets