# RPS Reaktor Assignment 2022

This is my implementation of the Reaktor 2022 pre-assignment for the Summer Developer position  
The application is developed with Flask framework

## How to Run

Go to the root derectory and run:
```bash
pip3 install -r requirements.txt
```
```bash
python3 rps/app.py
```

The app can now be accessed in the [http://localhost:5000/](http://localhost:5000/)


## Usage

**Index** page displays live games that have just ended along with the links to pages described below  
**Players** page shows a list of all the players in the tournament. You can click any player to view their games and stats  
**Live** page shows games that are currently being played and games that have just ended  
**Games** page shows some stats from all of the games along with the list of played games  

## Good to Know
* The application keeps a record of each game in the database so the database will be updated ones the server starts and periodically every 5 minutes
* Populating the database from scratch takes ~15 minutes and can be done with command:
```bash
cd rps && python3 db.py
```

### Known Issues and Development Ideas
* Games page loading time needs to be improved -> stats query takes too long
* Enhance the UI
  * Optimize for mobile
  * Add png to represent played hands
* Make database updating non-blocking
* Add tests
* Add better error pages
