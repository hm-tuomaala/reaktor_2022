# RPS Reaktor Assignment 2022

This is my implementation of the Reaktor 2022 pre-assignment for the Summer Developer position  
The application is developed with Flask framework

## How to Run

Go to the root derectory and run:
* Install requirements
```bash
pip3 install -r requirements.txt
```
* Initialize the database that holds the games (**Do this only on the first run**)
```bash
cd rpc && python3 db.py && cd ..
```
* Launch the server (Takes ~10 mins if the database hasn't been initialized previously)
```bash
python3 rpc/app.py
```

The app can now be accessed in the [http://localhost:5000/](http://localhost:5000/)


## Usage

**Index** page displays live games that have just ended along with the links to pages described below  
**Players** page shows a list of all the players in the tournament. You can click any player to view their games and stats  
**Live** page shows games that are currently being played and games that have just ended  
**Games** page shows some stats from all of the games along with the list of played games  

## Good to Know
* The application keeps a record of each game in the database so the database will be updated ones the server starts and periodically every 5 minutes
* Populating the database from scratch takes ~10 minutes and after the first initialization few seconds depending how long the server has been offline

### Known Issues and Development Ideas
* Curent database schema is poor and should be changed to a more robust relational structure
* Games page loading time needs to be improved -> stats-query takes too long
* Enhance the UI
  * Optimize for mobile
  * Add png to represent played hands
* Make database updating non-blocking
* Add tests
* Add better error pages
