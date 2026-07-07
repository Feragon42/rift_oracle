# Rift Oracle
A Data Engineering portfolio project focused on predicting champion pick and ban trends across League of Legends patches.

## Goal
The goal of this project is to build a data platform capable of predicting champion *pick* and *ban* trends for future League of Legends patches.

## DataSources
The initial data sources for this project are: 
- Official Riot Games API
- Oracle's Elixir: An immense archive of competitive matches history.

## Roadmap
- [x] Explore available data sources
- [ ] Design the data model
- [ ] Build the ingestion pipelines
- [ ] Create the Bronze layer
- [ ] Build Silver transformations
- [ ] Design Gold analytics tables
- [ ] Engineer predictive features
- [ ] Train the first prediction model
- [ ] Evaluate model performance
- [ ] Deploy an interactive dashboard

## Engineering Journal:
### First Entry (2026-07-07)
*TL;DR:*
Findings:
---------
- Oracle's Elixir provides one of the cleanest competitive datasets available.
- Riot API is rich but rate-limited.
- Data Dragon contains versioned champion data.
- Patch notes are the biggest challenge.

Decisions
----------
- Oracle's Elixir will become the primary competitive dataset.
- Riot API will initially focus on Challenger Solo Queue.
- Champion changes will be simplified into Buff / Nerf labels.

Open Questions
--------------
- How should patch notes be parsed?
- Should I ignore item, map and system changes in the first version?
- Is Challenger Solo Queue representative enough?

In this first commit I explore the data available in the different sources available online.
First I have the oe_data_exploration notebook where I inspect the structure of the .csv files of competitive matches data in Oracle's Elixir, and found it to be a clean and well-structured dataset containing hundreds of valuable features to train predictive models with the LoL patch info to predict the behaviour of the competitive meta with every patch.
A second notebook, riot_api_exploration, shows how I use the official Riot Games API to obtain a list of player ID and the matches information for every one of them. Building this dataset could be challenging for the massive amount of data and the rate limits of the API for individuals. I plan to build the first version of the dataset only with the Challenger Division's players to test the how valuable is this data (that I suspect is the real behavior anchor, because professional teams often follow established team strategies rather than individual champion preferences). The match payload is extensive and contains many fields that are irrelevant for Ranked Solo Queue, since the API is designed to support multiple game modes, even when the data is in an unstructured json version.
The third notebook, ddragon_data_exploration, downloads the JSON definition of a champion from the official Riot archive Data Dragon. It contains of the champion skills and stats. In the Data Dragon's documentation they affirmed to update the files with every patch, but the numeration of the files are different for the patches, so I made a little test to confirm the value changes between the last two versions.
My major complication in this moment of the project is that Riot doesn't provide a simple format of the patch notes to parse. Maybe I'll need to make a web scraping to obtain that.
Because of the complexity involved in modeling over 170 champions, their abilities, items, map changes, and gameplay systems, I decided to reduce the scope of the first version. Rather than parsing every numerical change from the patch notes, the model will classify champion updates simply as Buff, Nerf, or Unchanged. Changes affecting items, objectives, maps, and other gameplay systems will be excluded from the initial implementation. This simplification should allow me to validate the predictive pipeline before introducing more detailed feature engineering.