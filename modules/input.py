


def user_input():
    print("Welcome to EDASS (Elite Dangerous Automatic System Survey) v0.3!")
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
            if radius <= 0: raise ValueError
            if not radius:  raise ValueError
            break
        except ValueError:
            print("Invalid radius. Please enter a valid number.")
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
                print("Invalid number. Please enter a valid number.")
                min_planets_str = input("Enter the minimum number of planets required (default 0): ").strip()

    exclude_uncolonisable_bool = input("Do you want to exclude uncolonisable systems? (y/n): ")
    exclude_uncolonisable_bool = exclude_uncolonisable_bool.strip().lower()
    if exclude_uncolonisable_bool in ("y", "yes"):
        exclude_uncolonisable = True
    elif exclude_uncolonisable_bool in ("n", "no", "false"):
        exclude_uncolonisable = False
    else:
        exclude_uncolonisable = True
        print("Input invalid, defaulting to true.")

    
    return centre, radius, min_planets, exclude_uncolonisable