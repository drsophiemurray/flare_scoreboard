flare_scoreboard
================

Python routines to grab latest flare forecasts from internal MO systems and send them to NASA/CCMC's [Flare Scoreboard](http://ccmc.gsfc.nasa.gov/challenges/flare.php) for intercomparison.

The forecasts are grabbed from the internal archiving system and converted to the International Space Environment Service standardised XML forecast format. There are two types of forecast:

* **Radio Blackout Forecasts** consist of total disk forecasts for the next four days, and are available twice daily in JSON format. 
* **Sunspot Region Summaries** give 24-hour forecasts for all active regions on disk, and are available every six hours as .docx files. 

Both forecasts list percentage probabilities for _GOES_ M- and X- [class](http://www.swpc.noaa.gov/phenomena/solar-flares-radio-blackouts) flares.