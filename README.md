### EDASS - Elite Dangerous Automatic System Survey



Generate a simple, human-readable CSV containing data on potentially colonisable systems in your vicinity in Elite Dangerous.



#### Features:

* Automatic look-up of EDSM data in a user-defined radius.
* Automatic, mostly fool-proof determination of system colonisation status.
* Counts the numbers of bodies and rings in the system, and the distance from you.
* Determination of "interesting" body types, and counts the total.
* Procedural notes section, including notes such as the presence of an ELW.



#### Caveats:

* EDSM data can be wrong, or out of date.
* This program is slow, it hammers the EDSM api, and is intentionally kept slow.
* Again, it is limited to EDSM data, if none is present, a search isn't valid.
* Does not currently check for star types, but is planned.
* Some systems are colonisation locked, but uninhabited and not permit locked, EDASS is not capable of detecting this colonisation lock, it will return as colonisable.



#### Requirements:

* You will need Python v3.10+, and ideally pip.
* The only required module is requests, it will NOT work without this module.



#### Usage:

To run EDASS, simply run EDASS.py in the root folder. The program will ask you for a central system to search around, a search radius, and a minimum planet count to cull. The CSV file is generated in /exports.

### Example CSV:

<img width="935" height="184" alt="50a019964a16593c171d772a68d4866e" src="https://github.com/user-attachments/assets/202fe3d8-1445-4349-91c8-52488af691e2" />


