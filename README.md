### EDASS - Elite Dangerous Automatic System Survey - V0.3



Generate a simple, human-readable CSV containing data on potentially colonisable or otherwise interesting and unique systems in Elite Dangerous.



#### Features:

* Automatic look-up of EDSM data in a user-defined radius.
* Automatic, mostly fool-proof determination of system colonisation status.
* Counts the numbers of bodies and rings in the system, and the distance from you.
* Determination of "interesting" body types, and counts the total.
* Counts stars, notes stars of interest to you.
* Procedural notes section, informing you of unique or important system info.



#### Caveats:

* EDSM data can be wrong, or out of date.
* This program is slow, it hammers the EDSM api, it is possible to be rate limited.
* Again, it is limited to EDSM data, if none is present, a search isn't valid.
* Some systems are colonisation locked, but uninhabited and not permit locked, EDASS is not capable of detecting this colonisation lock, it will return as colonisable.



#### Requirements:

* You will need Python v3.10+, and ideally pip.
* The only required module is httpx, it will NOT work without this module.



#### Usage:

To run EDASS, simply run EDASS.py in the root folder. The program will ask you for
a central system to search around, a search radius, and a minimum planet count to cull. The CSV file is generated in /export.

### Example CSV:

<img width="1184" height="763" alt="3107944a4326068cfca5e179fb7c6f1d" src="https://github.com/user-attachments/assets/11de9d1c-a979-4968-8e62-a93287716e2c" />


